/* ============================================================
   EMOS-UI DATA LAYER  —  the single swappable seam between the
   UI and its data source.

   DEFAULT = "sim": every method returns the bundled simulated data
   (form-data.js / cif-samples.js), so the app behaves exactly as the
   demo build does today and needs no network at all. This keeps the
   showcase build safe.

   LIVE   = the same methods hit the real Flask backend
   (aprilaihub/EMOS, backend/app.py). Opt in WITHOUT touching code:
       ?live=1                     -> live mode for this load
       ?api=https://host           -> set the backend base URL
   or persist:  localStorage.emos_live = "1"; localStorage.emos_api = "https://host"

   Nothing here runs the live path unless you opt in, so it cannot
   affect the Friday demo. The live fetches are written against the
   documented routes but have NOT been tested against a running
   backend yet — see BACKEND_INTEGRATION_PLAN.md. Points that still
   need confirmation from the team are marked  // CONFIRM.
   ============================================================ */
(function () {
  "use strict";

  const qs = new URLSearchParams(location.search);
  const LIVE = qs.get("live") === "1" || localStorage.getItem("emos_live") === "1";
  // CONFIRMED live 2026-07-21: https://emos-backend.onrender.com (/api/health -> {"status":"ok"}).
  // Note: Render free services sleep after inactivity; first call can take ~30-60s to wake.
  const BASE = qs.get("api") || localStorage.getItem("emos_api") || "https://emos-backend.onrender.com";

  // CONFIRM: UI unit id  ->  backend IU class_name (used by /api/process/toggle_IU).
  // Best-guess PascalCase; verify each against Information_Units/*/*.py.
  const CLASS_NAMES = {
    cod: "COD", materialsproject: "MaterialsProject", alexandria: "Alexandria",
    mathub3d: "Mathub3D", jarvisdft: "JarvisDFT", aflow: "AFLOW",
    mattersim: "MatterSim", synthnn: "SynthNN", gbfs: "GBFS", gbfs_2d: "GBFS2D",
    chgnet: "CHGNet", // added by the team (PR #32)
    // generators (mg_*) map to their MatterGen classes — CONFIRM names.
  };

  // CONFIRMED from live GET /api/features/info (2026-07-21):
  //   1 Database Extractor · 2 Stability Consensus · 3 AMD Screening · 4 MOSFET Evaluator
  const FEATURE_IDS = { db_extract: 1, stability_consensus: 2, amd_screening: 3, mosfet_eval: 4 };

  async function req(path, opts) {
    const r = await fetch(BASE + path, Object.assign({
      headers: { "Content-Type": "application/json" },
    }, opts));
    if (!r.ok) throw new Error("EMOS backend " + r.status + " on " + path);
    return r.json();
  }

  // Adapt a raw backend candidate record to the shape the UI renders.
  // CONFIRM every field name once a real response is in hand.
  function normalizeCandidate(raw, i) {
    return {
      id: raw.id || raw.material_id || ("c" + i),
      formula: raw.formula || raw.pretty_formula || raw.composition || "—",
      symbol: raw.symbol || (raw.formula || "?").slice(0, 2),
      source: raw.source || raw.database || "",
      bandgap: raw.bandgap != null ? raw.bandgap : (raw.band_gap != null ? raw.band_gap : null),
      lo: raw.lo != null ? raw.lo : raw.bandgap_lo,
      hi: raw.hi != null ? raw.hi : raw.bandgap_hi,
      formationE: raw.formationE != null ? raw.formationE : raw.formation_energy,
      stability: raw.stability || raw.stability_label,
      cif: raw.cif || raw.cif_string || null,
    };
  }

  const EmosAPI = {
    mode: LIVE ? "live" : "sim",
    base: BASE,
    results: null,          // last run's candidate rows (null => UI falls back to CANDIDATES)
    online: null,           // last health() result

    isLive() { return this.mode === "live"; },

    async health() {
      if (!this.isLive()) { this.online = true; return { status: "sim" }; }
      try { const j = await req("/api/health"); this.online = j.status === "ok"; return j; }
      catch (e) { this.online = false; return { status: "down", error: String(e) }; }
    },

    async featuresInfo() {
      if (!this.isLive()) return (typeof FEATURES !== "undefined") ? FEATURES : [];
      return req("/api/features/info");           // GET
    },

    // Activate/deactivate an IU on the backend to match a sidebar toggle.
    // Real payload (from the live frontend): { class_name, class_type, active }.
    async toggleIU(unitId, unitType, active) {
      if (!this.isLive()) return { ok: true };
      const class_name = CLASS_NAMES[unitId] || unitId;
      return req("/api/process/toggle_IU", { method: "POST", body: JSON.stringify({ class_name, class_type: unitType, active }) });
    },

    // Run a whole Feature. Backend returns { results, logs, architecture };
    // `results` is feature-specific, so normalize whatever array it carries.
    async runFeature(feature, params) {
      if (!this.isLive()) { this.results = null; return (typeof CANDIDATES !== "undefined") ? CANDIDATES : []; }
      const fid = FEATURE_IDS[feature.id];
      const raw = await req("/api/process/" + fid, { method: "POST", body: JSON.stringify(params || {}) });
      const arr = Array.isArray(raw.results) ? raw.results : (raw.results && raw.results.candidates) || raw.candidates || [];
      const rows = arr.map(normalizeCandidate);
      this.results = rows.length ? rows : null;   // null => UI keeps the sample data
      return rows;
    },

    // Run a single Information Unit (used by the node editor).
    async runIU(iuType, iuId, inputs) {
      if (!this.isLive()) { this.results = null; return (typeof CANDIDATES !== "undefined") ? CANDIDATES : []; }
      const raw = await req("/api/process/iu/" + iuType + "/" + iuId, { method: "POST", body: JSON.stringify(inputs || {}) });
      const arr = Array.isArray(raw.results) ? raw.results : (raw.results && raw.results.candidates) || raw.candidates || raw.cif_strings || [];
      const rows = arr.map(normalizeCandidate);
      this.results = rows.length ? rows : null;
      return rows;
    },

    // LLM assistant — KEY-READY. Returns the reply text, or null (=> the UI
    // keeps its built-in canned replies, so the demo works with no key).
    //
    // Configure ONE of these (query param or localStorage), then it just works:
    //   A) Hub proxy (SAFEST — no key in the browser):
    //        localStorage.emos_llm_proxy = "https://<aisha-endpoint>"
    //      POSTs { prompt, context } and expects { reply } or { text } back.
    //   B) Direct OpenAI-compatible key (fine for a local demo; the key is
    //      visible to anyone using the page, so don't ship it on a public site):
    //        localStorage.emos_llm_key   = "sk-..."
    //        localStorage.emos_llm_url   = "https://api.openai.com/v1/chat/completions"  (default)
    //        localStorage.emos_llm_model = "gpt-4o-mini"                                  (default)
    //   C) Backend proxy route on the EMOS Flask server: /api/assistant.
    async assistant(prompt, context) {
      const sys = "You are the EMOS assistant, helping a materials scientist compose and run " +
        "AI-driven materials-discovery pipelines (databases, generators, predictors, features). " +
        "Be concise and practical." + (context ? " Current context: " + context : "");
      const proxy = qs.get("llm") || localStorage.getItem("emos_llm_proxy");
      const key = localStorage.getItem("emos_llm_key");
      try {
        // A) hub proxy
        if (proxy) {
          const j = await (await fetch(proxy, { method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt, context, system: sys }) })).json();
          return j.reply || j.text || j.message || (j.choices && j.choices[0] && (j.choices[0].message ? j.choices[0].message.content : j.choices[0].text)) || null;
        }
        // B) direct OpenAI-compatible key
        if (key) {
          const url = localStorage.getItem("emos_llm_url") || "https://api.openai.com/v1/chat/completions";
          const model = localStorage.getItem("emos_llm_model") || "gpt-4o-mini";
          const j = await (await fetch(url, { method: "POST",
            headers: { "Content-Type": "application/json", "Authorization": "Bearer " + key },
            body: JSON.stringify({ model, messages: [{ role: "system", content: sys }, { role: "user", content: prompt }] }) })).json();
          return (j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content) || null;
        }
        // C) backend proxy route (only when live)
        if (this.isLive()) {
          const j = await req("/api/assistant", { method: "POST", body: JSON.stringify({ prompt, context, system: sys }) });
          return j.reply || j.text || null;
        }
      } catch (e) { /* fall through to canned replies */ }
      return null;
    },
  };

  window.EmosAPI = EmosAPI;

  // Live-only connection badge (top-right). Never renders in sim mode, so the
  // showcase build is untouched. Lets the morning see at a glance whether the
  // backend is reachable.
  function mountBadge() {
    if (!EmosAPI.isLive()) return;
    const el = document.createElement("div");
    el.id = "emosConn";
    el.style.cssText = "position:fixed;top:10px;right:12px;z-index:9999;font:600 12px/1 -apple-system,Segoe UI,sans-serif;" +
      "padding:6px 10px;border-radius:999px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.15);display:flex;align-items:center;gap:7px;";
    el.innerHTML = '<span style="width:8px;height:8px;border-radius:50%;background:#d9a441;"></span><span>connecting…</span>';
    document.body.appendChild(el);
    EmosAPI.health().then((h) => {
      const ok = h.status === "ok";
      el.querySelector("span:first-child").style.background = ok ? "#16a34a" : "#c8241a";
      el.querySelector("span:last-child").textContent = ok ? "live backend" : "backend offline (using samples)";
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountBadge);
  else mountBadge();
})();
