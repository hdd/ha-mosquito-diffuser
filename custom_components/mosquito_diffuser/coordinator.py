"""Data coordinator for the Mosquito Diffuser integration.

Tracks cartridge consumption purely from the outlet's on/off state:

- Exact accounting on every on->off state transition.
- A 60 s tick keeps the accrual anchor fresh and covers restarts/downtime
  (if HA is down while the outlet is on, that time is caught up on the
  next tick, because the physical diffuser really kept running).
- The accumulator is persisted to ``.storage`` shortly after every change,
  so a month-long cartridge is unaffected by recorder purges or restarts.

No dependency on the recorder/history database at all.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any, Callable

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_LIFE_HOURS,
    CONF_LOW_THRESHOLD,
    CONF_OFF_TIME,
    CONF_ON_TIME,
    CONF_OUTLET,
    CONF_SCHEDULE_ENABLED,
    DEFAULT_LIFE_HOURS,
    DEFAULT_LOW_THRESHOLD,
    PERSIST_DELAY,
    STORAGE_VERSION,
    TICK_INTERVAL,
)


def _parse_hhmm(value: Any) -> time | None:
    """Parse an ``HH:MM`` string into a time object."""
    if not value:
        return None
    return dt_util.parse_time(value) or dt_util.parse_datetime(str(value))


class MosquitoDiffuserCoordinator:
    """Usage accounting + schedule engine for one diffuser instance."""

    def __init__(self, hass: HomeAssistant, entry, data: dict[str, Any]) -> None:
        """Initialize the coordinator from merged entry data/options."""
        self.hass = hass
        self.entry = entry

        self.outlet_entity: str = data[CONF_OUTLET]
        self.life_hours: float = float(data.get(CONF_LIFE_HOURS, DEFAULT_LIFE_HOURS))
        self.low_threshold: int = int(data.get(CONF_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD))
        self.schedule_enabled: bool = bool(data.get(CONF_SCHEDULE_ENABLED, False))
        self.on_time: time | None = _parse_hhmm(data.get(CONF_ON_TIME))
        self.off_time: time | None = _parse_hhmm(data.get(CONF_OFF_TIME))

        self.used_hours: float = 0.0
        self.installed_at: datetime = dt_util.utcnow()
        self.last_accrual: datetime = dt_util.utcnow()
        self.schedule_active: bool = True

        self._listeners: list[Callable[[], None]] = []
        self._unsubs: list[Callable[[], None]] = []
        self._dirty = False
        self._store = Store(hass, STORAGE_VERSION, f"mosquito_diffuser_{entry.entry_id}")

    # ------------------------------------------------------------------ load
    async def async_load(self) -> None:
        """Load persisted data and register all listeners."""
        raw = await self._store.async_load() or {}
        self.used_hours = float(raw.get("used_hours", 0.0) or 0.0)
        self.installed_at = (
            dt_util.parse_datetime(raw.get("installed_at", "")) or dt_util.utcnow()
        )
        self.last_accrual = (
            dt_util.parse_datetime(raw.get("last_accrual", "")) or dt_util.utcnow()
        )
        self.schedule_active = bool(raw.get("schedule_active", True))

        self._unsubs.append(
            async_track_state_change_event(
                self.hass, [self.outlet_entity], self._on_outlet_state_event
            )
        )
        self._unsubs.append(
            async_track_time_interval(self.hass, self._on_tick, TICK_INTERVAL)
        )
        if self.schedule_enabled and self.on_time and self.off_time:
            self._unsubs.append(
                async_track_time_change(
                    self.hass,
                    self._on_schedule_on,
                    hour=self.on_time.hour,
                    minute=self.on_time.minute,
                    second=0,
                )
            )
            self._unsubs.append(
                async_track_time_change(
                    self.hass,
                    self._on_schedule_off,
                    hour=self.off_time.hour,
                    minute=self.off_time.minute,
                    second=0,
                )
            )
        self._unsubs.append(
            self.hass.bus.async_listen_once(
                "homeassistant_shutdown", self._on_shutdown_event
            )
        )

    async def async_shutdown(self) -> None:
        """Remove listeners and flush state to disk."""
        while self._unsubs:
            self._unsubs.pop()()
        await self.async_persist()

    # --------------------------------------------------------------- accrual
    async def _on_outlet_state_event(self, event: Event) -> None:
        """Handle an outlet state change: charge exactly the finished ON span."""
        old_state = event.data.get("old_state")
        now = dt_util.utcnow()

        if old_state is not None and old_state.state == "on":
            # The outlet ran from the last accrual anchor up to this instant.
            self._accrue(now - self.last_accrual)

        self.last_accrual = now
        self._schedule_save()
        self._publish()

    async def _on_tick(self, _now: Any) -> None:
        """Periodic catch-up tick (also refreshes time-derived sensors)."""
        now = dt_util.utcnow()
        state = self.hass.states.get(self.outlet_entity)
        if state is not None and state.state == "on":
            self._accrue(now - self.last_accrual)
            self._schedule_save()
        self.last_accrual = now
        self._publish()

    def _accrue(self, span: timedelta) -> None:
        """Add a span of ON time to the cartridge counter."""
        seconds = span.total_seconds()
        if seconds > 0:
            self.used_hours = round(self.used_hours + seconds / 3600, 4)
            self._dirty = True

    # -------------------------------------------------------------- schedule
    @callback
    def _on_schedule_on(self, _now: Any) -> None:
        self._async_apply_schedule(True)

    @callback
    def _on_schedule_off(self, _now: Any) -> None:
        self._async_apply_schedule(False)

    @callback
    def _async_apply_schedule(self, turn_on: bool) -> None:
        """Switch the outlet at schedule time, unless paused."""
        if not self.schedule_active or not self.schedule_enabled:
            return
        state = self.hass.states.get(self.outlet_entity)
        if state is None:
            return
        if (turn_on and state.state == "on") or (not turn_on and state.state != "on"):
            return
        domain = self.outlet_entity.split(".", 1)[0]
        service = "turn_on" if turn_on else "turn_off"
        self.hass.async_create_task(
            self.hass.services.async_call(
                domain, service, {"entity_id": self.outlet_entity}, blocking=False
            )
        )

    async def async_set_schedule_active(self, active: bool) -> None:
        """Pause/resume the built-in schedule (virtual switch)."""
        if self.schedule_active == active:
            return
        self.schedule_active = active
        await self.async_persist()
        self._publish()

    # ----------------------------------------------------------------- reset
    async def async_reset_cartridge(self) -> None:
        """New cartridge installed: zero the counter, re-stamp the clock."""
        now = dt_util.utcnow()
        self.used_hours = 0.0
        self.installed_at = now
        self.last_accrual = now
        await self.async_persist()
        self._publish()

    async def async_set_level(self, pct: float) -> None:
        """Calibrate the counter from a remaining-life percentage.

        The install timestamp is backdated assuming 24 h/day pace, so the
        pace estimate starts conservative and converges to the real usage
        rhythm over the following days.
        """
        pct = max(0.0, min(float(pct), 100.0))
        now = dt_util.utcnow()
        self.used_hours = round(self.life_hours * (1 - pct / 100), 2)
        self.installed_at = now - timedelta(hours=self.used_hours / 24)
        self.last_accrual = now
        await self.async_persist()
        self._publish()

    # ------------------------------------------------------------ persistence
    def _store_data(self) -> dict[str, Any]:
        return {
            "used_hours": self.used_hours,
            "installed_at": self.installed_at.isoformat(),
            "last_accrual": self.last_accrual.isoformat(),
            "schedule_active": self.schedule_active,
        }

    @callback
    def _schedule_save(self) -> None:
        self._store.async_delay_save(self._store_data, PERSIST_DELAY)

    async def async_persist(self) -> None:
        await self._store.async_save(self._store_data())

    async def _on_shutdown_event(self, _event: Event) -> None:
        await self.async_persist()

    # ------------------------------------------------------------- derived
    @property
    def remaining_hours(self) -> float:
        return max(self.life_hours - self.used_hours, 0.0)

    @property
    def remaining_pct(self) -> float:
        if self.life_hours <= 0:
            return 0.0
        return min(self.remaining_hours / self.life_hours * 100, 100.0)

    @property
    def days_installed(self) -> float:
        span = (dt_util.utcnow() - self.installed_at).total_seconds() / 86400
        return max(span, 1 / 24)  # at least one hour, avoids div/0

    @property
    def avg_hours_per_day(self) -> float:
        return self.used_hours / self.days_installed

    @property
    def days_left(self) -> float:
        """Days until empty at the measured usage pace (24 h/day fallback)."""
        avg = self.avg_hours_per_day
        if avg < 1:
            avg = 24.0  # conservative until real usage data exists
        return round(self.remaining_hours / avg, 1)

    # ------------------------------------------------------------- listeners
    def async_add_listener(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def async_remove_listener(self, listener: Callable[[], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    @callback
    def _publish(self) -> None:
        for listener in list(self._listeners):
            listener()
