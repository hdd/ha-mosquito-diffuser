/**
 * Mosquito Diffuser Card — the companion Lovelace widget for the
 * `mosquito_diffuser` custom integration.
 *
 * Cartridge status at a glance: a vertical cartridge gauge (or the classic
 * donut, `gauge: donut`) with the remaining
 * percentage, days left at the measured pace, runtime left, hours used,
 * the estimated empty date, install date and average pace, the schedule
 * window with its active months — plus a
 * low-cartridge banner and one-tap actions: "new cartridge" reset
 * (two-tap confirm), schedule pause/resume and outlet toggle. The subtitle
 * flags when the schedule is paused or outside its active months.
 *
 * Plain web component: no build step, no external dependencies.
 *
 * Minimal configuration:
 *
 *   type: custom:mosquito-diffuser-card
 *   entity: sensor.<name>_remaining
 *
 * `entity` accepts any entity of the diffuser — the card strips the known
 * suffix from the id and finds the sibling entities automatically.
 * Every sibling can also be set explicitly:
 *
 *   name, icon, outlet_entity, days_entity, runtime_entity, used_entity,
 *   empty_entity, button_entity, level_entity, schedule_entity, low_entity,
 *   gauge ("bar" default, "donut"), stats ("tiles" default, "plain")
 */

const CARD_VERSION = "1.3.3";
const DEFAULT_ICON = "mdi:mosquito";

/** Known entity-id suffixes of the integration (longest first). */
const SUFFIXES = [
  "remaining_runtime",
  "estimated_empty",
  "days_left",
  "new_cartridge",
  "cartridge_level",
  "remaining",
  "used",
  "schedule",
  "low",
];

/** Trailing entity names to strip when deriving the device title. */
const NAME_TAILS = [
  "Remaining runtime",
  "Estimated empty",
  "Days left",
  "New cartridge",
  "Cartridge level",
  "Remaining",
  "Used",
  "Schedule",
  "Low",
];

/** Escape anything user-visible before it goes into the template. */
const esc = (value) =>
  String(value == null ? "" : value).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

/** Month abbreviations for compact season ranges (e.g. "Apr–Oct"). */
const MONTH_ABBR = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Compact label for a list of month numbers; "" when nothing is worth showing. */
const monthsSpan = (months) => {
  if (!Array.isArray(months)) return "";
  const set = [...new Set(months.map(Number))]
    .filter((m) => m >= 1 && m <= 12)
    .sort((a, b) => a - b);
  if (set.length === 0 || set.length === 12) return "";
  const runs = [];
  let start = set[0];
  let prev = set[0];
  for (let i = 1; i <= set.length; i++) {
    const m = set[i];
    if (m !== prev + 1) {
      runs.push(
        start === prev
          ? MONTH_ABBR[start - 1]
          : `${MONTH_ABBR[start - 1]}–${MONTH_ABBR[prev - 1]}`
      );
      start = m;
    }
    prev = m;
  }
  return runs.join(", ");
};

