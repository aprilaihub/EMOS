/* ============================================================
   EMOS Form Page — application logic (vanilla JS)
   ============================================================ */
(function () {
  "use strict";

  /* ---------- state ---------- */
  const state = {
    selected: { database: new Set(), generator: new Set(), predictor: new Set() },
    activeFeature: null,
    run: "idle",            // idle | running | done
    hasResults: false,
    selCandidate: null,
    tab: "table",
    filter: "",
    typeFilter: "all",
    pins: new Set(JSON.parse(sessionStorage.getItem("emos_pins") || "[]")),
    notes: JSON.parse(sessionStorage.getItem("emos_notes") || "{}"),
    names: JSON.parse(sessionStorage.getItem("emos_names") || "{}"),
    commentFor: null,
    showPinnedOnly: false,
    welcomeDismissed: localStorage.getItem("emos_welcome_dismissed") === "1",
    activeUnit: null,   // { type, id } when an IU is open in the main panel
    user: JSON.parse(localStorage.getItem("emos_user") || "null"),
    view: "form",       // "form" | "node" — which surface fills the main panel
  };
  const persist = () => {
    sessionStorage.setItem("emos_pins", JSON.stringify([...state.pins]));
    sessionStorage.setItem("emos_notes", JSON.stringify(state.notes));
    sessionStorage.setItem("emos_names", JSON.stringify(state.names));
  };
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const featureById = (id) => FEATURES.find((f) => f.id === id);
  const unitName = (type, id) => UNITS[type].items.find((u) => u.id === id)?.name || id;

  /* =========================================================
     SIDEBAR — type filter chips (All / DB / Gen / Pred)
     ========================================================= */
  function renderTypeChips() {
    const wrap = $("#typeChips");
    const chips = [
      { key: "all", label: "All", n: UNITS.database.items.length + UNITS.generator.items.length + UNITS.predictor.items.length, dot: null },
      { key: "database", label: "DB", n: UNITS.database.items.length, dot: "database" },
      { key: "generator", label: "Gen", n: UNITS.generator.items.length, dot: "generator" },
      { key: "predictor", label: "Pred", n: UNITS.predictor.items.length, dot: "predictor" },
    ];
    wrap.innerHTML = chips.map((c) =>
      `<button class="type-chip${state.typeFilter === c.key ? " active" : ""}" data-type="${c.key}">
        ${c.dot ? `<span class="tc-dot dot ${c.dot}"></span>` : ""}${c.label} <span class="tc-n">${c.n}</span></button>`).join("");
    wrap.querySelectorAll("[data-type]").forEach((b) =>
      b.addEventListener("click", () => { state.typeFilter = b.dataset.type; renderTypeChips(); renderUnits(); }));
  }

  /* =========================================================
     SIDEBAR — units
     ========================================================= */
  function renderUnits() {
    const wrap = $("#unitScroll");
    wrap.innerHTML = "";
    // Determine which unit type the active feature requires. In node view
    // nothing is dimmed: every unit is a drag source for the canvas.
    const activeFeature = state.activeFeature != null ? featureById(state.activeFeature) : null;
    const requiredType = (state.view !== "node" && activeFeature) ? activeFeature.uses : null;

    ["database", "generator", "predictor"].forEach((type) => {
      if (state.typeFilter !== "all" && state.typeFilter !== type) return;
      const grp = UNITS[type];
      const sel = state.selected[type];
      const visible = grp.items.filter((u) => u.name.toLowerCase().includes(state.filter));
      if (!visible.length) return;

      // Dim entire section if a feature is open and this type is not required
      const isDimmed = requiredType !== null && requiredType !== type;
      const section = el("div", "unit-section" + (isDimmed ? " unit-section--dimmed" : ""));
      const head = el("div", "section-head");
      head.innerHTML = `<span class="label">${grp.label}</span><span class="spacer"></span>
        ${isDimmed ? `<span class="not-used-badge">not used</span>` : ""}`;
      section.appendChild(head);

      visible.forEach((u) => {
        const on = sel.has(u.id);
        const row = el("div", "unit-row" + (on ? " selected" : "") + (isDimmed ? " unit-row--dimmed" : ""));
        row.dataset.toggle = isDimmed ? "" : `${type}:${u.id}`;
        if (!isDimmed) { row.setAttribute("role", "button"); row.tabIndex = 0; row.setAttribute("aria-pressed", on ? "true" : "false"); }
        // Drag source for the Node Editor canvas. The node "kind" ids are
        // db:/gen:/pred: + unit id (see node-app.js KINDS); dropping one spawns
        // that node. Harmless in form mode (no drop target there).
        if (!isDimmed) {
          const prefix = { database: "db:", generator: "gen:", predictor: "pred:" }[type];
          row.setAttribute("draggable", "true");
          row.addEventListener("dragstart", (e) => {
            e.dataTransfer.setData("text/kind", prefix + u.id);
            e.dataTransfer.effectAllowed = "copy";
            row.classList.add("dragging");
          });
          row.addEventListener("dragend", () => row.classList.remove("dragging"));
        }
        // Sidebar shows the distinguishing part of the name; the shared
        // "MatterGen:" prefix otherwise truncates every generator identically.
        const shortName = u.name.replace(/^MatterGen:\s*/, "");
        row.innerHTML = `
          <span class="dot ${type}${on ? " dot-on" : ""}"></span>
          <span class="unit-name" title="${u.name}">${shortName}</span>
          ${u.desc ? `<button class="doc-icon" tabindex="0" aria-label="About ${u.name}" data-doc-title="${u.name}">?<span class="doc-desc">${u.desc}</span></button>` : ""}
          ${!isDimmed ? `<button class="open-btn" data-open="${type}:${u.id}">Open</button>` : ""}`;
        section.appendChild(row);
      });
      wrap.appendChild(section);
    });

    wrap.querySelectorAll(".unit-row[data-toggle]").forEach((row) => {
      row.style.cursor = "pointer";
      const toggle = (e) => {
        if (e.target.closest(".open-btn") || e.target.closest(".doc-icon")) return;
        const [type, id] = row.dataset.toggle.split(":");
        if (!type || !id) return;
        // In node view rows are drag sources only; clicking must not toggle
        // form selection or open a workspace hidden behind the canvas.
        if (state.view === "node") return;
        // If a unit workspace is already open, a row click navigates to that
        // unit (so the user is never trapped on the first one they opened).
        if (state.activeUnit) { openUnitWorkspace(type, id); return; }
        const set = state.selected[type];
        set.has(id) ? set.delete(id) : set.add(id);
        renderUnits(); updateTray(); updatePipeline(); renderWorkspace(); syncAIContext();
      };
      row.addEventListener("click", toggle);
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(e); }
      });
    });
    wrap.querySelectorAll("[data-open]").forEach((b) =>
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const [type, id] = b.dataset.open.split(":");
        openUnitWorkspace(type, id);
      })
    );
  }

  /* =========================================================
     SIDEBAR — features
     ========================================================= */
  function renderFeatures() {
    const wrap = $("#featureList");
    wrap.innerHTML = `<div class="section-head"><span class="label">Features</span></div>`;
    FEATURES.forEach((f) => {
      const active = state.activeFeature === f.id;
      const row = el("div", "feature-row" + (active ? " active" : ""));
      row.innerHTML = `
        <span class="fname">${f.name}</span>
        ${f.desc ? `<button class="doc-icon" tabindex="0" aria-label="About ${f.name}" data-doc-title="${f.name}">?<span class="doc-desc">${f.desc}</span></button>` : ""}
        <span class="ready-tag ${f.readyClass}">${f.ready}</span>
        <span class="chev">›</span>`;
      row.setAttribute("role", "button"); row.tabIndex = 0;
      row.addEventListener("click", (e) => { if (e.target.closest(".doc-icon")) return; openFeature(f.id); });
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); if (!e.target.closest(".doc-icon")) openFeature(f.id); }
      });
      wrap.appendChild(row);
    });
  }

  /* =========================================================
     TRAY + PIPELINE — removed. The bottom counts tray and the
     SOURCE/GENERATE/SCREEN/EVALUATE strip were redundant with the
     per-feature IU toggles, so these are now no-ops (kept so the many
     existing call sites don't each need touching).
     ========================================================= */
  function updateTray() {}
  function updatePipeline() {}

  /* =========================================================
     WORKSPACE ROUTER
     ========================================================= */
  function renderWorkspace() {
    if (state.activeUnit) return renderUnitWorkspace(state.activeUnit.type, state.activeUnit.id);
    state.activeFeature ? renderStateB(featureById(state.activeFeature)) : renderStateA();
  }

  /* ---------- STATE A : welcome ---------- */
  function renderStateA() {
    $("#crumbLeaf").textContent = "Form";
    const db = state.selected.database, gen = state.selected.generator, pred = state.selected.predictor;
    const inner = $("#wsInner");
    const totalSel = db.size + gen.size + pred.size;

    const welcomeHTML = (totalSel === 0 && !state.welcomeDismissed) ? `
      <div class="ws-welcome fade-in">
        <button class="ws-welcome-close" id="welcomeClose" title="Dismiss" aria-label="Dismiss">&times;</button>
        <div class="ws-welcome-body">
          <div class="ws-steps">
            <div class="ws-step"><span class="ws-step-n mono">01</span><span class="ws-step-t">Select units</span><span class="ws-step-d">Click databases, generators and predictors in the left panel to add them to your pipeline.</span></div>
            <div class="ws-step-arrow">›</div>
            <div class="ws-step"><span class="ws-step-n mono">02</span><span class="ws-step-t">Open a feature</span><span class="ws-step-d">Pick a feature (Database Extractor, Stability Consensus…) and configure its parameters.</span></div>
            <div class="ws-step-arrow">›</div>
            <div class="ws-step"><span class="ws-step-n mono">03</span><span class="ws-step-t">Run and explore</span><span class="ws-step-d">Launch the run, follow the live log, then browse ranked candidates as a table or 3D crystal.</span></div>
          </div>
          <button class="btn btn-primary ws-example-btn" id="tryExample">Try a worked example  →</button>
        </div>
      </div>` : "";

    const selNames = [
      ...[...db].map((id) => unitName("database", id)),
      ...[...gen].map((id) => unitName("generator", id)),
      ...[...pred].map((id) => unitName("predictor", id)),
    ];
    const bannerHTML = totalSel > 0 ? `
      <div class="ready-banner fade-in">
        <div class="rb-left">
          <span class="rb-dot"></span>
          <span class="rb-msg"><b>${totalSel} unit${totalSel > 1 ? "s" : ""} selected:</b> ${selNames.slice(0, 3).join(", ")}${selNames.length > 3 ? ` +${selNames.length - 3} more` : ""}. Now open a feature to run your pipeline.</span>
        </div>
      </div>` : "";

    // Features are always visible: cards whose required units are missing
    // stay clickable — the feature workspace guides selection inline.
    const featuresHTML = `
      <div class="avail-features fade-in">
        <div class="af-label">Features</div>
        <div class="af-grid">
          ${FEATURES.map((f) => {
            const ready = !f.uses || state.selected[f.uses].size > 0;
            return `
            <div class="af-card${ready ? "" : " af-preview"}" data-feat="${f.id}" role="button" tabindex="0">
              <div class="af-top"><span class="af-stage">${f.stage}</span>${ready ? "" : `<span class="af-req">needs ${f.uses}s</span>`}</div>
              <div class="af-name">${f.name}</div>
              <div class="af-desc">${f.desc.slice(0, 72)}…</div>
              <button class="btn ${ready ? "btn-primary" : "btn-ghost"} btn-sm af-open">Open →</button>
            </div>`;
          }).join("")}
        </div>
      </div>`;

    const searchHTML = `
      <div class="card search-panel">
        <div class="panel-label">Quick material search</div>
        <div class="search-row">
          <div class="field"><label>Composition</label><input class="input" id="mqComp" placeholder="e.g. Fe2O3"></div>
          <div class="field"><label>Database</label>
            <select class="select" id="mqDb"><option>All selected</option>${UNITS.database.items.map((u) => `<option>${u.name}</option>`).join("")}</select></div>
          <div class="field"><label>Max results</label><input class="input mono" id="mqMax" value="25"></div>
          <button class="btn btn-primary" id="mqGo">Search</button>
        </div>
        <div id="mqResults"></div>
      </div>`;

    inner.innerHTML = welcomeHTML + bannerHTML + featuresHTML + searchHTML;

    inner.querySelectorAll(".af-card").forEach((c) => {
      c.addEventListener("click", () => openFeature(c.dataset.feat));
      c.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openFeature(c.dataset.feat); } });
    });
    const mqGo = $("#mqGo"); if (mqGo) { mqGo.addEventListener("click", runMaterialSearch); $("#mqComp")?.addEventListener("keydown", (e) => { if (e.key === "Enter") runMaterialSearch(); }); }
    const te = $("#tryExample"); if (te) te.addEventListener("click", loadExample);
    const wc = $("#welcomeClose"); if (wc) wc.addEventListener("click", () => { state.welcomeDismissed = true; localStorage.setItem("emos_welcome_dismissed", "1"); renderWorkspace(); });
  }

  function runMaterialSearch() {
    const comp = ($("#mqComp").value || "").trim().toLowerCase();
    const max = parseInt($("#mqMax").value, 10) || 25;
    let rows = resultRows().filter((c) => !comp || c.formula.toLowerCase().includes(comp)).slice(0, max);
    const out = $("#mqResults");
    if (!rows.length) { out.innerHTML = `<p style="font-size:13px;color:var(--text-muted);margin-top:16px;">No structures matched that composition.</p>`; return; }
    out.innerHTML = `<table class="rtable"><thead><tr>
        <th>Formula</th><th>ID</th><th>Source</th><th>Band gap</th><th>Stability</th></tr></thead>
      <tbody>${rows.map((c) => `<tr>
        <td class="mono" style="font-weight:600;">${fmt(c.formula)}</td>
        <td class="mono" style="color:var(--text-muted);">${c.id}</td>
        <td><span class="src-badge">${c.source}</span></td>
        <td class="mono">${c.val.toFixed(2)} eV</td>
        <td><span class="pill ${c.stability}">${cap(c.stability)}</span></td></tr>`).join("")}</tbody></table>`;
  }

  function loadExample() {
    state.selected.database = new Set(["materialsproject", "cod"]);
    state.selected.predictor = new Set(["mattersim", "synthnn"]);
    renderUnits(); updateTray(); updatePipeline();
    openFeature("db_extract");
  }

  /* ---------- STATE B : feature workspace ---------- */
  function renderStateB(f) {
    $("#crumbLeaf").textContent = f.name;
    const usesSet = f.uses ? state.selected[f.uses] : null;
    const ok = !f.uses || usesSet.size > 0;

    // Build inline IU toggle strip for this feature's required type
    // (the strip is the single representation of the selection — no duplicate chips row)
    const iuStrip = f.uses ? (() => {
      const items = UNITS[f.uses].items;
      const sel = state.selected[f.uses];
      const unitButtons = items.map((u) => `
        <button class="fus-unit${sel.has(u.id) ? " on" : ""}" data-fus="${f.uses}:${u.id}">
          <span class="fus-toggle"></span>
          <span class="dot ${f.uses}" style="width:8px;height:8px;border-radius:50%;flex-shrink:0"></span>
          ${u.name}
        </button>`).join("");
      const hint = f.uses === "predictor"
        ? "Each predictor runs on your structures; EMOS compares them for a consensus verdict."
        : f.uses === "database"
        ? "Selected databases are queried together and their results combined into one candidate pool."
        : "Selected units are used together in this feature.";
      return `<div class="feature-units-strip">
        <div class="fus-head">
          <span class="fus-label">${UNITS[f.uses].label} used by this feature</span>
        </div>
        <div class="fus-hint">${hint}</div>
        <div class="fus-units">${unitButtons}</div>
      </div>`;
    })() : "";

    const inner = $("#wsInner");
    inner.innerHTML = `
      <div class="page-head fade-in">
        <h1>${f.name}</h1>
        <p>${f.desc}</p>
      </div>
      ${iuStrip}
      <div class="two-col">
        <div class="card params-card">
          <h3>Parameters</h3>
          ${f.params.map(paramHTML).join("")}
          <details class="advanced">
            <summary><span class="arr">›</span> Advanced parameters</summary>
            <div class="adv-body">${f.advanced.map(paramHTML).join("")}</div>
          </details>
        </div>
        <div class="card controls-card">
          <h3>Run configuration</h3>
          <button class="btn btn-primary btn-lg" id="featRun"${ok ? "" : " disabled"}>▶ Run ${f.name}</button>
          <div class="run-status"><span class="run-dot" id="runDot"></span><span id="runText">Ready to run</span></div>
          <div class="run-stages" id="runStages"></div>
          <div class="progress-track" id="runTrack" hidden><div class="progress-fill" id="runFill"></div></div>
          <div class="run-log" id="runLog"></div>
          <div class="cfg-summary" id="cfgSummary"></div>
        </div>
      </div>
      <div id="resultsMount"></div>`;

    // sliders
    inner.querySelectorAll("input[type=range].slider").forEach((s) => {
      const out = inner.querySelector(`[data-val="${s.id}"]`);
      const upd = () => { out.textContent = formatVal(s.value, s.dataset.unit); paintSlider(s); updateCfg(f); };
      s.addEventListener("input", upd); paintSlider(s);
    });
    // Wire the inline IU toggle strip
    inner.querySelectorAll("[data-fus]").forEach((btn) =>
      btn.addEventListener("click", () => {
        const [type, id] = btn.dataset.fus.split(":");
        const set = state.selected[type];
        set.has(id) ? set.delete(id) : set.add(id);
        renderUnits(); updateTray(); updatePipeline(); renderWorkspace(); syncAIContext();
      })
    );
    $("#featRun").addEventListener("click", () => doRun(f));
    updateCfg(f);

    // restore prior run/results for this feature view
    if (state.hasResults) { renderResults(); }
    else { state.run = "idle"; }
  }

  function paramHTML(p) {
    if (p.kind === "slider") {
      return `<div class="slider-row">
        <div class="slider-top">
          <span class="s-name">${p.label}${p.unit ? ` <span class="unit">(${p.unit})</span>` : ""}</span>
          <span class="s-val mono" data-val="${p.id}">${formatVal(p.value, p.unit)}</span>
        </div>
        <input type="range" class="slider" id="${p.id}" data-unit="${p.unit}" min="${p.min}" max="${p.max}" step="${p.step}" value="${p.value}">
        <div class="slider-minmax"><span>${p.min}</span><span>${p.max}</span></div>
      </div>`;
    }
    if (p.kind === "text") {
      return `<div class="field-row"><label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:5px;">${p.label}</label>
        <input class="input" id="${p.id}" placeholder="${p.placeholder || ""}"></div>`;
    }
    if (p.kind === "select") {
      return `<div class="field-row"><label style="display:block;font-size:12px;color:var(--text-secondary);margin-bottom:5px;">${p.label}</label>
        <select class="select" id="${p.id}">${p.options.map((o) => `<option>${o}</option>`).join("")}</select></div>`;
    }
    return "";
  }

  function paintSlider(s) {
    const pct = ((s.value - s.min) / (s.max - s.min)) * 100;
    s.style.background = `linear-gradient(to right, var(--accent) 0 ${pct}%, var(--grey-200) ${pct}% 100%)`;
  }

  function updateCfg(f) {
    const root = $("#wsInner");
    const rows = [];
    f.params.forEach((p) => {
      const node = root.querySelector("#" + p.id);
      if (!node) return;
      const v = p.kind === "slider" ? formatVal(node.value, p.unit) : (node.value || "n/a");
      rows.push([p.label, v]);
    });
    if (f.uses) rows.unshift([UNITS[f.uses].label, state.selected[f.uses].size]);
    $("#cfgSummary").innerHTML = rows.map(([k, v]) =>
      `<div class="cfg-row"><span class="k">${k}</span><span class="v mono">${v}</span></div>`).join("");
  }

  /* =========================================================
     RUN sequence
     ========================================================= */
  // ---- data seam ---------------------------------------------------------
  // Results come from the live backend when EmosAPI has fetched some;
  // otherwise we fall back to the bundled simulated CANDIDATES, so the demo
  // build is unchanged. See data-layer.js / BACKEND_INTEGRATION_PLAN.md.
  function resultRows() {
    const api = window.EmosAPI;
    return (api && api.results && api.results.length) ? api.results : CANDIDATES;
  }
  function findCand(id) {
    return resultRows().find((x) => x.id === id) || CANDIDATES.find((x) => x.id === id);
  }
  // Params gathered for a live run. TODO(morning): map real slider/toggle
  // values + selected IU class names; {} is fine for the simulated build.
  function collectRunParams(f) {
    const p = {};
    if (f.uses) p.units = [...state.selected[f.uses]];
    return p;
  }

  function doRun(f) {
    if (f.uses && state.selected[f.uses].size === 0) {
      toast("warn", "Run blocked", `Select at least one ${f.uses} before running ${f.name}. EMOS will not return an empty result silently.`);
      return;
    }
    const dot = $("#runDot"), text = $("#runText"), fill = $("#runFill"), log = $("#runLog");
    state.run = "running"; state.hasResults = false;
    dot.className = "run-dot running"; text.textContent = "Running…";
    $("#runTrack").hidden = false;
    fill.style.width = "0%"; log.textContent = "";
    $("#featRun").disabled = true;
    // Citrine-style named stages
    const STAGES = ["Initialise", "Fetch", "Compute", "Score", "Rank"];
    const stagesEl = $("#runStages");
    const renderStages = (cur) => {
      stagesEl.innerHTML = STAGES.map((s, k) => {
        const cls = k < cur ? "done" : k === cur ? "active" : "";
        const ic = k < cur ? ICON.check : k === cur ? ICON.spinner : "";
        return `<span class="run-stage ${cls}">${ic ? `<span class="rs-icon">${ic}</span>` : ""}${s}</span>`;
      }).join("");
    };
    renderStages(0);
    const steps = [
      "Initialising " + f.name + "…",
      f.uses ? `Connecting to ${state.selected[f.uses].size} ${f.uses}(s)…` : "Loading device solver…",
      "Fetching candidate structures…",
      "Computing properties…",
      "Scoring stability consensus…",
      "Ranking candidates…",
      "Done. " + CANDIDATES.length + " structures returned.",
    ];
    let i = 0;
    const tick = () => {
      if (i < steps.length) {
        log.textContent += (i ? "\n" : "") + "› " + steps[i];
        log.scrollTop = log.scrollHeight;
        fill.style.width = Math.round(((i + 1) / steps.length) * 100) + "%";
        renderStages(Math.min(STAGES.length - 1, Math.round((i / (steps.length - 1)) * STAGES.length)));
        i++;
        setTimeout(tick, 380);
      } else {
        completeRun(f);
      }
    };
    tick();
  }
  // Fetch the run's results through the data seam, then render. In sim mode
  // EmosAPI.runFeature resolves instantly to CANDIDATES, so this is identical
  // to the old synchronous completion; in live mode it awaits the backend.
  async function completeRun(f) {
    const dot = $("#runDot"), text = $("#runText"), stagesEl = $("#runStages"), STAGES = ["Initialise", "Fetch", "Compute", "Score", "Rank"];
    try {
      await window.EmosAPI.runFeature(f, collectRunParams(f));
    } catch (e) {
      toast("warn", "Backend unavailable", "Could not reach the live backend; showing the bundled sample data.");
    }
    const rows = resultRows();
    state.run = "done"; state.hasResults = true;
    dot.className = "run-dot done"; text.textContent = "Completed";
    stagesEl.innerHTML = STAGES.map((s) => `<span class="run-stage done"><span class="rs-icon">${ICON.check}</span>${s}</span>`).join("");
    $("#featRun").disabled = false;
    renderResults();
    const rm = $("#resultsMount");
    if (rm) {
      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      rm.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
    }
    toast("ok", `${f.name} complete`, `${rows.length} structures returned and ranked by likelihood. Open the Plot or Crystal tab to explore.`);
  }

  /* =========================================================
     RESULTS (tabs)
     ========================================================= */
  function renderResults() {
    const mount = $("#resultsMount");
    mount.innerHTML = `
      <div class="card results-card fade-in">
        <div class="results-head">
          <div class="rh-left"><h3>Results</h3><span class="rh-count" id="rhCount"></span></div>
          <div class="rh-actions">
            <button class="rh-pinned${state.showPinnedOnly ? " active" : ""}" id="pinnedToggle" title="Show only pinned structures">${ICON.pin}<span>Pinned</span> <span class="rp-n" id="pinnedN">${state.pins.size}</span></button>
            <button class="btn btn-ghost btn-sm" id="resExpCsv">Export CSV</button>
            <button class="btn btn-ghost btn-sm" id="resExpCif">Download CIF</button>
          </div>
        </div>
        <div class="tabbar">
          <button class="tab${state.tab === "table" ? " active" : ""}" data-tab="table">Table</button>
          <button class="tab${state.tab === "plot" ? " active" : ""}" data-tab="plot">Plot</button>
          <button class="tab${state.tab === "crystal" ? " active" : ""}" data-tab="crystal">Crystal structure</button>
        </div>
        <div class="tab-panel" data-panel="table"${state.tab === "table" ? "" : " hidden"}></div>
        <div class="tab-panel" data-panel="plot"${state.tab === "plot" ? "" : " hidden"}></div>
        <div class="tab-panel" data-panel="crystal"${state.tab === "crystal" ? "" : " hidden"}></div>
        <div id="driversMount"></div>
      </div>`;
    mount.querySelectorAll(".tab").forEach((t) =>
      t.addEventListener("click", () => switchTab(t.dataset.tab)));
    $("#resExpCsv").addEventListener("click", () => {
      const rows = resultRows();
      downloadText(candidatesCSV(rows), "emos-results.csv", "text/csv");
      toast("ok", "Exported", `emos-results.csv with ${rows.length} structures downloaded.`);
    });
    $("#resExpCif").addEventListener("click", () => {
      const rows = resultRows();
      const c = (state.selCandidate && findCand(state.selCandidate)) || rows[0];
      const p = candidateCIF(c);
      if (!p) { toast("warn", "No structure", "Select a candidate with a crystal structure first."); return; }
      downloadText(p.cif, `${p.name.replace(/[^A-Za-z0-9]/g, "")}.cif`, "chemical/x-cif");
      toast("ok", "Downloaded", `${p.name} crystal structure saved as CIF.`);
    });
    const pt = $("#pinnedToggle");
    pt.addEventListener("click", () => {
      state.showPinnedOnly = !state.showPinnedOnly;
      pt.classList.toggle("active", state.showPinnedOnly);
      state.tab = "table";
      document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "table"));
      document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = p.dataset.panel !== "table"));
      renderTableTab(); updateRhCount();
    });
    renderTableTab(); renderPlotTab(); renderCrystalTab(); renderDrivers(); updateRhCount();
  }

  function updateRhCount() {
    const rc = $("#rhCount"); if (!rc) return;
    const n = state.showPinnedOnly ? state.pins.size : resultRows().length;
    rc.textContent = state.showPinnedOnly
      ? `Showing ${n} pinned structure${n === 1 ? "" : "s"}`
      : `Showing ${n} structures`;
    const pn = $("#pinnedN"); if (pn) pn.textContent = state.pins.size;
    const tp = $("#topPinN"); if (tp) { tp.textContent = state.pins.size; $("#topPin").classList.toggle("has", state.pins.size > 0); }
  }

  /* ---------- feature importance ("why these results") ---------- */
  function renderDrivers() {
    const mount = $("#driversMount");
    if (!mount) return;
    const f = state.activeFeature ? featureById(state.activeFeature) : null;
    const drivers = (f && DRIVERS[f.id]) || DRIVERS.db_extract;
    const top = Math.max(...drivers.map((d) => d.weight));
    mount.innerHTML = `<div class="drivers">
      <div class="drivers-head">
        <h4>What drove these results</h4>
      </div>
      <p class="drivers-sub">Relative influence of each input on the ranking. A green tag raises the score, a red tag lowers it.</p>
      ${drivers.map((d) => `<div class="driver-row">
        <span class="driver-name" title="${d.name}">${d.name}</span>
        <span class="driver-track"><span class="driver-fill" style="width:${(d.weight / top) * 100}%"></span></span>
        <span class="driver-pct">${Math.round(d.weight * 100)}%
          <span class="driver-dir ${d.dir === "+" ? "up" : "down"}">${d.dir}</span></span>
      </div>`).join("")}
    </div>`;
  }

  function switchTab(tab) {
    state.tab = tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === tab));
    document.querySelectorAll(".tab-panel").forEach((p) => (p.hidden = p.dataset.panel !== tab));
    if (tab === "crystal") renderCrystalTab();
  }

  function maxRange() {
    return Math.max(...resultRows().map((c) => c.hi));
  }

  /* Citrine-style likelihood score (0–1) derived from stability + uncertainty */
  const STAB_BASE = { stable: 0.86, marginal: 0.54, unstable: 0.24 };
  function candScore(c) {
    return Math.max(0.05, Math.min(0.99, STAB_BASE[c.stability] - c.err * 0.4));
  }
  function scoreColor(c) {
    return c.stability === "stable" ? "var(--status-stable)"
      : c.stability === "marginal" ? "var(--status-marginal)" : "var(--status-unstable)";
  }

  function renderTableTab() {
    const panel = document.querySelector('[data-panel="table"]');
    const mx = maxRange();
    let rows = [...resultRows()].sort((a, b) => candScore(b) - candScore(a));
    if (state.showPinnedOnly) rows = rows.filter((c) => state.pins.has(c.id));
    if (!rows.length) {
      panel.innerHTML = `<div style="padding:32px 8px;text-align:center;color:var(--text-muted);font-size:13px;">No pinned structures yet. Click the pin icon on any row to save it to your Pinned collection.</div>`;
      return;
    }
    panel.innerHTML = `<table class="cand-table"><thead><tr>
        <th>Score ↑</th><th>Structure</th><th>Band gap (eV) · range</th><th>Formation E</th><th>Source</th><th>Stability</th><th></th>
      </tr></thead><tbody>${rows.map((c) => {
        const named = state.names[c.id];
        const pinned = state.pins.has(c.id);
        const left = (c.lo / mx) * 100, width = ((c.hi - c.lo) / mx) * 100, pin = (c.val / mx) * 100;
        return `<tr class="cand-row${state.selCandidate === c.id ? " selected" : ""}" data-cand="${c.id}">
          <td class="score-cell"><span class="score-stripe" style="background:${scoreColor(c)}"></span>
            <span class="score-val">${candScore(c).toFixed(2)}</span></td>
          <td><div class="cand-formula">
            <span class="formula-icon">${c.el}</span>
            <span><span class="cand-name${named ? " named" : ""}" contenteditable="true" data-name="${c.id}">${named || fmt(c.formula)}</span><br>
            <span class="cand-id">${c.id}</span></span></div></td>
          <td class="prop-cell">
            <span class="prop-val">${c.val.toFixed(2)}</span> <span class="prop-err">± ${c.err.toFixed(2)}</span>
            <div class="range-bar"><div class="range-span" style="left:${left}%;width:${width}%;"></div>
              <div class="range-cap" style="left:${left}%;"></div><div class="range-cap" style="left:${left + width}%;"></div>
              <div class="range-pin" style="left:${pin}%;"></div></div>
            <div class="range-ends"><span>${c.lo.toFixed(1)}</span><span>${c.hi.toFixed(1)}</span></div>
          </td>
          <td class="mono">${c.ef.toFixed(2)}</td>
          <td><span class="src-badge">${c.source}</span></td>
          <td><span class="pill ${c.stability}">${cap(c.stability)}</span></td>
          <td><div class="cand-actions">
            <span class="cand-arrow" title="Inspect">${ICON.arrow}</span>
            <button data-view="${c.id}" title="View crystal">${ICON.eye}</button>
            <button data-pin="${c.id}" class="${pinned ? "active" : ""}" title="Pin">${ICON.pin}</button>
          </div></td></tr>`;
      }).join("")}</tbody></table>`;

    panel.querySelectorAll(".cand-row").forEach((r) =>
      r.addEventListener("click", (e) => {
        if (e.target.closest(".cand-actions") || e.target.dataset.name) return;
        selectCandidate(r.dataset.cand, true);
      }));
    panel.querySelectorAll("[data-view]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); selectCandidate(b.dataset.view, true); }));
    panel.querySelectorAll("[data-pin]").forEach((b) =>
      b.addEventListener("click", (e) => {
        e.stopPropagation();
        const id = b.dataset.pin;
        const was = state.pins.has(id);
        was ? state.pins.delete(id) : state.pins.add(id);
        persist(); b.classList.toggle("active", state.pins.has(id));
        if (!was) {
          const c = findCand(id);
          toast("ok", "Pinned " + (state.names[id] || c.formula), "Saved to your Pinned collection. Recall it with the Pinned button above the results.");
        }
        if (state.showPinnedOnly) renderTableTab();
        updateRhCount();
      }));
    panel.querySelectorAll("[data-name]").forEach((n) => {
      n.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); n.blur(); } });
      n.addEventListener("blur", () => {
        const id = n.dataset.name;
        const txt = n.textContent.trim();
        const orig = fmt(findCand(id).formula);
        if (txt && txt !== orig.replace(/<[^>]+>/g, "")) { state.names[id] = txt; n.classList.add("named"); }
        else { delete state.names[id]; n.classList.remove("named"); }
        persist();
      });
    });
  }

  function selectCandidate(id, goCrystal) {
    state.selCandidate = id;
    document.querySelectorAll(".cand-row").forEach((r) => r.classList.toggle("selected", r.dataset.cand === id));
    if (goCrystal) switchTab("crystal");
    syncAIContext();
  }

  /* ---------- PLOT tab (Apache ECharts: band gap bars + error bars) ---------- */
  function renderPlotTab() {
    const panel = document.querySelector('[data-panel="plot"]');
    panel.innerHTML = `<div class="plot-wrap"><div id="plotHost" style="width:100%;height:340px;"></div></div>`;
    renderBandgapChart($("#plotHost"), resultRows());
  }

  /* Shared band-gap chart (ECharts) — used by the Form and the Node editor.
     Bars = band gap, coloured by stability; whiskers = lo→hi uncertainty. */
  const STAB_COLOR = { stable: "#22C55E", marginal: "#F97316", unstable: "#EF4444" };
  function renderBandgapChart(host, rows) {
    if (!host) return;
    if (!window.echarts) { host.innerHTML = `<span class="vp-empty" style="color:var(--text-muted)">Chart library unavailable.</span>`; return; }
    const existing = window.echarts.getInstanceByDom(host);
    if (existing) existing.dispose();
    const chart = window.echarts.init(host, null, { renderer: "svg" });
    const font = "SF Pro Display, -apple-system, BlinkMacSystemFont, sans-serif";
    chart.setOption({
      textStyle: { fontFamily: font },
      grid: { left: 54, right: 18, top: 20, bottom: 64 },
      tooltip: {
        trigger: "axis",
        formatter: (ps) => {
          const i = ps[0].dataIndex, c = rows[i];
          return `<b>${c.formula}</b> · ${c.id}<br/>Band gap: <b>${c.val.toFixed(2)} eV</b> (±${c.err.toFixed(2)})<br/>Range: ${c.lo.toFixed(1)}–${c.hi.toFixed(1)} eV<br/>Stability: ${cap(c.stability)}`;
        },
      },
      xAxis: {
        type: "category", data: rows.map((c) => c.formula),
        axisLabel: { rotate: 40, color: "#6B7280", fontFamily: font },
        axisLine: { lineStyle: { color: "#D1D5DB" } }, axisTick: { show: false },
      },
      yAxis: {
        type: "value", name: "Band gap (eV)", nameLocation: "middle", nameGap: 38,
        nameTextStyle: { color: "#6B7280", fontFamily: font },
        axisLabel: { color: "#9CA3AF", fontFamily: font },
        splitLine: { lineStyle: { color: "#E5E7EB" } },
      },
      series: [
        {
          type: "bar", barWidth: "56%",
          data: rows.map((c) => ({ value: c.val, itemStyle: { color: STAB_COLOR[c.stability] || "#9CA3AF", borderRadius: [2, 2, 0, 0] } })),
          z: 1,
        },
        {
          type: "custom", z: 2,
          renderItem: (params, api) => {
            const xv = api.value(0);
            const hi = api.coord([xv, api.value(2)]);
            const lo = api.coord([xv, api.value(1)]);
            const hw = api.size([1, 0])[0] * 0.12;
            const style = { stroke: "#374151", lineWidth: 1.4, fill: null };
            return { type: "group", children: [
              { type: "line", shape: { x1: hi[0] - hw, y1: hi[1], x2: hi[0] + hw, y2: hi[1] }, style },
              { type: "line", shape: { x1: hi[0], y1: hi[1], x2: lo[0], y2: lo[1] }, style },
              { type: "line", shape: { x1: lo[0] - hw, y1: lo[1], x2: lo[0] + hw, y2: lo[1] }, style },
            ] };
          },
          encode: { x: 0, y: [1, 2] },
          data: rows.map((c, i) => [i, c.lo, c.hi]),
        },
      ],
    });
    window.addEventListener("resize", () => chart.resize());
    // the plot pane can be laid out at zero width when first rendered (hidden
    // tab); a ResizeObserver + rAF resize makes the chart fill once it's shown.
    requestAnimationFrame(() => chart.resize());
    if (window.ResizeObserver) {
      const obs = new ResizeObserver(() => { if (host.clientWidth) chart.resize(); });
      obs.observe(host);
    }
  }

  /* ---------- CRYSTAL tab (real CIF rendered with 3Dmol.js) ---------- */
  let crystalViewer = null;
  function renderCrystalTab() {
    const panel = document.querySelector('[data-panel="crystal"]');
    const c = state.selCandidate ? findCand(state.selCandidate) : null;
    if (!c) {
      panel.innerHTML = `<div class="viewport"><span class="vp-empty">Select a material from the Table tab to view its crystal structure.</span></div>`;
      return;
    }
    const els = structureElements(c);
    const pick = pickCIFFor(c);
    panel.innerHTML = `
      <div class="crystal-wrap">
        <div class="crystal-label"><span class="cl-formula mono">${fmt(c.formula)}</span><span class="cl-id mono">${c.id} · ${c.source}</span></div>
        <div class="viewport"><div id="crystalViewport" style="position:relative;width:100%;height:100%;"></div>
          <div class="vp-hint">Drag to rotate · Scroll to zoom${pick ? ` · CIF: ${pick.key}` : ""}</div></div>
        <div class="legend">${els.map((e) => `<span class="el"><span class="ed" style="background:${ELEMENT_COLORS[e] || "#888"}"></span>${e}</span>`).join("")}</div>
      </div>`;
    renderCIF(pick ? pick.cif : null);
  }

  function structureElements(c) {
    // crude element split from formula (caps-delimited)
    const matches = c.formula.match(/[A-Z][a-z]?/g) || [c.el];
    return [...new Set(matches)];
  }

  /* Prefer the candidate's OWN real CIF (keyed by formula); fall back to the
     nearest-elements sample only if a structure is missing. */
  function pickCIFFor(c) {
    if (typeof CANDIDATE_CIFS !== "undefined" && CANDIDATE_CIFS[c.formula]) {
      return { key: c.formula, cif: CANDIDATE_CIFS[c.formula] };
    }
    if (typeof SAMPLE_CIFS === "undefined") return null;
    const els = structureElements(c);
    const keys = Object.keys(SAMPLE_CIFS);
    if (!keys.length) return null;
    let best = keys[0], bestScore = -1;
    keys.forEach((k) => {
      const kEls = k.match(/[A-Z][a-z]?/g) || [];
      const score = kEls.filter((e) => els.includes(e)).length;
      if (score > bestScore) { bestScore = score; best = k; }
    });
    return { key: best, cif: SAMPLE_CIFS[best] };
  }

  /* Render a CIF string as a real 3D structure using 3Dmol.js, into a host
     element (defaults to the form's crystal viewport). Shared with node-app. */
  function renderCIF(cif, hostEl) {
    const host = hostEl || $("#crystalViewport");
    if (!host) return;
    if (!window.$3Dmol || !cif) {
      host.innerHTML = `<span class="vp-empty">3D structure viewer unavailable.</span>`;
      return;
    }
    try {
      const viewer = window.$3Dmol.createViewer(host, { backgroundColor: "#0D1117", antialias: true });
      viewer.addModel(cif, "cif");
      // colour each atom by element (Jmol/CPK scheme) so different elements are
      // visually distinct, with a ball-and-stick style.
      viewer.setStyle({}, { stick: { radius: 0.14, colorscheme: "Jmol" }, sphere: { scale: 0.32, colorscheme: "Jmol" } });
      try { viewer.addUnitCell({ box: { color: "#3a4150" } }); } catch (e) { /* some cells lack full symmetry */ }
      viewer.setViewStyle({ style: "outline", color: "black", width: 0.03 });
      viewer.zoomTo();
      viewer.render();
      viewer.zoom(1.15, 400);
      if (!hostEl) crystalViewer = viewer;
    } catch (e) {
      host.innerHTML = `<span class="vp-empty">Could not render this structure.</span>`;
    }
  }

  /* =========================================================
     FEATURE open / clear
     ========================================================= */
  function openFeature(id) {
    // Toggle: clicking the active feature again deselects it
    if (state.activeFeature === id) {
      state.activeFeature = null;
      state.hasResults = false; state.run = "idle"; state.selCandidate = null;
      renderUnits(); renderFeatures(); updatePipeline(); renderWorkspace(); syncAIContext();
      return;
    }
    state.activeFeature = id;
    state.activeUnit = null;  // feature takes over the main panel
    state.hasResults = false; state.run = "idle"; state.selCandidate = null; state.tab = "table";
    renderUnits(); renderFeatures(); updatePipeline(); renderWorkspace(); syncAIContext();
    $("#workspace").scrollTop = 0;
  }

  function openUnitWorkspace(type, id) {
    state.activeUnit = { type, id };
    state.activeFeature = null; // unit takes over, clear feature
    renderUnits(); renderFeatures(); updatePipeline(); renderWorkspace(); syncAIContext();
    $("#workspace").scrollTop = 0;
  }

  /* =========================================================
     UNIT WORKSPACE — IU opens in the main panel
     ========================================================= */
  function renderUnitWorkspace(type, id) {
    const cfg = unitPanelConfig(type, id);
    $("#crumbLeaf").textContent = cfg.title;
    const inner = $("#wsInner");

    // Build inputs HTML — core fields visible, rarely-used ones behind
    // an Advanced disclosure (same pattern as the feature parameters card)
    const fieldHTML = (f) => {
      const field = `<div class="field"><label class="field-label">${f.label}</label>`;
      if (f.type === "select") {
        return field + `<select class="select" id="uwf_${f.id}">${f.options.map((o) => `<option>${o}</option>`).join("")}</select></div>`;
      }
      return field + `<input class="input${f.type === "number" ? " mono" : ""}" id="uwf_${f.id}" type="${f.type === "number" ? "number" : "text"}" ${f.value != null ? `value="${f.value}"` : ""} placeholder="${f.placeholder || ""}"></div>`;
    };
    const coreInputs = cfg.inputs.filter((f) => !f.advanced);
    const advInputs = cfg.inputs.filter((f) => f.advanced);
    const inputsHTML = coreInputs.map(fieldHTML).join("") + (advInputs.length
      ? `<details class="advanced"><summary><span class="arr">›</span> Advanced parameters</summary>
           <div class="adv-body">${advInputs.map(fieldHTML).join("")}</div></details>`
      : "");

    inner.innerHTML = `
      <div class="unit-workspace fade-in">
        <button class="uw-back" id="uwBack" type="button">&larr; Back to workspace</button>
        <div class="uw-header">
          <div class="uw-kicker">${UNITS[type].label.replace(/s$/, "")} information unit</div>
          <h1 class="uw-title">${cfg.title}</h1>
          <p class="uw-sub">${cfg.subtitle}</p>
        </div>

        <div class="uw-cols">
          <div class="uw-section">
            <div class="uw-section-label">Inputs</div>
            ${inputsHTML}
          </div>

          <div class="uw-section">
            <div class="uw-section-label">Processing</div>
            <button class="btn btn-primary uw-run-btn" id="uwRunBtn">Start processing</button>
            <div class="uw-log-head">
              <span id="uwLogStatus">Idle</span>
              <button class="uw-log-clear" id="uwLogClear">Clear</button>
            </div>
            <div class="uw-log" id="uwLog"></div>

            <div class="uw-out-head">
              <div class="uw-section-label" style="margin:0">Outputs</div>
              <button class="btn btn-ghost btn-sm uw-download hidden" id="uwDownload">Download JSON</button>
            </div>
            <div class="uw-output-label" id="uwOutLabel">${cfg.outputLabel}</div>
            <div class="uw-output" id="uwOutput"><span class="uw-output-empty">No output yet. Run the unit to see results.</span></div>
          </div>
        </div>
      </div>`;

    // wire run button
    let uwTimer = null;
    const source = UNITS[type].label.replace(/s$/, "");
    $("#uwRunBtn").addEventListener("click", () => {
      const log = $("#uwLog");
      const out = $("#uwOutput");
      log.innerHTML = ""; out.innerHTML = `<span class="uw-output-empty">Processing…</span>`;
      $("#uwDownload").classList.add("hidden");
      if (uwTimer) { clearInterval(uwTimer); uwTimer = null; }
      const steps = [
        { t: `Initialising ${cfg.title}…`, c: "ll-info" },
        { t: "Validating inputs… ok", c: "ll-ok" },
        { t: type === "predictor" ? "Loading model weights…" : "Connecting to source…", c: "ll-info" },
        { t: type === "generator" ? "Sampling candidate structures…" : "Fetching records…", c: "ll-info" },
        { t: "Parsing structures… ok", c: "ll-ok" },
        { t: "Done.", c: "ll-ok" },
      ];
      let i = 0;
      $("#uwLogStatus").textContent = "Processing…";
      $("#uwRunBtn").disabled = true;
      uwTimer = setInterval(() => {
        const line = document.createElement("div");
        line.className = steps[i].c;
        line.textContent = "› " + steps[i].t;
        log.appendChild(line); log.scrollTop = log.scrollHeight;
        i++;
        if (i >= steps.length) {
          clearInterval(uwTimer); uwTimer = null;
          $("#uwLogStatus").textContent = "Completed";
          $("#uwRunBtn").disabled = false;
          const result = buildUnitOutput(type, cfg.title);
          $("#uwOutLabel").textContent = result.label;
          out.innerHTML = result.html;
          const dl = $("#uwDownload");
          dl.classList.remove("hidden");
          dl.onclick = () => downloadJSON(result.json, `${cfg.title.replace(/\s+/g, "_").toLowerCase()}_output.json`);
        }
      }, 420);
    });
    $("#uwLogClear").addEventListener("click", () => { $("#uwLog").innerHTML = ""; $("#uwLogStatus").textContent = "Idle"; });
    $("#uwBack").addEventListener("click", goHome);
  }

  /* Build a structured, human-readable output for an IU run (paper §S5 pattern):
     a summary of what was produced, a compact results table, and a JSON payload
     available for download. Uses the sample candidate corpus. */
  function buildUnitOutput(type, title) {
    const rows = CANDIDATES.slice(0, 6);
    const tiles = (pairs) => `<div class="uw-out-tiles">${pairs.map(([k, v]) =>
      `<div class="uw-tile"><div class="uw-tile-v mono">${v}</div><div class="uw-tile-k">${k}</div></div>`).join("")}</div>`;

    if (type === "predictor") {
      const label = "Predicted properties";
      const html = tiles([["Structures scored", rows.length], ["Model", title], ["Mean uncertainty", "± 0.06 eV"]]) +
        `<table class="rtable"><thead><tr><th>Structure</th><th>ID</th><th>Predicted (eV)</th><th>Stability</th></tr></thead><tbody>${
          rows.map((c) => `<tr><td class="mono" style="font-weight:600">${fmt(c.formula)}</td><td class="mono" style="color:var(--text-muted)">${c.id}</td><td class="mono">${c.val.toFixed(2)} ± ${c.err.toFixed(2)}</td><td><span class="pill ${c.stability}">${cap(c.stability)}</span></td></tr>`).join("")
        }</tbody></table>`;
      const json = { unit: title, type, structures_scored: rows.length, results: rows.map((c) => ({ id: c.id, formula: c.formula, predicted_value_eV: c.val, uncertainty_eV: c.err, stability: c.stability })) };
      return { label, html, json };
    }
    if (type === "generator") {
      const label = "Generated candidate structures";
      const html = tiles([["Structures generated", rows.length], ["Model", title], ["Unique formulas", new Set(rows.map((c) => c.formula)).size]]) +
        `<table class="rtable"><thead><tr><th>Formula</th><th>Proposed ID</th><th>Source</th></tr></thead><tbody>${
          rows.map((c, i) => `<tr><td class="mono" style="font-weight:600">${fmt(c.formula)}</td><td class="mono" style="color:var(--text-muted)">gen-${String(i + 1).padStart(4, "0")}</td><td><span class="src-badge">${title}</span></td></tr>`).join("")
        }</tbody></table>`;
      const json = { unit: title, type, structures_generated: rows.length, structures: rows.map((c, i) => ({ id: `gen-${String(i + 1).padStart(4, "0")}`, formula: c.formula })) };
      return { label, html, json };
    }
    // database (default)
    const label = "Retrieved dataset";
    const html = tiles([["Records extracted", rows.length], ["Databases queried", 1], ["Databases skipped", 0], ["Retrieval mode", "Lenient"]]) +
      `<table class="rtable"><thead><tr><th>Formula</th><th>ID</th><th>Source</th><th>Band gap</th><th>Stability</th></tr></thead><tbody>${
        rows.map((c) => `<tr><td class="mono" style="font-weight:600">${fmt(c.formula)}</td><td class="mono" style="color:var(--text-muted)">${c.id}</td><td><span class="src-badge">${c.source}</span></td><td class="mono">${c.val.toFixed(2)} eV</td><td><span class="pill ${c.stability}">${cap(c.stability)}</span></td></tr>`).join("")
      }</tbody></table>`;
    const json = { unit: title, type, records_extracted: rows.length, databases_queried: 1, databases_skipped: 0, retrieval_mode: "lenient", structures: rows.map((c) => ({ id: c.id, formula: c.formula, source: c.source, band_gap_eV: c.val, stability: c.stability })) };
    return { label, html, json };
  }

  /* Trigger a client-side JSON file download. */
  function downloadJSON(obj, filename) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; document.body.appendChild(a); a.click();
    a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function downloadText(text, filename, mime) {
    const blob = new Blob([text], { type: mime || "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; document.body.appendChild(a); a.click();
    a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  // CSV of a candidate list (shared by the form and node results panels).
  function candidatesCSV(rows) {
    const head = "formula,band_gap_eV,band_gap_lo,band_gap_hi,formation_energy_eV_atom,source,stability";
    return [head].concat(rows.map((c) =>
      [c.formula, c.bandgap, c.lo, c.hi, c.formationE, c.source, c.stability]
        .map((v) => (v == null ? "" : String(v).replace(/,/g, " "))).join(","))).join("\n");
  }
  // CIF for the selected candidate (or the top one): its own CIF if present,
  // else the closest bundled structure via pickCIFFor.
  function candidateCIF(c) {
    if (!c) return null;
    if (c.cif) return { name: c.formula, cif: c.cif };
    const pick = pickCIFFor(c);
    return pick ? { name: c.formula, cif: pick.cif } : null;
  }

  /* Return to the main workspace from any open unit or feature.
     Also exits the Node Editor: the Workspace crumb must always lead home. */
  function goHome() {
    if (state.view === "node") setView("form");
    state.activeUnit = null;
    state.activeFeature = null;
    state.hasResults = false; state.run = "idle"; state.selCandidate = null;
    renderUnits(); renderFeatures(); updatePipeline(); renderWorkspace(); syncAIContext();
    $("#workspace").scrollTop = 0;
  }

  /* ---------- styled confirm dialog (reuses .modal-scrim) ---------- */
  const confirmScrim = $("#confirmScrim");
  let confirmCb = null;
  function confirmDialog(title, body, okLabel, onConfirm) {
    $("#confirmTitle").textContent = title;
    $("#confirmBody").textContent = body;
    $("#confirmOk").textContent = okLabel || "Confirm";
    confirmCb = onConfirm;
    confirmScrim.hidden = false;
    $("#confirmCancel").focus();
  }
  function closeConfirm() { confirmScrim.hidden = true; confirmCb = null; }
  $("#confirmCancel").addEventListener("click", closeConfirm);
  $("#confirmOk").addEventListener("click", () => { const cb = confirmCb; closeConfirm(); if (cb) cb(); });
  confirmScrim.addEventListener("click", (e) => { if (e.target === confirmScrim) closeConfirm(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !confirmScrim.hidden) closeConfirm(); });

  function clearFormSelection() {
    state.selected = { database: new Set(), generator: new Set(), predictor: new Set() };
    state.activeFeature = null; state.activeUnit = null; state.hasResults = false;
    renderUnits(); renderFeatures(); updateTray(); updatePipeline(); renderWorkspace(); syncAIContext();
  }
  // Clear is context-aware: on the node canvas it wipes the pipeline, in the
  // form it clears the unit selection — always behind a confirmation.
  $("#clearSel").addEventListener("click", () => {
    if (state.view === "node") {
      const n = (window.EmosShared && window.EmosShared.nodeCount) ? window.EmosShared.nodeCount() : 0;
      const resultsOpen = !!document.querySelector("#results.open");
      // nothing on the canvas AND no results panel showing => truly nothing to clear
      if (!n && !resultsOpen) { toast("info", "Canvas already empty", "There are no nodes to clear."); return; }
      // if only the results panel is left, clear it without a confirm prompt
      if (!n && resultsOpen) { window.EmosShared.nodeClear(); return; }
      confirmDialog("Clear the canvas?", "This removes all nodes, connections and results from the pipeline. This cannot be undone.", "Clear canvas", () => {
        window.EmosShared.nodeClear();
        toast("ok", "Canvas cleared", "All nodes and connections were removed.");
      });
    } else {
      const total = state.selected.database.size + state.selected.generator.size + state.selected.predictor.size;
      if (!total && !state.activeFeature && !state.activeUnit) { toast("info", "Nothing to clear", "No units are selected."); return; }
      confirmDialog("Clear your selection?", "This deselects all units and closes the open feature.", "Clear selection", clearFormSelection);
    }
  });

  // Breadcrumb root ("EMOS") returns to the main workspace.
  $("#crumbRoot").addEventListener("click", goHome);

  /* =========================================================
     VIEW SWITCH — the Node Editor renders inside the main panel (same slot
     the Form workspace uses); the left sidebar stays put and becomes the
     drag source. The launcher button toggles between the two.
     ========================================================= */
  const nodeRoot = $("#nodeRoot");
  const mainEl = document.querySelector("main.main");
  const sidebarEl = document.querySelector("aside.sidebar");
  function setView(view) {
    const isNode = view === "node";
    state.view = view;
    nodeRoot.hidden = !isNode;
    mainEl.classList.toggle("node-mode", isNode);
    sidebarEl.classList.toggle("node-mode", isNode);
    $("#nodeTools").hidden = !isNode;
    $("#nodePalette").hidden = !isNode;
    $("#dragHint").hidden = !isNode;
    // launcher button label: "Node Editor" ⇄ "EMOS form" (return)
    $("#launchNodeTitle").textContent = isNode ? "EMOS form" : "Node Editor";
    $("#launchNodeDesc").textContent = isNode ? "Back to the guided form" : "Build a pipeline visually";
    $("#launchNode").setAttribute("aria-pressed", isNode ? "true" : "false");
    $("#clearSel").textContent = isNode ? "Clear canvas" : "Clear selection";
    // Re-render the sidebar for the new view: node mode undims every unit
    // (all are drag sources); form mode restores feature-context dimming.
    renderUnits();
    if (isNode) {
      dismissHint();
      window.EmosShared && window.EmosShared.refreshNodeContext && window.EmosShared.refreshNodeContext();
      window.EmosShared && window.EmosShared.nodeFitView && window.EmosShared.nodeFitView();
    } else {
      syncAIContext();
    }
    $("#crumbLeaf").textContent = isNode ? "Node Editor" : (state.activeUnit ? unitName(state.activeUnit.type, state.activeUnit.id) : (state.activeFeature ? featureById(state.activeFeature).name : "Form"));
  }
  $("#launchNode").addEventListener("click", () => setView(state.view === "node" ? "form" : "node"));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && state.view === "node") setView("form"); });

  /* =========================================================
     HELP POPOVER — clickable, viewport-clamped (never clipped)
     ========================================================= */
  (function initDocPopover() {
    const pop = $("#docPopover");
    let openBtn = null;
    function hide() { pop.hidden = true; if (openBtn) { openBtn.classList.remove("open"); openBtn = null; } }
    function show(btn) {
      const title = btn.dataset.docTitle || "";
      const desc = btn.querySelector(".doc-desc")?.textContent || "";
      pop.innerHTML = (title ? `<div class="dp-title">${title}</div>` : "") + desc;
      pop.hidden = false;
      const r = btn.getBoundingClientRect();
      const pw = pop.offsetWidth, ph = pop.offsetHeight, m = 8;
      let left = Math.max(m, Math.min(r.left + r.width / 2 - pw / 2, window.innerWidth - pw - m));
      let top = r.top - ph - 8;
      if (top < m) top = r.bottom + 8; // flip below when there is no room above
      pop.style.left = left + "px"; pop.style.top = top + "px";
      openBtn = btn; btn.classList.add("open");
    }
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".doc-icon");
      if (btn) { openBtn === btn ? hide() : show(btn); return; }
      if (!e.target.closest("#docPopover")) hide();
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") hide(); });
    window.addEventListener("scroll", hide, true);
    window.addEventListener("resize", hide);
  })();

  $("#unitFilter").addEventListener("input", (e) => { state.filter = e.target.value.toLowerCase(); renderUnits(); });

  /* =========================================================
     AI panel
     ========================================================= */
  const aiPanel = $("#aiPanel");
  function openAI(prefill) {
    aiPanel.classList.add("open");
    syncAIContext();
    if (!aiPanel.dataset.greeted) { greetAI(); aiPanel.dataset.greeted = "1"; }
    if (prefill) { $("#aiInput").value = prefill; $("#aiInput").focus(); }
  }
  function closeAI() { aiPanel.classList.remove("open"); aiPanel.classList.remove("maximised"); $("#aiScrim").classList.remove("show"); }
  $("#aiFab").addEventListener("click", () => { openAI(); dismissHint(); });
  $("#aiClose").addEventListener("click", closeAI);

  // Maximise / restore the AI panel into a centered square
  const aiScrim = $("#aiScrim");
  $("#aiMax").addEventListener("click", () => {
    const max = aiPanel.classList.toggle("maximised");
    aiScrim.classList.toggle("show", max);
    $("#aiMax").title = max ? "Restore" : "Maximise";
  });
  aiScrim.addEventListener("click", () => {
    aiPanel.classList.remove("maximised");
    aiScrim.classList.remove("show");
    $("#aiMax").title = "Maximise";
  });

  /* ----- Contextual hint bubble next to the FAB ----- */
  const aiHint = $("#aiHint");
  const aiHintText = $("#aiHintText");
  let hintDismissed = false;

  function hintForContext() {
    const f = state.activeFeature ? featureById(state.activeFeature) : null;
    const anySelected =
      state.selected.database.size + state.selected.generator.size + state.selected.predictor.size;
    if (state.hasResults) return "Want me to explain these results?";
    if (f && f.uses && state.selected[f.uses].size === 0)
      return `Need a ${f.uses} for ${f.name}? I can suggest one.`;
    if (f) return `Questions about configuring ${f.name}?`;
    if (anySelected) return "Ready to pick a feature? I can help you choose.";
    return "New here? I can help you build your first pipeline.";
  }

  function showHint() {
    if (hintDismissed || aiPanel.classList.contains("open")) return;
    aiHintText.textContent = hintForContext();
    aiHint.hidden = false;
  }
  function dismissHint() { aiHint.hidden = true; }
  function refreshHint() {
    // Update text if visible; otherwise leave dismissed state alone
    if (!aiHint.hidden && !hintDismissed) aiHintText.textContent = hintForContext();
  }
  $("#aiHintClose").addEventListener("click", () => { hintDismissed = true; dismissHint(); });

  // Surface the hint shortly after load, once, contextually
  setTimeout(showHint, 2400);

  /* =========================================================
     UNIT PANEL CONFIG — resolves inputs/outputs for an IU workspace
     ========================================================= */
  function unitPanelConfig(type, id) {
    if (UNIT_PANELS[id]) return UNIT_PANELS[id];
    const base = DEFAULT_UNIT_PANEL[type];
    return {
      title: unitName(type, id),
      subtitle: `${UNITS[type].label.replace(/s$/, "")} information unit`,
      kind: type,
      inputs: base.inputs,
      outputLabel: base.outputLabel,
    };
  }

  function syncAIContext() {
    // The context bar is shared; when the node canvas is the active view,
    // node-app.js owns what it says (node count etc), not the form's state.
    if (state.view === "node") {
      if (window.EmosShared && window.EmosShared.refreshNodeContext) window.EmosShared.refreshNodeContext();
      return;
    }
    const f = state.activeFeature ? featureById(state.activeFeature) : null;
    let ctx = "Welcome · no feature open";
    if (f) {
      const n = f.uses ? state.selected[f.uses].size : 0;
      ctx = f.uses ? `${f.name} · ${n} ${f.uses}${n === 1 ? "" : "s"} selected` : `${f.name} · device mode`;
    }
    if (state.selCandidate) ctx += ` · ${findCand(state.selCandidate).formula}`;
    $("#aiContext").innerHTML = `<span class="dotc"></span>${ctx}`;
    if (typeof refreshHint === "function") refreshHint();
  }

  function greetAI() {
    if (state.view === "node") {
      pushAI("bot", `Describe what you want to discover and I'll propose a pipeline. Try: "stable semiconductors with band gap near 1.4 eV", or ask me to "add a stability screen".`);
      return;
    }
    const f = state.activeFeature ? featureById(state.activeFeature) : null;
    let msg, suggest;
    if (!f) {
      msg = "Hi, I'm the EMOS Assistant. Select databases, generators or predictors to assemble a pipeline and I'll help you configure it.";
      suggest = "Try: \"Which databases have band gap data?\"";
    } else if (f.uses && state.selected[f.uses].size === 0) {
      msg = `You've opened ${f.name}, but no ${f.uses} is selected yet. Toggle at least one ${f.uses} on the left to enable this run.`;
      suggest = `Try: \"Recommend a ${f.uses} for wide band gap oxides\"`;
    } else {
      msg = `Ready to run ${f.name}. I can suggest parameter values or explain what each control does.`;
      suggest = "Try: \"What max-results value should I use?\"";
    }
    pushAI("bot", msg, suggest);
  }
  function pushAI(role, text, suggest) {
    const box = $("#aiMessages");
    if (role === "bot") box.appendChild(el("div", "ai-msg bot", `<div class="bubble">${text}</div>${suggest ? `<div class="ai-suggest">${suggest}</div>` : ""}`));
    else box.appendChild(el("div", "ai-msg user", text));
    box.scrollTop = box.scrollHeight;
    return box.lastElementChild;
  }
  // The assistant panel is shared by the Form and the Node Editor. When the
  // node canvas is the active view, a typed message proposes a pipeline
  // (node-app.js's own logic) instead of the form's canned keyword replies.
  function sendAI() {
    const inp = $("#aiInput"); const v = inp.value.trim(); if (!v) return;
    if (state.view === "node" && window.EmosShared && window.EmosShared.nodeAIHandle) {
      inp.value = ""; window.EmosShared.nodeAIHandle(v); return;
    }
    pushAI("user", v); inp.value = "";
    // Canned keyword reply — the fallback when no LLM key is configured.
    const cannedReply = () => {
      const f = state.activeFeature ? featureById(state.activeFeature) : null;
      if (/band ?gap/i.test(v)) return "MaterialsProject, JarvisDFT and Alexandria all carry DFT band gap values, with JarvisDFT best for 2D materials.";
      if (/recommend|which/i.test(v)) return "For wide band gap oxides, start with MaterialsProject plus AFLOW, then screen with MatterSim for stability.";
      if (/max|results|value|parameter/i.test(v)) return f ? `For ${f.name}, 50 to 100 results is a good first pass; tighten the energy above hull to 0.05 eV/atom for stable-only candidates.` : "Open a feature and I'll suggest concrete parameter values.";
      return "Open a feature on the left, set its parameters, and run it to see scored candidates.";
    };
    // Try the real LLM first (key-ready via EmosAPI.assistant); if it isn't
    // configured or fails, fall back to the canned reply so the demo still works.
    const f = state.activeFeature ? featureById(state.activeFeature) : null;
    const ctx = f ? `feature "${f.name}"` : "no feature open";
    const typing = pushAI("bot", "…");
    (async () => {
      let reply = null;
      try { if (window.EmosAPI && EmosAPI.assistant) reply = await EmosAPI.assistant(v, ctx); } catch (e) { reply = null; }
      typing.remove();
      pushAI("bot", reply || cannedReply());
    })();
  }
  $("#aiSend").addEventListener("click", sendAI);
  $("#aiInput").addEventListener("keydown", (e) => { if (e.key === "Enter") sendAI(); });

  /* =========================================================
     Onboarding
     ========================================================= */
  const ob = $("#onboard");
  let obIdx = 0;
  function showOnboard() {
    ob.hidden = false; obIdx = 0; renderOb();
  }
  function renderOb() {
    const s = ONBOARDING[obIdx];
    $("#obStep").textContent = String(obIdx + 1).padStart(2, "0") + " / 0" + ONBOARDING.length;
    $("#obTitle").textContent = s.title;
    $("#obDesc").textContent = s.desc;
    $("#obPreview").innerHTML = s.preview;
    $("#obFill").style.width = ((obIdx + 1) / ONBOARDING.length) * 100 + "%";
    $("#obPrev").disabled = obIdx === 0;
    $("#obNext").textContent = obIdx === ONBOARDING.length - 1 ? "Get started" : "Next";
    $("#obDots").innerHTML = ONBOARDING.map((_, i) => `<span class="d${i === obIdx ? " on" : ""}"></span>`).join("");
  }
  function closeOnboard() { ob.hidden = true; localStorage.setItem("emos_onboarded", "1"); }
  $("#obNext").addEventListener("click", () => { if (obIdx === ONBOARDING.length - 1) closeOnboard(); else { obIdx++; renderOb(); } });
  $("#obPrev").addEventListener("click", () => { if (obIdx > 0) { obIdx--; renderOb(); } });
  $("#obSkip").addEventListener("click", closeOnboard);

  /* =========================================================
     helpers
     ========================================================= */
  function fmt(formula) { return formula.replace(/(\d+)/g, "<sub>$1</sub>"); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function formatVal(v, unit) {
    const num = parseFloat(v);
    const s = Number.isInteger(num) ? num : num.toFixed(2);
    return unit ? `${s} ${unit}` : `${s}`;
  }
  const ICON = {
    eye: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>`,
    pin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M19 21l-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>`,
    comment: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>`,
    arrow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h13M13 6l6 6-6 6"/></svg>`,
    spark: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6z"/><path d="M19 14l.8 2.7L22.5 17l-2.7.8L19 20.5l-.8-2.7L15.5 17l2.7-.8z"/></svg>`,
    check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`,
    spinner: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 3a9 9 0 1 0 9 9" /></svg>`,
  };

  /* ---------- toast notifications ---------- */
  function toast(kind, title, msg) {
    const stack = $("#toastStack");
    const t = el("div", "toast" + (kind === "warn" ? " warn" : ""),
      `<span class="t-dot"></span><div class="t-body"><div class="t-title">${title}</div><div class="t-msg">${msg}</div></div><button class="t-close">&times;</button>`);
    stack.appendChild(t);
    const kill = () => { t.style.opacity = "0"; t.style.transition = "opacity .2s"; setTimeout(() => t.remove(), 220); };
    t.querySelector(".t-close").addEventListener("click", kill);
    setTimeout(kill, 5200);
  }

  /* =========================================================
     SHARED API — the Node Editor (node-app.js) is inlined into this same
     document and reuses the Form's single AI assistant, comment panel and
     toast system rather than keeping its own duplicates of each.
     ========================================================= */
  /* =========================================================
     INTERACTIVE PRODUCT TOUR — one skippable walkthrough that spotlights the
     real UI in order across the Form and the Node Editor, with a short
     auto-demo (a pipeline appears) so users see how it works, not just read it.
     ========================================================= */
  const tourEl = $("#tour");
  let tourSteps = [], tourIdx = 0;
  function tourOpenFeature() { if (!state.activeFeature) openFeature(FEATURES[0].id); }
  function tourShowResults() {
    if (!state.activeFeature) openFeature(FEATURES[0].id);
    state.run = "done"; state.hasResults = true; renderResults();
    // bring the real results into view so the spotlight lands on them, not empty space below the fold
    const rm = $("#resultsMount");
    if (rm) rm.scrollIntoView({ behavior: "auto", block: "center" });
  }
  // Animated drag: fly a ghost of a sidebar unit onto the canvas, drop a node,
  // then fill in the rest of the pipeline so the user sees how it's built.
  function tourAnimateDrag() {
    if (window.EmosShared && window.EmosShared.nodeClear) window.EmosShared.nodeClear();
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const src = document.querySelector('.unit-row[draggable="true"]');
    const canvas = document.querySelector("#canvasWrap");
    if (prefersReduced || !src || !canvas) { if (window.EmosShared.nodeLoadTemplate) window.EmosShared.nodeLoadTemplate(1); return; }
    const sr = src.getBoundingClientRect(), cr = canvas.getBoundingClientRect();
    const ghost = document.createElement("div");
    ghost.className = "tour-ghost";
    ghost.textContent = src.querySelector(".unit-name") ? src.querySelector(".unit-name").textContent : "Database";
    document.body.appendChild(ghost);
    ghost.style.left = sr.left + "px"; ghost.style.top = sr.top + "px";
    const tx = cr.left + cr.width * 0.32, ty = cr.top + cr.height * 0.42;
    requestAnimationFrame(() => { ghost.style.left = tx + "px"; ghost.style.top = ty + "px"; ghost.style.opacity = "0.9"; });
    setTimeout(() => {
      ghost.style.opacity = "0";
      setTimeout(() => ghost.remove(), 200);
      if (window.EmosShared.nodeLoadTemplate) window.EmosShared.nodeLoadTemplate(1); // drop the full example
    }, 950);
  }
  // Full walkthrough (Form + Node), reachable from the ? menu next to Pinned.
  function buildFullTourSteps() {
    return [
      { center: true, view: "form", title: "Welcome to EMOS", text: "A quick walkthrough of how to go from raw databases to a ranked, device-ready shortlist. You can skip anytime." },
      { view: "form", target: "#unitScroll", title: "Your building blocks", text: "Databases, generators and predictors live here. Select them for a Feature, or drag them onto the node canvas." },
      { view: "form", target: "#featureList", title: "Run a Feature", text: "Features bundle those units into a ready-made workflow, like the Database Extractor." },
      { view: "form", before: tourOpenFeature, target: ".controls-card", title: "Configure and run", text: "Set the parameters, then press Run to execute the workflow." },
      { view: "form", before: tourShowResults, target: "#resultsMount", title: "Read the results", text: "Results come back as a ranked table, an interactive plot, and a real 3D crystal structure, never raw JSON." },
      { view: "node", target: "#launchNode", title: "Or build it visually", text: "Prefer full control? The Node Editor lets you wire a custom pipeline from the same units." },
      { view: "node", before: tourAnimateDrag, target: "#canvasWrap", title: "Drag, drop, wire", text: "Drag any unit from the left onto the canvas and connect the ports, like this. Matching port colours snap together." },
      { view: "node", target: "#runBtn", title: "Run the pipeline", text: "Press Run Pipeline to execute the whole graph and get your ranked candidates." },
      { center: true, view: "form", title: "You're all set", text: "That's the whole loop. You can reopen this tour anytime from the ? button next to Pinned." },
    ];
  }
  // Node-only walkthrough, reachable from the Node Editor's own "Take the guided tour".
  function buildNodeTourSteps() {
    return [
      { center: true, view: "node", title: "Node Editor tour", text: "How to build a custom pipeline by dragging units onto the canvas and wiring them together. You can skip anytime." },
      { view: "node", target: "#unitScroll", title: "Your building blocks", text: "Drag any database, generator or predictor from the left onto the canvas to add it as a node." },
      { view: "node", before: tourAnimateDrag, target: "#canvasWrap", title: "Drag, drop, wire", text: "Drop a unit on the canvas and connect the ports, like this. Matching port colours snap together." },
      { view: "node", target: "#runBtn", title: "Run the pipeline", text: "Press Run Pipeline to execute the whole graph and get your ranked candidates." },
      { center: true, view: "node", title: "You're all set", text: "That's the Node Editor. Reopen this tour anytime from the help menu." },
    ];
  }
  let tourScope = "full";
  function startTour(scope) {
    tourScope = scope === "node" ? "node" : "full";
    tourSteps = tourScope === "node" ? buildNodeTourSteps() : buildFullTourSteps();
    tourIdx = 0; tourEl.hidden = false;
    if (tourScope === "node" && state.view !== "node") setView("node");
    showTourStep();
  }
  function endTour() {
    tourEl.hidden = true; tourEl.classList.remove("no-target"); localStorage.setItem("emos_tour_done", "1");
    // reset to a clean, empty starting state on both surfaces
    if (window.EmosShared && window.EmosShared.nodeClear) window.EmosShared.nodeClear();
    clearFormSelection();
    // return to the surface the tour was about
    setView(tourScope === "node" ? "node" : "form");
  }
  function showTourStep() {
    const s = tourSteps[tourIdx];
    if (s.view && state.view !== s.view) setView(s.view);
    if (s.before) s.before();
    $("#tourStep").textContent = `Step ${tourIdx + 1} of ${tourSteps.length}`;
    $("#tourTitle").textContent = s.title;
    $("#tourText").textContent = s.text;
    $("#tourBack").style.visibility = tourIdx === 0 ? "hidden" : "visible";
    $("#tourNext").textContent = tourIdx === tourSteps.length - 1 ? "Done" : "Next";
    // hide the callout + spotlight until they are positioned, so they don't
    // flash in the top-left corner during the pre-position delay
    const spot = $("#tourSpot"), pop = $("#tourPop");
    pop.style.opacity = "0"; if (spot) spot.style.opacity = "0";
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setTimeout(() => positionTour(s), prefersReduced ? 0 : 260);
  }
  function positionTour(s) {
    const spot = $("#tourSpot"), pop = $("#tourPop");
    pop.style.opacity = "1"; if (spot) spot.style.opacity = "1";
    const target = s.center ? null : document.querySelector(s.target);
    if (!target || !target.getBoundingClientRect().width) {
      tourEl.classList.add("no-target"); spot.hidden = true;
      pop.style.left = "50%"; pop.style.top = "50%"; pop.style.transform = "translate(-50%,-50%)";
      return;
    }
    tourEl.classList.remove("no-target"); pop.style.transform = "none";
    const r = target.getBoundingClientRect(), pad = 6;
    spot.hidden = false;
    spot.style.left = (r.left - pad) + "px"; spot.style.top = (r.top - pad) + "px";
    spot.style.width = (r.width + pad * 2) + "px"; spot.style.height = (r.height + pad * 2) + "px";
    const popW = 320, popH = pop.offsetHeight || 190, gap = 16;
    let left = r.right + gap, top = r.top;
    if (left + popW > window.innerWidth - 12) left = r.left - popW - gap;         // flip to left
    if (left < 12) { left = Math.min(Math.max(12, r.left), window.innerWidth - popW - 12); top = r.bottom + gap; }  // drop below
    top = Math.min(Math.max(12, top), window.innerHeight - popH - 12);
    pop.style.left = left + "px"; pop.style.top = top + "px";
  }
  $("#tourNext").addEventListener("click", () => { if (tourIdx === tourSteps.length - 1) { endTour(); return; } tourIdx++; showTourStep(); });
  $("#tourBack").addEventListener("click", () => { if (tourIdx > 0) { tourIdx--; showTourStep(); } });
  $("#tourSkip").addEventListener("click", endTour);
  window.addEventListener("resize", () => { if (!tourEl.hidden && tourSteps[tourIdx]) positionTour(tourSteps[tourIdx]); });

  /* =========================================================
     HELP menu (?) + Help overlay (accordion) + topbar Pinned
     ========================================================= */
  const helpMenu = $("#helpMenu"), helpOverlay = $("#helpOverlay");
  function toggleHelpMenu(force) {
    const show = force !== undefined ? force : helpMenu.hidden;
    helpMenu.hidden = !show;
    $("#topHelp").setAttribute("aria-expanded", show ? "true" : "false");
  }
  $("#topHelp").addEventListener("click", (e) => { e.stopPropagation(); toggleHelpMenu(); });
  document.addEventListener("click", (e) => { if (!helpMenu.hidden && !e.target.closest(".help-wrap")) toggleHelpMenu(false); });
  function openHelp() { toggleHelpMenu(false); helpOverlay.hidden = false; }
  function closeHelp() { helpOverlay.hidden = true; }
  $("#helpClose").addEventListener("click", closeHelp);
  helpOverlay.addEventListener("click", (e) => { if (e.target === helpOverlay) closeHelp(); });
  $("#helpAskAI").addEventListener("click", () => { closeHelp(); openAI(); });
  $("#helpStartTour").addEventListener("click", () => { closeHelp(); startTour(); });
  helpMenu.querySelectorAll("[data-help]").forEach((b) => b.addEventListener("click", () => {
    toggleHelpMenu(false);
    const k = b.dataset.help;
    if (k === "page") openHelp(); else if (k === "ai") openAI(); else if (k === "tour") startTour();
  }));
  // accordion (one-open); smooth via the CSS grid-rows trick
  $("#helpAcc").querySelectorAll(".acc-head").forEach((h) => h.addEventListener("click", () => {
    const item = h.closest(".acc-item"), wasOpen = item.classList.contains("open");
    $("#helpAcc").querySelectorAll(".acc-item").forEach((i) => i.classList.remove("open"));
    if (!wasOpen) item.classList.add("open");
  }));

  // Topbar Pinned: reflects the pin count; opens the pinned candidates.
  function updateTopPin() {
    const n = state.pins.size, pin = $("#topPin");
    $("#topPinN").textContent = n;
    pin.classList.toggle("has", n > 0);
  }
  $("#topPin").addEventListener("click", () => {
    if (!state.pins.size) { toast("info", "No pins yet", "Pin candidates from a results table to collect them here."); return; }
    if (state.view === "node") { toast("info", "Pinned candidates", `You have ${state.pins.size} pinned. Open a results table to review them.`); return; }
    if (!state.hasResults) { toast("info", "Run a feature first", "Your pinned candidates appear in the results table."); return; }
    state.showPinnedOnly = true;
    renderResults();
    const rm = $("#resultsMount"); if (rm) rm.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  window.EmosShared = {
    openAI, closeAI, syncAIContext, pushAI, toast,
    updateTopPin,
    get pins() { return state.pins; },
    get names() { return state.names; },
    persist,
    // shared 3D crystal rendering so the node editor shows the same real CIF
    pickCIF: pickCIFFor,
    renderCIFInto: (host, cif) => renderCIF(cif, host),
    // shared ECharts band-gap plot
    renderPlot: renderBandgapChart,
    // let the node editor re-open the tour
    startTour,
    // shared result exports (CSV text + per-candidate CIF)
    candidatesCSV, candidateCIF, downloadText,
  };

  /* =========================================================
     init
     ========================================================= */
  renderTypeChips(); renderUnits(); renderFeatures(); updateTray(); updatePipeline(); renderWorkspace(); syncAIContext(); updateTopPin();
  // First visit → launch the interactive tour (replaces the old static modal).
  if (!localStorage.getItem("emos_tour_done")) setTimeout(startTour, 600);
})();
