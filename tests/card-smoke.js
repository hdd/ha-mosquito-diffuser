/* Headless smoke test for the bundled card — run with plain node:
 *
 *   node tests/card-smoke.js
 *
 * Stubs HTMLElement/shadow DOM, feeds canned entity states into the card
 * and asserts the rendered markup: merged used/left tile (tiles + plain),
 * fallbacks when a sibling sensor is missing, ring colors and the
 * single-segment days tile.
 */
const fs = require("fs");
const path = require("path");

const cardSrc = fs.readFileSync(
  path.join(__dirname, "..", "custom_components", "mosquito_diffuser", "frontend", "mosquito-diffuser-card.js"),
  "utf8"
);

global.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = {
      _html: "",
      set innerHTML(v) { this._html = v; },
      get innerHTML() { return this._html; },
      addEventListener() {},
    };
    return this.shadowRoot;
  }
  dispatchEvent() {}
};
global.customElements = { define() {} };
global.window = { customCards: [] };

eval(cardSrc + "\n;globalThis.MosquitoDiffuserCard = MosquitoDiffuserCard;");

const mk = (state, attrs = {}) => ({ state: String(state), attributes: attrs });
const t0 = new Date(Date.now() - 60 * 86400000).toISOString().replace("Z", "");

const states = {
  "sensor.lounge_remaining": mk(17, { friendly_name: "Lounge Remaining" }),
  "sensor.lounge_days_left": mk(5.2, {
    rated_life_hours: 720,
    installed_at: t0,
    average_hours_per_day: 1.2,
    outlet_entity: "switch.lounge_plug",
  }),
  "sensor.lounge_remaining_runtime": mk(119.3),
  "sensor.lounge_used": mk(600.7),
  "sensor.lounge_estimated_empty": mk("2026-11-08 09:30:00"),
  "button.lounge_new_cartridge": mk(""),
  "number.lounge_cartridge_level": mk(100),
  "switch.lounge_schedule": mk("on", { in_season: true, on_time: "22:00", off_time: "08:00", active_months: [4, 5, 6, 7, 8, 9, 10] }),
  "binary_sensor.lounge_low": mk("off", { threshold_pct: 15 }),
  "switch.lounge_plug": mk("on"),
};

const boot = (config) => {
  const el = new MosquitoDiffuserCard();
  el.setConfig(config);
  el.hass = { states, locale: { language: "en" }, callService() {} };
  return el.shadowRoot.innerHTML;
};

let failures = 0;
const check = (name, ok) => {
  console.log(`${name} -> ${ok ? "OK" : "FAIL"}`);
  if (!ok) failures++;
};

// 1. Default tiles mode — merged tile present, two segments
let html = boot({ entity: "sensor.lounge_remaining" });
check(
  "tiles: merged tile with 2 segments",
  /Used \/ left[\s\S]*?601 \/ 119 h[\s\S]*?tile-bar[\s\S]*?width:83\.4\d*%; --ring:rgba\(127,127,127,0\.55\)[\s\S]*?width:16\.5\d*%; --ring:var\(--warning-color/.test(html)
);
check("tiles: no separate Runtime/Used tiles", !/Runtime left|>Used</.test(html));

// 2. Plain mode — merged text row
html = boot({ entity: "sensor.lounge_remaining", stats: "plain" });
check("plain: merged row", /Used \/ left[\s\S]*?601 \/ 119 h/.test(html));

// 3. Missing runtime sensor — value falls back to "used", single segment
delete states["sensor.lounge_remaining_runtime"];
html = boot({ entity: "sensor.lounge_remaining" });
check("fallback: used-only value", /601 h used/.test(html));
check(
  "fallback: single segment bar",
  /tile-bar"><div class="tile-fill" style="width:[0-9.]+%; --ring:rgba\(127,127,127,0\.55\)"/.test(html)
);
states["sensor.lounge_remaining_runtime"] = mk(119.3);

// 4. Missing used sensor — "left" value, remaining-colored segment only
delete states["sensor.lounge_used"];
html = boot({ entity: "sensor.lounge_remaining" });
check("fallback: rem-only value", /119 h left/.test(html));
check(
  "fallback: rem segment uses pct fallback",
  /tile-fill" style="width:[0-9.]+%; --ring:var\(--warning-color/.test(html)
);
states["sensor.lounge_used"] = mk(600.7);

// 5. Low cartridge — remaining segment turns red
states["sensor.lounge_remaining"] = mk(8, {});
states["sensor.lounge_days_left"] = mk(2.4, { rated_life_hours: 720, installed_at: t0, average_hours_per_day: 1.2, outlet_entity: "switch.lounge_plug" });
states["sensor.lounge_remaining_runtime"] = mk(57.6);
states["sensor.lounge_used"] = mk(662.4);
html = boot({ entity: "sensor.lounge_remaining" });
check(
  "low: rem segment red",
  /rgba\(127,127,127,0\.55\)[\s\S]*?width:[0-9.]+%; --ring:var\(--error-color/.test(html)
);

// 6. Days tile unchanged (single segment)
html = boot({ entity: "sensor.lounge_remaining" });
check(
  "days tile: single segment",
  /Days left[\s\S]*?tile-bar"><div class="tile-fill" style="width:[0-9.]+%; --ring:var\(--[a-z]+-color[^"]*"><\/div><\/div>/.test(html)
);

process.exit(failures ? 1 : 0);