const STYLE = `
:host { display: block; }
.card { padding: 16px 16px 14px; }
.placeholder { color: var(--secondary-text-color); font-size: 13px; padding: 4px 0; }

.header { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.header-icon { --mdc-icon-size: 26px; color: var(--primary-text-color); flex: none; }
.title { font-size: 15px; font-weight: 600; color: var(--primary-text-color); }
.subtitle {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--secondary-text-color); margin-top: 1px;
}
.dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.dot.on { background: var(--success-color, #43b047); animation: md-pulse 2s ease-in-out infinite; }
.dot.off { background: var(--disabled-text-color, #9e9e9e); }
@keyframes md-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

.banner {
  display: flex; align-items: center; gap: 8px;
  margin: 10px 0 0; padding: 8px 12px;
  border-radius: 10px;
  background: rgba(229, 68, 72, 0.12);
  color: var(--error-color, #e54448);
  font-size: 13px; font-weight: 500;
  cursor: pointer;
}

.main { display: flex; align-items: center; gap: 18px; margin-top: 14px; }

.donut {
  position: relative;
  width: 128px; height: 128px; border-radius: 50%;
  flex: none;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background: conic-gradient(
    var(--ring) calc(var(--pct) * 1%),
    rgba(127, 127, 127, 0.25) 0
  );
  transition: background 0.6s ease;
  cursor: pointer;
}
.donut::after {
  content: "";
  position: absolute;
  inset: 13px;
  border-radius: 50%;
  background: var(--ha-card-background, var(--card-background-color, #fff));
  z-index: 0;
}
.donut > * { position: relative; z-index: 1; }
.donut-value { display: flex; align-items: baseline; }
.donut-value .num {
  font-size: 33px; font-weight: 700; line-height: 1;
  color: var(--primary-text-color);
}
.donut-value .unit {
  font-size: 15px; font-weight: 600;
  color: var(--secondary-text-color); margin-left: 2px;
}
.donut-label {
  font-size: 10px; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--secondary-text-color); margin-top: 4px;
}

/* Vertical cartridge gauge (default) */
.vbar {
  flex: none;
  display: flex; flex-direction: column; align-items: center;
  width: 92px;
  cursor: pointer;
}
.vbar-track {
  position: relative;
  width: 32px; height: 120px;
  border-radius: 16px;
  background: rgba(127, 127, 127, 0.25);
  overflow: hidden;
}
.vbar-fill {
  position: absolute; left: 0; right: 0; bottom: 0;
  height: calc(var(--pct) * 1%);
  border-radius: 16px;
  background: var(--ring);
  transition: height 0.6s ease;
}
.vbar-tick {
  position: absolute; left: 7px; right: 7px; height: 1px;
  background: rgba(127, 127, 127, 0.35);
  z-index: 1; pointer-events: none;
}
.vbar-value { display: flex; align-items: baseline; margin-top: 7px; }
.vbar-value .num {
  font-size: 30px; font-weight: 700; line-height: 1;
  color: var(--primary-text-color);
}
.vbar-value .unit {
  font-size: 14px; font-weight: 600;
  color: var(--secondary-text-color); margin-left: 2px;
}
.vbar-label {
  font-size: 10px; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--secondary-text-color); margin-top: 3px; text-align: center;
}

.stats { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.stat {
  display: flex; align-items: baseline; justify-content: space-between;
  padding: 5px 10px; border-radius: 8px;
}
.stat.clickable { cursor: pointer; }
.stat:hover { background: var(--secondary-background-color, rgba(127, 127, 127, 0.12)); }
.stat-label { font-size: 13px; color: var(--secondary-text-color); }
.stat-value { font-size: 14px; font-weight: 600; color: var(--primary-text-color); }

/* Stat tiles with mini progress bars (default) */
.tile {
  padding: 7px 10px 8px;
  border-radius: 10px;
  background: var(--secondary-background-color, rgba(127, 127, 127, 0.10));
}
.tile.clickable { cursor: pointer; }
.tile:hover { background: var(--secondary-background-color, rgba(127, 127, 127, 0.16)); }
.tile-top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.tile-label {
  font-size: 11px; letter-spacing: 0.05em; text-transform: uppercase;
  color: var(--secondary-text-color);
}
.tile-value {
  font-size: 15px; font-weight: 600;
  color: var(--primary-text-color); white-space: nowrap;
}
.tile-bar {
  margin-top: 6px; height: 4px;
  border-radius: 2px;
  background: rgba(127, 127, 127, 0.25);
  overflow: hidden;
}
.tile-fill {
  height: 100%; border-radius: 2px;
  background: var(--ring);
  transition: width 0.6s ease;
}

.meta {
  display: flex; flex-wrap: wrap; gap: 4px 16px;
  margin-top: 12px; padding-top: 10px;
  border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
  font-size: 12px; color: var(--secondary-text-color);
}
.meta-item { display: inline-flex; align-items: center; gap: 5px; }
.meta-item[data-entity] { cursor: pointer; }

.actions { display: flex; gap: 8px; margin-top: 12px; }
button.action {
  flex: 1;
  display: flex; align-items: center; justify-content: center;
  gap: 7px;
  padding: 10px 6px;
  border: none; border-radius: 12px;
  background: var(--secondary-background-color, rgba(127, 127, 127, 0.14));
  color: var(--primary-text-color);
  font: inherit; font-size: 12.5px; font-weight: 500;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
button.action:hover { opacity: 0.85; }
button.action.active { color: var(--success-color, #43b047); }
button.action.warn { color: var(--error-color, #e54448); }
.actions ha-icon, .meta-item ha-icon, .banner ha-icon { --mdc-icon-size: 16px; }
`;

