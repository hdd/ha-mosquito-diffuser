# AGENTS.md — guide for coding agents

Working notes for AI agents (and humans) touching this repo. Keep it current
with every release; it is the first file any agent reads.

## What this is

A Home Assistant custom integration + companion Lovelace card that tracks the
consumption of an anti-mosquito liquid diffuser cartridge. Usage is counted
from the outlet's on/off state only (no recorder/history dependency), and the
integration can also switch the outlet on a schedule restricted to the
mosquito season (active months).

Current version lives in two places (bump both together — see Release
checklist): `custom_components/mosquito_diffuser/manifest.json` and
`CARD_VERSION` in the card JS.

## Layout

```
custom_components/mosquito_diffuser/
  manifest.json        domain, version (bump on release)
  const.py             DOMAIN, config keys, presets, tick/persist intervals
  coordinator.py       the brain: accrual, persistence, schedule, derived values
  entity.py            MosquitoDiffuserEntity mixin (unique_id, device, push listener)
  sensor.py            used / remaining_runtime / remaining / days_left / estimated_empty
  button.py            button.<name>_new_cartridge  → async_reset_cartridge
  number.py            number.<name>_cartridge_level → async_set_level (calibrate)
  switch.py            switch.<name>_schedule         → async_set_schedule_active
  binary_sensor.py     binary_sensor.<name>_low (attrs: threshold_pct)
  config_flow.py       setup + options flow (presets, custom days×h/day, schedule)
  frontend.py          serves the card at /mosquito_diffuser/mosquito-diffuser-card.js
  frontend/mosquito-diffuser-card.js   the card (plain web component, no build)
hacs.json, info.md, README.md, assets/
tests/card-smoke.js    headless render test for the card (plain node)
```

## Architecture notes

- **Coordinator pattern, but push-based.** `MosquitoDiffuserCoordinator` is
  *not* a `DataUpdateCoordinator`; entities subscribe via
  `entity.py`'s `async_add_listener` and the coordinator calls `_publish()`
  on every change. Keep that shape when adding entities.
- **Accrual invariants:** `used + remaining = life_hours` exactly. Every
  on→off transition charges the finished ON span from `last_accrual`; a 60 s
  `TICK_INTERVAL` covers restarts/downtime. State is flushed to `.storage`
  (`Store`, `PERSIST_DELAY` = 60 s, plus on shutdown). Do not round before
  `_accrue` does (4 decimals).
- **Schedule seasonality:** out-of-season the schedule never switches the
  outlet *on*, but the *off* event still runs (safety net for a forgotten
  outlet). `in_season` and `active_months` are exposed as switch attributes.
- **`days_left`** divides by measured `avg_hours_per_day`, with a conservative
  24 h/day fallback until real usage exists — that's why forecasts look
  pessimistic right after a calibration.
- **Calibration** (`async_set_level`) backdates `installed_at` assuming
  24 h/day pace. Same for reset (`async_reset_cartridge`).

## Card conventions (frontend/mosquito-diffuser-card.js)

- Plain web component, no build step, no dependencies. ES2020+ is fine.
- **Escape everything user-visible** with `esc()` before template insertion.
- One delegated click listener on the shadow root (`_onClick`); actions are
  data attributes (`data-action="reset|schedule|outlet"`, `data-entity`).
- Only re-render when the `_signature()` actually changes — keep new visible
  state in the signature.
- Sibling entities are auto-detected from the base id (`SUFFIXES` list,
  longest first); every one can be overridden in config. Keep the
  `SUFFIXES` / `NAME_TAILS` / options docs (README table) in sync.
- Stat tiles render a single split bar for used/left hours (they are
  complementary) — do not split them back into two tiles.
- Bump `CARD_VERSION` with any card change.

## Docs to keep in sync

| File | Content |
|---|---|
| `README.md` | Full user manual: features, entities table, setup, card options |
| `info.md` | HACS blurb shown in the store UI |
| `hacs.json` | HACS metadata (`homeassistant` = min HA version) |
| `manifest.json` | HA integration metadata + version |
| `AGENTS.md` | This file |

## Testing

No pytest/test framework — the card is verified headlessly with plain node:

```bash
node tests/card-smoke.js
```

It stubs `HTMLElement`/shadow DOM, feeds canned entity states into the card,
and asserts the rendered markup (tiles, fallbacks, ring colors). Extend it
for any new card feature. Python side has no automated tests; validate
changes by loading the integration in a dev HA or by careful review.

## Release checklist

1. Bump version in `manifest.json` **and** `CARD_VERSION` in the card JS.
2. Update `README.md` / `info.md` / `AGENTS.md` for any behavior change.
3. `node tests/card-smoke.js` → all OK.
4. Commit, tag `vX.Y.Z`, and push:
   `git add -A && git commit -m "..." && git tag vX.Y.Z && git push github main && git push github vX.Y.Z`
   - The `github` remote is the publishing one (HACS pulls releases from it).
   - `git push origin` (Gitea) fails auth from this machine — don't block on it.
5. Deploy to HA (see below) and hard-refresh the dashboard so the browser
   picks up the new card JS.

## Home Assistant instance

- **Host:** `home-assistant-green-os` @ `192.168.1.12` (HAOS, per RackPeek
  inventory; `rackpeek.export_ssh_config` renders the Host block).
- SSH from this workstation is currently *not* configured for agents
  (BatchMode probes fail — add a key/user before attempting
  `ssh root@192.168.1.12 "ha core ..."`).
- Deploy paths: **HACS → update** (preferred; picks up the new GitHub tag),
  then restart HA; or manual copy of
  `custom_components/mosquito_diffuser/` into `/config/custom_components/`.
- After restart, the card is served by the integration itself at
  `/mosquito_diffuser/mosquito-diffuser-card.js` — the Lovelace resource
  registration is a one-time thing.

## Gotchas

- `git status` may show `__pycache__/` noise — it's untracked, ignore it.
- aiohttp refuses new static routes after startup: `frontend.py` logs a
  warning and serves the card only after the next restart. Expect that on a
  first install (the HACS flow restarts anyway).
- The integration uses only custom `const.py` keys — never import
  `CONF_CUSTOM_DAYS`/`CONF_CUSTOM_HPD` from `homeassistant.helpers` (past
  bug: dialog 500s from that exact mixup).