class MosquitoDiffuserCard extends HTMLElement {
  /** Prefill for the visual/YAML card editor. */
  static getStubConfig() {
    return { entity: "" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._config = {};
    this._confirmReset = false;
    this._confirmTimer = null;
    this._rendered = null;
    // One delegated listener survives innerHTML re-renders.
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  get hass() {
    return this._hass;
  }

  setConfig(config) {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid configuration");
    }
    this._config = { name: "", icon: "", ...config };
    this._rendered = null;
    this._render();
  }

  // The card is roughly four rows tall.
  getCardSize() {
    return 4;
  }

  // ------------------------------------------------------------ resolution

  _st(entityId) {
    if (!entityId || !this._hass) return null;
    const state = this._hass.states[entityId];
    return state === undefined ? null : state;
  }

  /** Base name of the device: entity id minus domain and known suffix. */
  _base() {
    const id = String(this._config.entity || "").split(".").slice(1).join(".");
    for (const suffix of SUFFIXES) {
      if (id.endsWith("_" + suffix)) {
        return id.slice(0, id.length - suffix.length - 1);
      }
    }
    return id;
  }

  /** Resolve all sibling entities, honoring explicit config overrides. */
  _resolve() {
    const base = this._base();
    const cfg = this._config;
    const pick = (...ids) => ids.find((id) => this._st(id)) || null;

    const days = cfg.days_entity || pick(`sensor.${base}_days_left`);
    const low = cfg.low_entity || pick(`binary_sensor.${base}_low`);
    const daysState = this._st(days);
    const lowState = this._st(low);

    // The outlet is not one of our entities: the integration exposes it
    // as an attribute on the days-left / low sensors.
    const outlet =
      cfg.outlet_entity ||
      (daysState && daysState.attributes && daysState.attributes.outlet_entity) ||
      (lowState && lowState.attributes && lowState.attributes.outlet_entity) ||
      null;

    return {
      pct: cfg.entity || null,
      days,
      runtime: cfg.runtime_entity || pick(`sensor.${base}_remaining_runtime`),
      used: cfg.used_entity || pick(`sensor.${base}_used`),
      empty: cfg.empty_entity || pick(`sensor.${base}_estimated_empty`),
      reset: cfg.button_entity || pick(`button.${base}_new_cartridge`),
      level: cfg.level_entity || pick(`number.${base}_cartridge_level`),
      schedule: cfg.schedule_entity || pick(`switch.${base}_schedule`),
      low,
      outlet,
    };
  }

  // ------------------------------------------------------------- formatting

  _pctValue() {
    const state = this._st(this._config.entity);
    if (!state) return null;
    const value = Number(state.state);
    return Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : null;
  }

  _num(value) {
    return Math.abs(value) >= 10 ? Math.round(value) : Math.round(value * 10) / 10;
  }

  _hours(entityId) {
    const state = this._st(entityId);
    if (!state) return null;
    const value = Number(state.state);
    if (!Number.isFinite(value)) return null;
    return value < 1 ? "<1 h" : `${this._num(value)} h`;
  }

  _days() {
    const state = this._st(this._resolve().days);
    if (!state) return null;
    const value = Number(state.state);
    if (!Number.isFinite(value)) return null;
    return value < 1 ? "<1 d" : `${this._num(value)} d`;
  }

  _fmtDate(raw) {
    if (!raw) return null;
    const date = new Date(String(raw).replace(" ", "T"));
    if (isNaN(date.getTime())) return null;
    const language = this._hass && this._hass.locale && this._hass.locale.language;
    return date.toLocaleDateString(language || undefined, {
      day: "numeric",
      month: "short",
    });
  }

  _lowThreshold() {
    const low = this._st(this._resolve().low);
    const raw = low && low.attributes ? low.attributes.threshold_pct : undefined;
    const value = Number(raw);
    return Number.isFinite(value) && value > 0 ? value : 15;
  }

  _ringColor(pct) {
    const threshold = this._lowThreshold();
    if (pct === null) return "var(--primary-text-color, #9e9e9e)";
    if (pct <= threshold) return "var(--error-color, #e54448)";
    if (pct <= Math.max(threshold * 2, 30)) return "var(--warning-color, #ffab40)";
    return "var(--success-color, #43b047)";
  }

  _title() {
    if (this._config.name) return this._config.name;
    const state = this._st(this._config.entity);
    const friendly = state && state.attributes ? state.attributes.friendly_name : null;
    if (friendly) {
      for (const tail of NAME_TAILS) {
        if (friendly.endsWith(" " + tail)) {
          return friendly.slice(0, friendly.length - tail.length - 1);
        }
      }
      return friendly;
    }
    return this._base().replace(/_/g, " ");
  }

  // ----------------------------------------------------------------- render

  /** Only re-render when something we show actually changed. */
  _signature() {
    const r = this._resolve();
    const part = (id) => {
      const state = this._st(id);
      if (!state) return "";
      const attrs = state.attributes || {};
      return [
        id,
        state.state,
        attrs.outlet_entity || "",
        attrs.threshold_pct || "",
        attrs.average_hours_per_day || "",
        attrs.installed_at || "",
        attrs.in_season === undefined ? "" : String(attrs.in_season),
        attrs.on_time || "",
        attrs.off_time || "",
      ].join("=");
    };
    return [
      this._confirmReset ? 1 : 0,
      part(r.pct),
      part(r.days),
      part(r.runtime),
      part(r.used),
      part(r.empty),
      part(r.reset),
      part(r.schedule),
      part(r.low),
      part(r.outlet),
    ].join("|");
  }

  _render() {
    if (!this._hass) return;

    if (!this._config.entity) {
      this._rendered = null;
      this.shadowRoot.innerHTML = `
        <style>${STYLE}</style>
        <ha-card>
          <div class="card placeholder">
            Mosquito Diffuser card — set <code>entity:</code> to one of its sensors
          </div>
        </ha-card>`;
      return;
    }

    const signature = this._signature();
    if (signature === this._rendered) return;
    this._rendered = signature;

    const r = this._resolve();
    const pct = this._pctValue();
    const title = this._title();
    const icon = this._config.icon || DEFAULT_ICON;

    const outletState = this._st(r.outlet);
    const outletOn = !!outletState && outletState.state === "on";
    const lowState = this._st(r.low);
    const lowOn = !!lowState && lowState.state === "on";
    const scheduleState = this._st(r.schedule);
    const schedulePaused = !!scheduleState && scheduleState.state === "off";
    const inSeason =
      !scheduleState ||
      !scheduleState.attributes ||
      scheduleState.attributes.in_season !== false;
    const daysState = this._st(r.days);
    const daysAttrs = (daysState && daysState.attributes) || {};

    const statRow = (label, value, entityId) =>
      `<div class="stat${entityId ? " clickable" : ""}"` +
      `${entityId ? ` data-entity="${esc(entityId)}"` : ""}>` +
      `<span class="stat-label">${esc(label)}</span>` +
      `<span class="stat-value">${esc(value)}</span></div>`;

    // Fractions for the tile mini-bars (0–100, null = unknown → no bar).
    const clampPct = (v) => Math.max(0, Math.min(100, v));
    const numState = (id) => {
      const s = this._st(id);
      if (!s) return null;
      const v = Number(s.state);
      return Number.isFinite(v) ? v : null;
    };
    const lifeHours = Number(daysAttrs.rated_life_hours) || null;
    const usedH = numState(r.used);
    const remH = numState(r.runtime);
    const daysLeft = numState(r.days);
    let daysInstalled = null;
    if (daysAttrs.installed_at) {
      const t = new Date(String(daysAttrs.installed_at).replace(" ", "T")).getTime();
      if (!isNaN(t)) daysInstalled = Math.max((Date.now() - t) / 86400000, 0);
    }
    const usedPct = lifeHours && usedH !== null ? clampPct((usedH / lifeHours) * 100) : null;
    const remPct =
      lifeHours && remH !== null ? clampPct((remH / lifeHours) * 100) : this._pctValue();
    const daysElapsedPct =
      daysInstalled !== null && daysLeft !== null && daysInstalled + daysLeft > 0
        ? clampPct((daysInstalled / (daysInstalled + daysLeft)) * 100)
        : null;

    const tileRow = (label, value, entityId, frac, ring) =>
      `<div class="tile${entityId ? " clickable" : ""}"` +
      `${entityId ? ` data-entity="${esc(entityId)}"` : ""}>` +
      `<div class="tile-top">` +
      `<span class="tile-label">${esc(label)}</span>` +
      `<span class="tile-value">${esc(value)}</span></div>` +
      (frac === null
        ? ""
        : `<div class="tile-bar"><div class="tile-fill"` +
          ` style="width:${frac}%; --ring:${ring}"></div></div>`) +
      `</div>`;

    const stats =
      this._config.stats === "plain"
        ? statRow("Days left", this._days() || "—", r.days) +
          statRow("Runtime left", this._hours(r.runtime) || "—", r.runtime) +
          statRow("Used", this._hours(r.used) || "—", r.used)
        : tileRow(
            "Days left",
            this._days() || "—",
            r.days,
            daysElapsedPct,
            this._ringColor(daysElapsedPct === null ? null : 100 - daysElapsedPct)
          ) +
          tileRow(
            "Runtime left",
            this._hours(r.runtime) || "—",
            r.runtime,
            remPct,
            this._ringColor(remPct)
          ) +
          tileRow(
            "Used",
            this._hours(r.used) || "—",
            r.used,
            usedPct,
            this._ringColor(usedPct === null ? null : 100 - usedPct)
          );

    const metaBits = [];
    const emptyState = this._st(r.empty);
    const emptyDate = this._fmtDate(emptyState && emptyState.state);
    if (emptyDate) {
      metaBits.push(
        `<span class="meta-item" data-entity="${esc(r.empty)}">` +
          `<ha-icon icon="mdi:calendar-remove"></ha-icon>Est. empty ${esc(emptyDate)}</span>`
      );
    }
    const installedDate = this._fmtDate(daysAttrs.installed_at);
    if (installedDate) {
      metaBits.push(
        `<span class="meta-item" data-entity="${esc(r.days)}">` +
          `<ha-icon icon="mdi:calendar"></ha-icon>Installed ${esc(installedDate)}</span>`
      );
    }
    const avgPerDay = Number(daysAttrs.average_hours_per_day);
    if (Number.isFinite(avgPerDay) && avgPerDay > 0) {
      metaBits.push(
        `<span class="meta-item" data-entity="${esc(r.days)}">` +
          `≈ ${this._num(avgPerDay)} h/day</span>`
      );
    }
    const schedAttrs = (scheduleState && scheduleState.attributes) || {};
    if (schedAttrs.on_time && schedAttrs.off_time) {
      const span = monthsSpan(schedAttrs.active_months);
      metaBits.push(
        `<span class="meta-item" data-entity="${esc(r.schedule)}">` +
          `<ha-icon icon="mdi:clock-outline"></ha-icon>` +
          `${esc(schedAttrs.on_time)} → ${esc(schedAttrs.off_time)}` +
          (span ? ` · ${esc(span)}` : "") +
          `</span>`
      );
    }
    if (r.level) {
      metaBits.push(
        `<span class="meta-item" data-entity="${esc(r.level)}">` +
          `<ha-icon icon="mdi:tune"></ha-icon>Calibrate</span>`
      );
    }

    const banner = lowOn
      ? `<div class="banner" data-entity="${esc(r.low)}">` +
        `<ha-icon icon="mdi:alert"></ha-icon>Low cartridge — replace soon</div>`
      : "";

    const subtitle =
      (outletState ? (outletOn ? "Diffusing now" : "Off") : "—") +
      (schedulePaused ? " · schedule paused" : "") +
      (!schedulePaused && !inSeason ? " · out of season" : "");

    const actions = [];
    if (r.reset) {
      actions.push(
        `<button class="action${this._confirmReset ? " warn" : ""}" data-action="reset">` +
          `<ha-icon icon="mdi:autorenew"></ha-icon>` +
          `<span>${this._confirmReset ? "Tap again to confirm" : "New cartridge"}</span></button>`
      );
    }
    if (r.schedule) {
      const on = scheduleState && scheduleState.state === "on";
      actions.push(
        `<button class="action${on ? " active" : ""}" data-action="schedule">` +
          `<ha-icon icon="mdi:calendar-clock"></ha-icon>` +
          `<span>${on ? "Schedule on" : "Schedule paused"}</span></button>`
      );
    }
    if (r.outlet) {
      actions.push(
        `<button class="action${outletOn ? " active" : ""}" data-action="outlet">` +
          `<ha-icon icon="mdi:power"></ha-icon>` +
          `<span>Outlet ${outletOn ? "on" : "off"}</span></button>`
      );
    }

    const gaugeValue =
      pct === null
        ? `<span class="num">—</span>`
        : `<span class="num">${Math.round(pct)}</span><span class="unit">%</span>`;

    const gauge =
      this._config.gauge === "donut"
        ? `<div class="donut" data-entity="${esc(r.pct)}"
               style="--pct:${pct === null ? 0 : pct}; --ring:${this._ringColor(pct)}">
             <div class="donut-value">${gaugeValue}</div>
             <div class="donut-label">cartridge left</div>
           </div>`
        : `<div class="vbar" data-entity="${esc(r.pct)}"
               style="--pct:${pct === null ? 0 : pct}; --ring:${this._ringColor(pct)}">
             <div class="vbar-track">
               <div class="vbar-fill"></div>
               <i class="vbar-tick" style="bottom:25%"></i>
               <i class="vbar-tick" style="bottom:50%"></i>
               <i class="vbar-tick" style="bottom:75%"></i>
             </div>
             <div class="vbar-value">${gaugeValue}</div>
             <div class="vbar-label">cartridge left</div>
           </div>`;

    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="card">
          <div class="header" data-entity="${esc(r.pct)}">
            <ha-icon class="header-icon" icon="${esc(icon)}"></ha-icon>
            <div class="header-text">
              <div class="title">${esc(title)}</div>
              <div class="subtitle">
                <span class="dot ${outletOn ? "on" : "off"}"></span>${esc(subtitle)}
              </div>
            </div>
          </div>
          ${banner}
          <div class="main">
            ${gauge}
            <div class="stats">${stats}</div>
          </div>
          ${metaBits.length ? `<div class="meta">${metaBits.join("")}</div>` : ""}
          ${actions.length ? `<div class="actions">${actions.join("")}</div>` : ""}
        </div>
      </ha-card>`;
  }

  // ---------------------------------------------------------------- actions

  _onClick(event) {
    const target = event.target
      ? event.target.closest("[data-entity], [data-action]")
      : null;
    if (!target) return;

    const action = target.getAttribute("data-action");
    if (action === "reset") {
      this._onResetAction();
      return;
    }
    if (action === "schedule" || action === "outlet") {
      const r = this._resolve();
      if (action === "schedule" && r.schedule) {
        this._hass.callService("switch", "toggle", { entity_id: r.schedule });
      } else if (action === "outlet" && r.outlet) {
        // homeassistant.toggle works for switch/light/fan/humidifier alike.
        this._hass.callService("homeassistant", "toggle", { entity_id: r.outlet });
      }
      return;
    }

    const entityId = target.getAttribute("data-entity");
    if (entityId) {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", {
          bubbles: true,
          composed: true,
          detail: { entityId },
        })
      );
    }
  }

  /** Two-tap confirmation for the destructive reset action. */
  _onResetAction() {
    const resetEntity = this._resolve().reset;
    if (!this._confirmReset) {
      this._confirmReset = true;
      this._rendered = null;
      this._render();
      clearTimeout(this._confirmTimer);
      this._confirmTimer = setTimeout(() => {
        this._confirmReset = false;
        this._rendered = null;
        this._render();
      }, 5000);
      return;
    }
    clearTimeout(this._confirmTimer);
    this._confirmReset = false;
    this._hass.callService("button", "press", { entity_id: resetEntity });
    this._rendered = null;
    this._render();
  }

  disconnectedCallback() {
    clearTimeout(this._confirmTimer);
  }
}

customElements.define("mosquito-diffuser-card", MosquitoDiffuserCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "mosquito-diffuser-card",
  name: "Mosquito Diffuser Card",
  description:
    "Cartridge gauge and quick actions for the Mosquito Diffuser integration.",
});

console.info(
  `%c 🦟 mosquito-diffuser-card %c ${CARD_VERSION} `,
  "background: #37474f; color: #fff; border-radius: 3px 0 0 3px; padding: 2px 4px;",
  "background: #43b047; color: #fff; border-radius: 0 3px 3px 0; padding: 2px 4px;"
);