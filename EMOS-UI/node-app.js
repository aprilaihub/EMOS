/* ============================================================
   EMOS Node Editor — application logic
   Inlined into form.html as a full-viewport overlay (#nodeRoot); reuses
   UNITS / CANDIDATES / ELEMENT_COLORS from form-data.js and the Form's
   shared AI assistant / comment panel / toasts via window.EmosShared.
   ============================================================ */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  /* ---------- node-type catalog ----------
     Every library item becomes a node "kind". Ports carry data types:
       crystal  (blue)   — a set of crystal structures
       props    (purple) — structures + predicted properties
       scored   (red)    — ranked / scored candidates
     A node accepts an input only if the upstream output type matches
     one of its `accepts`.                                          */
  const DT = {
    crystal: { label: "Crystals", color: "var(--dt-crystal)" },
    props:   { label: "Properties", color: "var(--dt-props)" },
    scored:  { label: "Scored", color: "var(--dt-scored)" },
  };

  // map a generator unit-id to the property it targets (for param defaults)
  const GEN_TARGET = {
    mg_base: { target: "Unconstrained", prop: "n/a" },
    mg_mp20: { target: "MP-20 distribution", prop: "n/a" },
    mg_chem: { target: "Chemical system", prop: "Elements" },
    mg_chem_stab: { target: "Chemical system + stability", prop: "E above hull" },
    mg_bandgap: { target: "DFT band gap", prop: "Band gap (eV)" },
    mg_magdens: { target: "Magnetic density", prop: "μB / Å³" },
    mg_magdens_hhi: { target: "Magnetic density + supply risk", prop: "μB / Å³, HHI" },
    mg_bulk: { target: "Bulk modulus", prop: "K (GPa)" },
    mg_spacegroup: { target: "Space group", prop: "Space group #" },
  };

  // build the kind table from UNITS + a couple of IO/utility kinds
  const KINDS = {};
  function regUnitKinds() {
    UNITS.database.items.forEach((u) =>
      (KINDS["db:" + u.id] = {
        cat: "database", catLabel: "Database", color: "var(--cat-db)",
        name: u.name, inputs: [], output: "crystal",
        params: [
          { kind: "slider", id: "maxResults", label: "Max batch size", unit: "structures", min: 50, max: 1000, step: 50, value: 100 },
          { kind: "slider", id: "bandgapMin", label: "Band gap minimum", unit: "eV", min: 0, max: 6, step: 0.1, value: 0.8 },
          { kind: "text", id: "elements", label: "Required elements", placeholder: "e.g. Ga, N" },
        ],
      }));
    UNITS.generator.items.forEach((u) => {
      const t = GEN_TARGET[u.id] || { target: "n/a", prop: "n/a" };
      KINDS["gen:" + u.id] = {
        cat: "generator", catLabel: "Generator", color: "var(--cat-gen)",
        name: u.name, target: t.target, inputs: ["crystal"], accepts: ["crystal"], output: "crystal",
        optionalIn: true,
        params: [
          { kind: "slider", id: "nSamples", label: "Samples to generate", unit: "structures", min: 8, max: 256, step: 8, value: 64 },
          { kind: "slider", id: "guidance", label: "Guidance strength", unit: "", min: 0, max: 5, step: 0.1, value: 2.0 },
          { kind: "slider", id: "targetVal", label: "Target " + t.prop, unit: "", min: 0, max: 6, step: 0.1, value: 1.4, when: t.prop !== "n/a" },
        ].filter((p) => p.when !== false),
      };
    });
    UNITS.predictor.items.forEach((u) =>
      (KINDS["pred:" + u.id] = {
        cat: "predictor", catLabel: "Predictor", color: "var(--cat-pred)",
        name: u.name, inputs: ["crystal"], accepts: ["crystal", "props"], output: "props",
        params: [
          { kind: "slider", id: "batch", label: "Batch size", unit: "", min: 8, max: 128, step: 8, value: 32 },
          { kind: "select", id: "relax", label: "Relaxation", options: ["None", "Light", "Full"], value: "Light" },
        ],
      }));
    // screening / ranking + device kinds
    KINDS["feat:stability"] = {
      cat: "feature", catLabel: "Screen", color: "var(--cat-feat)",
      name: "Stability Consensus", inputs: ["props"], accepts: ["props"], output: "scored",
      params: [
        { kind: "slider", id: "agree", label: "Agreement threshold", unit: "%", min: 50, max: 100, step: 5, value: 75 },
        { kind: "slider", id: "ehullMax", label: "E above hull max", unit: "eV/atom", min: 0, max: 0.5, step: 0.01, value: 0.1 },
      ],
    };
    KINDS["feat:rank"] = {
      cat: "feature", catLabel: "Screen", color: "var(--cat-feat)",
      name: "Rank Candidates", inputs: ["props"], accepts: ["props", "scored"], output: "scored",
      params: [
        { kind: "select", id: "objective", label: "Objective", options: ["Maximise band gap", "Target band gap", "Maximise stability"], value: "Target band gap" },
        { kind: "slider", id: "targetGap", label: "Target band gap", unit: "eV", min: 0, max: 6, step: 0.1, value: 1.4 },
        { kind: "slider", id: "topK", label: "Keep top K", unit: "", min: 5, max: 50, step: 5, value: 10 },
      ],
    };
    KINDS["feat:mosfet"] = {
      cat: "feature", catLabel: "Evaluate", color: "var(--cat-feat)",
      name: "MOSFET Evaluator", inputs: ["scored"], accepts: ["scored", "props"], output: "scored",
      params: [
        { kind: "slider", id: "gateV", label: "Gate voltage", unit: "V", min: 0, max: 3, step: 0.1, value: 1.2 },
        { kind: "slider", id: "channelL", label: "Channel length", unit: "nm", min: 5, max: 100, step: 5, value: 20 },
      ],
    };
  }
  regUnitKinds();

  const CAT_ORDER = [
    { cat: "database", label: "Databases", prefix: "db:" },
    { cat: "generator", label: "Generators", prefix: "gen:" },
    { cat: "predictor", label: "Predictors", prefix: "pred:" },
    { cat: "feature", label: "Screen & Evaluate", prefix: "feat:" },
  ];

  const TEMPLATES = [
    { name: "Database → Screen", desc: "Pull from a database, predict stability, rank the survivors.",
      nodes: [["db:materialsproject", 80, 120], ["pred:mattersim", 360, 120], ["feat:rank", 640, 120]],
      edges: [[0, 1], [1, 2]] },
    { name: "Generate → Screen → Evaluate", desc: "Seed from a database, generate targeted candidates, screen, evaluate at device level.",
      nodes: [["db:cod", 60, 80], ["gen:mg_bandgap", 320, 80], ["pred:synthnn", 580, 80], ["feat:mosfet", 840, 80]],
      edges: [[0, 1], [1, 2], [2, 3]] },
    { name: "De-novo generation", desc: "Unconditioned MatterGen into a stability consensus screen.",
      nodes: [["gen:mg_base", 120, 140], ["pred:mattersim", 400, 140], ["feat:stability", 680, 140]],
      edges: [[0, 1], [1, 2]] },
  ];

  /* ---------- state ---------- */
  let state = {
    nodes: [],            // {uid, kind, x, y, params:{}, status, proposed}
    edges: [],            // {from, to}  uids
    seq: 1,
    sel: null,
    view: { x: 80, y: 40, k: 1 },
    running: false,
    dtPane: "params",
    resTab: "table",
    selCandidate: null,
    pendingProposal: null,
  };
  // Pins / notes / names / user identity / comment panel are owned by the
  // Form app (form-app.js) and shared here via window.EmosShared, so a
  // pinned or annotated candidate looks the same from either view.
  const Shared = window.EmosShared;

  const ICON = {
    eye: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>`,
    pin: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 4h6l-1 7 4 3v2H6v-2l4-3z"/><line x1="12" y1="16" x2="12" y2="21"/></svg>`,
    pinFill: `<svg viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1"><path d="M9 4h6l-1 7 4 3v2H6v-2l4-3z"/><line x1="12" y1="16" x2="12" y2="21" stroke-width="1.8"/></svg>`,
    chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7A8.38 8.38 0 0 1 4 11.5 8.5 8.5 0 0 1 12.5 3 8.38 8.38 0 0 1 21 11.5z"/></svg>`,
    check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>`,
  };

  /* ---------- node helpers ---------- */
  function addNode(kindId, x, y, opts = {}) {
    const k = KINDS[kindId];
    const params = {};
    (k.params || []).forEach((p) => (params[p.id] = p.value !== undefined ? p.value : (p.kind === "select" ? p.options[0] : "")));
    const n = { uid: "n" + state.seq++, kind: kindId, x, y, params, status: "notcfg", proposed: !!opts.proposed };
    state.nodes.push(n);
    return n;
  }
  const nodeById = (uid) => state.nodes.find((n) => n.uid === uid);
  const kindOf = (n) => KINDS[n.kind];
  function inputEdge(uid) { return state.edges.find((e) => e.to === uid); }
  function upstreamType(uid) {
    const e = inputEdge(uid);
    if (!e) return null;
    return kindOf(nodeById(e.from)).output;
  }
  function nodeReady(n) {
    const k = kindOf(n);
    if (k.inputs.length && !k.optionalIn && !inputEdge(n.uid)) return false;
    return true;
  }

  /* ---------- counts → topbar stages ---------- */
  function recomputeStatuses() {
    state.nodes.forEach((n) => {
      if (n.status === "running" || n.status === "done" || n.status === "error") return;
      n.status = nodeReady(n) ? "ready" : "notcfg";
    });
  }
  // The old topbar "SOURCE › GENERATE › SCREEN › EVALUATE" strip was removed;
  // this now only keeps the AI context text and the Run button enable state in
  // sync with the graph (the real status, not a redundant breadcrumb).
  function renderStages() {
    updateAICtx();
    const total = state.nodes.length;
    const runBtn = $("#runBtn");
    if (runBtn) runBtn.disabled = total === 0 || state.running;
  }

  /* ---------- pipeline-node palette (Screen & Evaluate kinds) ----------
     The database / generator / predictor drag sources are the Form's own
     sidebar rows (wired in form-app.js). Only the feature/screen/evaluate
     kinds, which have no sidebar row, get rendered as a small drag palette. */
  function renderNodePalette() {
    const host = $("#npItems");
    if (!host) return;
    const items = Object.entries(KINDS).filter(([id]) => id.startsWith("feat:"));
    host.innerHTML = items.map(([id, k]) =>
      `<div class="np-item" draggable="true" data-kind="${id}" title="${k.name}">
        <span class="npd" style="background:${k.color}"></span><span>${k.name}</span><span class="npg">⠿</span></div>`).join("");
    $$(".np-item", host).forEach((it) =>
      it.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/kind", it.dataset.kind)));
  }
  function renderTemplates() {
    const host = $("#tplList");
    if (!host) return;
    host.innerHTML = TEMPLATES.map((t, i) =>
      `<div class="tpl-card" data-tpl="${i}"><div class="tn">${t.name}</div><div class="td">${t.desc}</div></div>`).join("");
    $$(".tpl-card").forEach((c) => c.addEventListener("click", () => loadTemplate(+c.dataset.tpl)));
  }
  function loadTemplate(i, proposed = false) {
    const t = TEMPLATES[i];
    clearGraph();
    const uids = t.nodes.map(([kind, x, y]) => addNode(kind, x, y, { proposed }).uid);
    t.edges.forEach(([a, b]) => state.edges.push({ from: uids[a], to: uids[b] }));
    recomputeStatuses(); renderAll(); fitView();
    if (!proposed) toast("ok", "Template loaded", `${t.name}: ${t.nodes.length} nodes wired and ready to configure.`);
    return uids;
  }
  function clearGraph() { state.nodes = []; state.edges = []; state.sel = null; closeDetail(); }

  /* ---------- render canvas ---------- */
  function applyView() {
    $("#canvas").style.transform = `translate(${state.view.x}px,${state.view.y}px) scale(${state.view.k})`;
  }
  function renderNodes() {
    const layer = $("#nodeLayer");
    layer.innerHTML = state.nodes.map((n) => {
      const k = kindOf(n);
      const p0 = (k.params || [])[0];
      let pv = "Not configured";
      if (p0) { const v = n.params[p0.id]; pv = (v === "" || v == null) ? "Not configured" : `${p0.label}: ${v}${p0.unit ? " " + p0.unit : ""}`; }
      const hasIn = k.inputs.length > 0;
      const inType = upstreamType(n.uid);
      const inColor = inType ? DT[inType].color : "var(--grey-300)";
      return `<div class="node ${state.sel === n.uid ? "selected" : ""} ${n.proposed ? "proposed" : ""}" data-uid="${n.uid}" style="left:${n.x}px;top:${n.y}px;">
        <div class="hbar" style="background:${k.color}"></div>
        ${hasIn ? `<div class="port in" data-port="in" data-uid="${n.uid}" style="background:${inColor}"><span class="port-tip">in · ${k.accepts.map((t) => DT[t].label).join(" / ")}</span></div>` : ""}
        <div class="port out" data-port="out" data-uid="${n.uid}" style="background:${DT[k.output].color}"><span class="port-tip">out · ${DT[k.output].label}</span></div>
        <div class="nbody" data-drag="${n.uid}">
          <div class="ntype"><span style="color:${k.color};font-weight:700;">${k.catLabel}</span>${n.proposed ? '<span class="pb">AI</span>' : ""}</div>
          <div class="nname">${k.name}</div>
          <div class="nparam ${p0 && (n.params[p0.id] === "" || n.params[p0.id] == null) ? "unset" : ""}">${pv}</div>
          <div class="nstatus"><span class="sdot ${n.status}"></span><span>${statusLabel(n.status)}</span></div>
        </div>
      </div>`;
    }).join("");
    bindNodeEvents();
    updateEmptyState();
  }
  // Show the onboarding guide only when the canvas is empty AND the user has
  // not dismissed it before (persisted across reloads).
  function nodeOnboarded() { return localStorage.getItem("emos_node_onboarded") === "1"; }
  function updateEmptyState() {
    const el = $("#emptyState");
    if (!el) return;
    el.classList.toggle("hidden", state.nodes.length > 0 || nodeOnboarded());
  }
  (function () {
    const d = document.getElementById("emptyDismiss");
    if (d) d.addEventListener("click", () => { localStorage.setItem("emos_node_onboarded", "1"); updateEmptyState(); });
    const t = document.getElementById("emptyTour");
    if (t) t.addEventListener("click", () => { if (Shared.startTour) Shared.startTour("node"); });
  })();
  function statusLabel(s) {
    return { notcfg: "Needs input", ready: "Ready", running: "Running…", done: "Complete", error: "Error" }[s] || s;
  }

  function renderWires(temp) {
    const svg = $("#wires");
    const OFFS = 4000;
    let paths = "";
    state.edges.forEach((e, i) => {
      const a = portPos(e.from, "out"), b = portPos(e.to, "in");
      if (!a || !b) return;
      const t = kindOf(nodeById(e.from)).output;
      const d = bezier(a.x + OFFS, a.y + OFFS, b.x + OFFS, b.y + OFFS);
      paths += `<path d="${d}" stroke="${DT[t].color}" stroke-width="2"/>`;
      paths += `<path class="hit" d="${d}" data-edge="${i}"/>`;
    });
    if (temp) {
      const d = bezier(temp.ax + OFFS, temp.ay + OFFS, temp.bx + OFFS, temp.by + OFFS);
      paths += `<path d="${d}" stroke="var(--grey-400)" stroke-width="2" stroke-dasharray="5 4"/>`;
    }
    svg.innerHTML = paths;
    $$("path.hit", svg).forEach((p) => p.addEventListener("click", () => {
      state.edges.splice(+p.dataset.edge, 1);
      recomputeStatuses(); renderAll();
    }));
  }
  function bezier(ax, ay, bx, by) {
    const dx = Math.max(40, Math.abs(bx - ax) * 0.5);
    return `M ${ax} ${ay} C ${ax + dx} ${ay}, ${bx - dx} ${by}, ${bx} ${by}`;
  }
  // port position in canvas (untransformed) coords
  function portPos(uid, port) {
    const n = nodeById(uid); if (!n) return null;
    const W = 200, H = 88; // approx node height; port is vertically centered on body
    const cy = n.y + 44;
    return { x: port === "out" ? n.x + W : n.x, y: cy };
  }

  function renderMinimap() {
    const mm = $("#minimap");
    mm.style.display = state.nodes.length ? "" : "none";
    if (!state.nodes.length) { mm.innerHTML = ""; return; }
    const xs = state.nodes.map((n) => n.x), ys = state.nodes.map((n) => n.y);
    const minX = Math.min(...xs) - 40, maxX = Math.max(...xs) + 240;
    const minY = Math.min(...ys) - 40, maxY = Math.max(...ys) + 140;
    const sx = 148 / (maxX - minX), sy = 96 / (maxY - minY), s = Math.min(sx, sy);
    mm.innerHTML = state.nodes.map((n) => {
      const k = kindOf(n);
      return `<div class="mm-node" style="left:${(n.x - minX) * s}px;top:${(n.y - minY) * s}px;width:${200 * s}px;height:${70 * s}px;background:${k.color};opacity:.8;"></div>`;
    }).join("");
  }

  function renderAll() {
    recomputeStatuses();
    applyView(); renderNodes(); renderWires(); renderStages(); renderMinimap();
    if (state.sel) renderDetail();
  }

  /* ---------- node + port interactions ---------- */
  let drag = null, connect = null;
  function bindNodeEvents() {
    $$(".node").forEach((el) => {
      el.addEventListener("mousedown", (e) => {
        if (e.target.closest(".port")) return;
        const uid = el.dataset.uid;
        selectNode(uid);
        const n = nodeById(uid);
        drag = { uid, sx: e.clientX, sy: e.clientY, ox: n.x, oy: n.y, moved: false };
        e.preventDefault();
      });
    });
    $$(".port").forEach((p) => {
      p.addEventListener("mousedown", (e) => {
        e.stopPropagation();
        const uid = p.dataset.uid, port = p.dataset.port;
        if (port === "out") connect = { from: uid, kind: "out" };
        else {
          // dragging from an input detaches existing edge to re-route
          const ex = inputEdge(uid);
          if (ex) { state.edges = state.edges.filter((x) => x !== ex); connect = { from: ex.from, kind: "out" }; }
          else connect = { to: uid, kind: "in" };
        }
        e.preventDefault();
      });
    });
  }
  function selectNode(uid) { state.sel = uid; openDetail(); renderNodes(); renderWires(); }

  window.addEventListener("mousemove", (e) => {
    if (drag) {
      const dx = (e.clientX - drag.sx) / state.view.k, dy = (e.clientY - drag.sy) / state.view.k;
      if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
      const n = nodeById(drag.uid);
      n.x = drag.ox + dx; n.y = drag.oy + dy;
      renderNodes(); renderWires(); renderMinimap();
    } else if (connect) {
      const pt = clientToCanvas(e.clientX, e.clientY);
      let a, b;
      if (connect.kind === "out") { const p = portPos(connect.from, "out"); a = p; b = pt; }
      else { const p = portPos(connect.to, "in"); a = pt; b = p; }
      renderWires({ ax: a.x, ay: a.y, bx: b.x, by: b.y });
    } else if (pan) {
      state.view.x = pan.ox + (e.clientX - pan.sx);
      state.view.y = pan.oy + (e.clientY - pan.sy);
      applyView();
    }
  });
  window.addEventListener("mouseup", (e) => {
    if (connect) {
      const tgt = e.target.closest(".port");
      if (tgt) {
        const uid = tgt.dataset.uid, port = tgt.dataset.port;
        if (connect.kind === "out" && port === "in") tryConnect(connect.from, uid);
        else if (connect.kind === "in" && port === "out") tryConnect(uid, connect.to);
      }
      connect = null; renderWires();
    }
    if (drag) { drag = null; renderAll(); }
    if (pan) { pan = null; $("#canvasWrap").classList.remove("panning"); }
  });

  function tryConnect(fromUid, toUid) {
    if (fromUid === toUid) return;
    const from = nodeById(fromUid), to = nodeById(toUid);
    const ko = kindOf(from), ki = kindOf(to);
    if (!ki.inputs.length) { toast("warn", "No input", `${ki.name} does not take an input.`); return; }
    if (!ki.accepts.includes(ko.output)) {
      toast("warn", "Type mismatch", `${ki.name} accepts ${ki.accepts.map((t) => DT[t].label).join(" / ")}, but ${ko.name} outputs ${DT[ko.output].label}.`);
      return;
    }
    if (createsCycle(fromUid, toUid)) { toast("warn", "Loop blocked", "That connection would create a cycle in the pipeline."); return; }
    state.edges = state.edges.filter((x) => x.to !== toUid); // single input
    state.edges.push({ from: fromUid, to: toUid });
    recomputeStatuses(); renderAll();
  }
  function createsCycle(from, to) {
    // does `from` already depend (transitively) on `to`?
    let stack = [from], seen = new Set();
    while (stack.length) {
      const cur = stack.pop();
      if (cur === to) return true;
      if (seen.has(cur)) continue; seen.add(cur);
      state.edges.filter((e) => e.to === cur).forEach((e) => stack.push(e.from));
    }
    return false;
  }

  /* ---------- pan / zoom ---------- */
  let pan = null;
  $("#canvasWrap").addEventListener("mousedown", (e) => {
    if (e.target.closest(".node") || e.target.closest(".port") ||
        e.target.closest(".zoom-ctl") || e.target.closest(".minimap") || e.target.closest(".results") ||
        e.target.closest(".ai-panel") || e.target.closest(".comment-panel") || e.target.closest(".empty") ||
        e.target.closest("path.hit")) return;
    pan = { sx: e.clientX, sy: e.clientY, ox: state.view.x, oy: state.view.y };
    $("#canvasWrap").classList.add("panning");
    if (state.sel) { state.sel = null; closeDetail(); renderNodes(); }
  });
  $("#canvasWrap").addEventListener("wheel", (e) => {
    if (e.target.closest(".results") || e.target.closest(".library") || e.target.closest(".detail")) return;
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    zoomAt(e.clientX, e.clientY, factor);
  }, { passive: false });
  function zoomAt(cx, cy, factor) {
    const wrap = $("#canvasWrap").getBoundingClientRect();
    const px = cx - wrap.left, py = cy - wrap.top;
    const k0 = state.view.k, k1 = Math.max(0.35, Math.min(2, k0 * factor));
    state.view.x = px - (px - state.view.x) * (k1 / k0);
    state.view.y = py - (py - state.view.y) * (k1 / k0);
    state.view.k = k1; applyView(); renderMinimap();
  }
  function clientToCanvas(cx, cy) {
    const wrap = $("#canvasWrap").getBoundingClientRect();
    return { x: (cx - wrap.left - state.view.x) / state.view.k, y: (cy - wrap.top - state.view.y) / state.view.k };
  }
  function fitView() {
    if (!state.nodes.length) { state.view = { x: 80, y: 40, k: 1 }; applyView(); return; }
    const xs = state.nodes.map((n) => n.x), ys = state.nodes.map((n) => n.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs) + 200;
    const minY = Math.min(...ys), maxY = Math.max(...ys) + 110;
    const wrap = $("#canvasWrap").getBoundingClientRect();
    const k = Math.min(1.2, (wrap.width - 160) / (maxX - minX), (wrap.height - 120) / (maxY - minY));
    state.view.k = Math.max(0.4, k);
    state.view.x = (wrap.width - (maxX - minX) * state.view.k) / 2 - minX * state.view.k;
    state.view.y = (wrap.height - (maxY - minY) * state.view.k) / 2 - minY * state.view.k + 10;
    applyView(); renderMinimap();
  }

  $("#zoomIn").onclick = () => { const r = $("#canvasWrap").getBoundingClientRect(); zoomAt(r.left + r.width / 2, r.top + r.height / 2, 1.15); };
  $("#zoomOut").onclick = () => { const r = $("#canvasWrap").getBoundingClientRect(); zoomAt(r.left + r.width / 2, r.top + r.height / 2, 1 / 1.15); };
  $("#zoomFit").onclick = fitView;

  /* ---------- drop from library ---------- */
  const wrap = $("#canvasWrap");
  wrap.addEventListener("dragover", (e) => e.preventDefault());
  wrap.addEventListener("drop", (e) => {
    e.preventDefault();
    const kind = e.dataTransfer.getData("text/kind");
    if (!kind || !KINDS[kind]) return;
    const pt = clientToCanvas(e.clientX, e.clientY);
    const n = addNode(kind, pt.x - 100, pt.y - 44);
    recomputeStatuses(); renderAll(); selectNode(n.uid);
  });

  /* ---------- detail panel ---------- */
  function openDetail() { $("#detail").classList.remove("closed"); renderDetail(); }
  function closeDetail() { $("#detail").classList.add("closed"); }
  $("#dtClose").onclick = () => { state.sel = null; closeDetail(); renderNodes(); };

  function renderDetail() {
    const n = nodeById(state.sel); if (!n) return;
    const k = kindOf(n);
    $("#dtBar").style.background = k.color;
    $("#dtType").textContent = k.catLabel + (k.target ? " · " + k.target : "");
    $("#dtName").textContent = k.name;
    const badge = $("#dtBadge");
    badge.className = "dt-badge " + n.status;
    badge.textContent = { notcfg: "Needs input connection", ready: "Ready to run", running: "Running…", done: "Complete", error: "Error" }[n.status];
    $$("#detail .dt-tab").forEach((t) => t.classList.toggle("active", t.dataset.pane === state.dtPane));
    $$("#detail .dt-pane").forEach((p) => p.classList.toggle("active", p.dataset.pane === state.dtPane));
    renderParamsPane(n, k);
    renderOutputsPane(n, k);
    renderLogPane(n);
    renderDtFoot(n, k);
  }
  function renderParamsPane(n, k) {
    const pane = $("#paneParams");
    const inType = upstreamType(n.uid);
    let connNote = "";
    if (k.inputs.length) {
      connNote = inType
        ? `<div class="conn-note">Input: <b>${DT[inType].label}</b> from ${kindOf(nodeById(inputEdge(n.uid).from)).name}.</div>`
        : `<div class="conn-note">No input connected. Wire a ${k.accepts.map((t) => DT[t].label).join(" / ")} source into this node${k.optionalIn ? ", or run it unconditioned." : "."}</div>`;
    }
    pane.innerHTML = connNote + (k.params || []).map((p) => paramControl(n, p)).join("");
    bindParamControls(n, pane);
  }
  function paramControl(n, p) {
    const v = n.params[p.id];
    if (p.kind === "slider") {
      return `<div class="field slider-row">
        <div class="sr-top"><span class="nm">${p.label}${p.unit ? `<span class="u">${p.unit}</span>` : ""}</span><span class="val" data-val="${p.id}">${v}</span></div>
        <input class="slider" type="range" min="${p.min}" max="${p.max}" step="${p.step}" value="${v}" data-param="${p.id}">
        <div class="sr-minmax"><span>${p.min}</span><span>${p.max}</span></div></div>`;
    }
    if (p.kind === "select") {
      return `<div class="field"><label>${p.label}</label>
        <select class="input" data-param="${p.id}">${p.options.map((o) => `<option ${o === v ? "selected" : ""}>${o}</option>`).join("")}</select></div>`;
    }
    return `<div class="field"><label>${p.label}</label>
      <input class="input" type="text" data-param="${p.id}" value="${v}" placeholder="${p.placeholder || ""}"></div>`;
  }
  function bindParamControls(n, pane) {
    $$("[data-param]", pane).forEach((el) => {
      const ev = el.type === "range" || el.tagName === "SELECT" ? "input" : "input";
      el.addEventListener(ev, () => {
        n.params[el.dataset.param] = el.value;
        if (el.type === "range") { const lab = $(`[data-val="${el.dataset.param}"]`, pane); if (lab) lab.textContent = el.value; }
        const p0 = (kindOf(n).params || [])[0];
        if (p0 && el.dataset.param === p0.id) renderNodes();
      });
    });
  }
  function renderOutputsPane(n, k) {
    const pane = $("#paneOutputs");
    if (n.status !== "done") {
      pane.innerHTML = `<div class="dt-empty">Outputs appear here after the pipeline runs.<br>This node emits <b>${DT[k.output].label}</b>.</div>`;
      return;
    }
    const rows = currentResults().slice(0, 6);
    pane.innerHTML = `<table class="mini-table"><thead><tr><th>Formula</th><th>Band gap</th><th>Stability</th></tr></thead><tbody>
      ${rows.map((c) => `<tr><td class="fm mono">${fmt(c.formula)}</td><td class="mono">${c.val.toFixed(2)}</td><td><span class="pill ${c.stability}">${cap(c.stability)}</span></td></tr>`).join("")}
    </tbody></table><div style="margin-top:10px;"><button class="btn btn-ghost btn-sm" id="dtOpenResults">Open full results ↓</button></div>`;
    $("#dtOpenResults").onclick = openResults;
  }
  function renderLogPane(n) {
    const pane = $("#paneLog");
    pane.innerHTML = n._log ? `<div class="dt-log">${n._log}</div>` : `<div class="dt-empty">No run log yet. Run the pipeline to see step-by-step output for this node.</div>`;
  }
  function renderDtFoot(n, k) {
    $("#dtFoot").innerHTML = `<button class="btn btn-ghost btn-sm" id="dtDup">Duplicate</button><button class="btn btn-ghost btn-sm" id="dtDel" style="color:var(--accent);">Delete node</button>`;
    $("#dtDel").onclick = () => {
      state.nodes = state.nodes.filter((x) => x.uid !== n.uid);
      state.edges = state.edges.filter((e) => e.from !== n.uid && e.to !== n.uid);
      state.sel = null; closeDetail(); recomputeStatuses(); renderAll();
    };
    $("#dtDup").onclick = () => {
      const c = addNode(n.kind, n.x + 30, n.y + 30);
      c.params = { ...n.params }; recomputeStatuses(); renderAll(); selectNode(c.uid);
    };
  }
  $$("#detail .dt-tab").forEach((t) => t.addEventListener("click", () => { state.dtPane = t.dataset.pane; renderDetail(); }));

  /* ---------- run ---------- */
  function topoOrder() {
    const indeg = {}, adj = {};
    state.nodes.forEach((n) => { indeg[n.uid] = 0; adj[n.uid] = []; });
    state.edges.forEach((e) => { indeg[e.to]++; adj[e.from].push(e.to); });
    const q = state.nodes.filter((n) => indeg[n.uid] === 0).map((n) => n.uid);
    const order = [];
    while (q.length) { const u = q.shift(); order.push(u); adj[u].forEach((v) => { if (--indeg[v] === 0) q.push(v); }); }
    return order.length === state.nodes.length ? order : null;
  }
  function validate() {
    const issues = [];
    if (!state.nodes.length) { issues.push({ t: "Empty canvas", d: "Add at least one node to run." }); return issues; }
    const hasSource = state.nodes.some((n) => ["database", "generator"].includes(kindOf(n).cat));
    if (!hasSource) issues.push({ t: "No source", d: "Add a Database or Generator so the pipeline has structures to work on." });
    state.nodes.forEach((n) => {
      const k = kindOf(n);
      if (k.inputs.length && !k.optionalIn && !inputEdge(n.uid))
        issues.push({ t: k.name + " has no input", d: `Connect a ${k.accepts.map((t) => DT[t].label).join(" / ")} source into it.` });
    });
    if (!topoOrder()) issues.push({ t: "Cycle detected", d: "Remove the connection that loops back on itself." });
    return issues;
  }
  $("#runBtn").onclick = runPipeline;
  function runPipeline() {
    const issues = validate();
    if (issues.length) { showValidation(issues); return; }
    hideValidation();
    const order = topoOrder();
    state.running = true; renderStages();
    $("#runBtn").style.display = "none"; $("#cancelBtn").style.display = "";
    state.nodes.forEach((n) => { n.status = "ready"; n._log = ""; });
    let i = 0, cancelled = false;
    $("#cancelBtn").onclick = () => { cancelled = true; };
    const step = () => {
      if (cancelled) { state.running = false; state.nodes.forEach((n) => { if (n.status === "running") n.status = "ready"; }); finishRun(false); return; }
      if (i >= order.length) { finishRun(true); return; }
      const n = nodeById(order[i]);
      n.status = "running"; n._log = `› init ${kindOf(n).name}\n› processing…`;
      renderNodes(); if (state.sel === n.uid) renderDetail();
      setTimeout(() => {
        n.status = "done";
        n._log = `› init ${kindOf(n).name}\n› processed input\n<span class="ok">✓ ${outCount(n)} ${DT[kindOf(n).output].label.toLowerCase()} emitted</span>`;
        renderNodes(); if (state.sel === n.uid) renderDetail();
        i++; setTimeout(step, 180);
      }, 520);
    };
    step();
  }
  function outCount(n) {
    const k = kindOf(n);
    if (k.cat === "generator") return n.params.nSamples || 64;
    if (k.cat === "database") return n.params.maxResults || 60;
    if (n.kind === "feat:rank") return n.params.topK || 10;
    return currentResults().length;
  }
  async function finishRun(ok) {
    state.running = false;
    $("#runBtn").style.display = ""; $("#cancelBtn").style.display = "none";
    renderStages();
    if (ok) {
      try { await maybeFetchNodeResults(); }
      catch (e) { toast("warn", "Backend unavailable", "Showing the bundled sample data."); }
      toast("ok", "Pipeline complete", `${state.nodes.length} nodes executed. ${currentResults().length} ranked candidates ready.`);
      openResults();
    } else {
      toast("warn", "Run cancelled", "Pipeline stopped before completion.");
    }
  }
  function showValidation(issues) {
    let el = $("#valpanel");
    if (!el) { el = document.createElement("div"); el.className = "valpanel"; el.id = "valpanel"; $("#canvasWrap").appendChild(el); }
    el.innerHTML = `<div class="vh"><span class="sdot error" style="width:8px;height:8px;border-radius:50%;background:var(--status-unstable);"></span>Cannot run yet · ${issues.length} issue${issues.length > 1 ? "s" : ""}<span class="vx" id="valX">✕</span></div>
      <ul>${issues.map((x) => `<li><b>${x.t}.</b> ${x.d}</li>`).join("")}</ul>`;
    $("#valX").onclick = hideValidation;
  }
  function hideValidation() { const el = $("#valpanel"); if (el) el.remove(); }

  /* ---------- results (live via EmosAPI, else simulated CANDIDATES) ---------- */
  // Live backend rows when a run has fetched some; otherwise the bundled sample.
  const liveRows = () => (window.EmosAPI && window.EmosAPI.results && window.EmosAPI.results.length) ? window.EmosAPI.results : CANDIDATES;
  const nfind = (id) => liveRows().find((x) => x.id === id) || CANDIDATES.find((x) => x.id === id);
  function currentResults() {
    // if a Rank node exists, honor its topK
    const rank = state.nodes.find((n) => n.kind === "feat:rank");
    let rows = [...liveRows()];
    if (rank) rows = rows.slice(0, Math.min(rows.length, rank.params.topK || 10));
    return rows;
  }
  // Live: translate the graph's terminal node into a backend call and store
  // the rows on EmosAPI.results. Sim: no-op, so currentResults keeps CANDIDATES.
  async function maybeFetchNodeResults() {
    if (!window.EmosAPI || !window.EmosAPI.isLive()) return;
    // TODO(morning): map the wired pipeline to /api/process/iu/<type>/<id>
    // (or a feature id) for the terminal node, then EmosAPI.results is set.
  }
  function openResults() {
    const el = $("#results");
    el.classList.add("open"); renderResults();
    // the panel animates up into view on its own; scrollIntoView here would
    // push the panel header (title/tabs/close) above the fold, so don't call it.
  }
  function closeResults() { const el = $("#results"); if (el) el.classList.remove("open"); }
  $("#resClose").onclick = () => $("#results").classList.remove("open");
  $("#nodeExpCsv").onclick = () => {
    const rows = currentResults();
    Shared.downloadText(Shared.candidatesCSV(rows), "emos-pipeline-results.csv", "text/csv");
    toast("ok", "Exported", `emos-pipeline-results.csv with ${rows.length} structures downloaded.`);
  };
  $("#nodeExpCif").onclick = () => {
    const c = (state.selCandidate && nfind(state.selCandidate)) || currentResults()[0];
    const p = Shared.candidateCIF(c);
    if (!p) { toast("warn", "No structure", "Select a candidate with a crystal structure first."); return; }
    Shared.downloadText(p.cif, `${p.name.replace(/[^A-Za-z0-9]/g, "")}.cif`, "chemical/x-cif");
    toast("ok", "Downloaded", `${p.name} crystal structure saved as CIF.`);
  };
  $$("#resTabs .res-tab").forEach((t) => t.addEventListener("click", () => { state.resTab = t.dataset.tab; renderResults(); }));

  function pipelineSummary() {
    const order = topoOrder() || state.nodes.map((n) => n.uid);
    const names = order.map((uid) => kindOf(nodeById(uid)).name.replace(/^MatterGen:\s*/, ""));
    return names.length ? "Pipeline: " + names.join(" → ") : "";
  }
  function renderResults() {
    const rows = currentResults();
    $("#resCount").textContent = `Showing ${rows.length} structures`;
    const rp = $("#resPipeline"); if (rp) rp.textContent = pipelineSummary();
    $$("#resTabs .res-tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === state.resTab));
    $$(".res-pane").forEach((p) => p.classList.toggle("active", p.dataset.pane === state.resTab));
    if (state.resTab === "table") renderTable(rows);
    else if (state.resTab === "plot") renderPlot(rows);
    else renderCrystal();
  }
  function maxRange(rows) { return { lo: Math.min(...rows.map((c) => c.lo)), hi: Math.max(...rows.map((c) => c.hi)) }; }
  function renderTable(rows) {
    const mx = maxRange(rows), span = mx.hi - mx.lo || 1;
    $("#paneTable").innerHTML = `<table class="cand-table"><thead><tr>
      <th>Candidate</th><th>Band gap ± σ</th><th>Formation E</th><th>Source</th><th>Stability</th><th></th></tr></thead><tbody>
      ${rows.map((c) => {
        const left = ((c.lo - mx.lo) / span) * 100, width = ((c.hi - c.lo) / span) * 100, pin = ((c.val - mx.lo) / span) * 100;
        const nm = Shared.names[c.id] || fmt(c.formula);
        return `<tr data-id="${c.id}" class="${state.selCandidate === c.id ? "sel" : ""}">
          <td><div class="fcell"><div class="ficon">${c.formula.replace(/[0-9]/g, "").slice(0, 2)}</div>
            <div><div class="fname editable" data-name="${c.id}">${nm}</div><div class="fid">${c.id}</div></div></div></td>
          <td><span class="mono">${c.val.toFixed(2)}</span> <span class="mono" style="color:var(--grey-400);">± ${c.err.toFixed(2)}</span>
            <div class="range-bar"><div class="range-span" style="left:${left}%;width:${width}%;"></div>
              <div class="range-cap" style="left:${left}%;"></div><div class="range-cap" style="left:${left + width}%;"></div>
              <div class="range-pin" style="left:${pin}%;"></div></div>
            <div class="range-ends"><span>${c.lo.toFixed(1)}</span><span>${c.hi.toFixed(1)}</span></div></td>
          <td class="mono">${c.ef.toFixed(2)}</td>
          <td><span class="src-badge">${c.source}</span></td>
          <td><span class="pill ${c.stability}">${cap(c.stability)}</span></td>
          <td><div class="row-acts">
            <button class="ract" data-view="${c.id}" title="View structure">${ICON.eye}</button>
            <button class="ract ${Shared.pins.has(c.id) ? "on" : ""}" data-pin="${c.id}" title="Pin">${Shared.pins.has(c.id) ? ICON.pinFill : ICON.pin}</button></div></td></tr>`;
      }).join("")}</tbody></table>`;
    const pane = $("#paneTable");
    $$("tr[data-id]", pane).forEach((tr) => tr.addEventListener("click", (e) => {
      if (e.target.closest(".ract") || e.target.closest("[data-name]")) return;
      state.selCandidate = tr.dataset.id; state.resTab = "crystal"; renderResults();
    }));
    $$("[data-view]", pane).forEach((b) => b.addEventListener("click", (e) => { e.stopPropagation(); state.selCandidate = b.dataset.view; state.resTab = "crystal"; renderResults(); }));
    $$("[data-pin]", pane).forEach((b) => b.addEventListener("click", (e) => {
      e.stopPropagation(); const id = b.dataset.pin; const was = Shared.pins.has(id);
      was ? Shared.pins.delete(id) : Shared.pins.add(id); Shared.persist(); if (Shared.updateTopPin) Shared.updateTopPin(); renderResults();
      if (!was) { const c = nfind(id); toast("ok", "Pinned " + (Shared.names[id] || c.formula), "Saved to your pinned collection."); }
    }));
    $$("[data-name]", pane).forEach((el) => el.addEventListener("click", (e) => { e.stopPropagation(); editName(el); }));
  }
  function editName(el) {
    const id = el.dataset.name, cur = Shared.names[id] || el.textContent;
    const inp = document.createElement("input"); inp.className = "input"; inp.value = cur; inp.style.width = "120px"; inp.style.font = "inherit";
    el.replaceWith(inp); inp.focus(); inp.select();
    const commit = () => { const v = inp.value.trim(); if (v) Shared.names[id] = v; Shared.persist(); renderResults(); };
    inp.addEventListener("blur", commit);
    inp.addEventListener("keydown", (e) => { if (e.key === "Enter") inp.blur(); });
  }
  function renderPlot(rows) {
    // same ECharts band-gap chart the Form uses (shared via EmosShared)
    $("#panePlot").innerHTML = `<div class="plot-wrap"><div id="nodePlotHost" style="width:100%;height:320px;"></div></div>`;
    if (Shared.renderPlot) Shared.renderPlot($("#nodePlotHost"), rows);
  }

  /* crystal viewer — real CIF via the Form's shared 3Dmol renderer (same
     structures the form shows; no synthetic canvas). */
  function renderCrystal() {
    const pane = $("#paneCrystal");
    const c = state.selCandidate ? nfind(state.selCandidate) : null;
    if (!c) { pane.innerHTML = `<div class="crystal-wrap"><div class="viewport"><div class="vp-empty">Select a material from the Table tab to inspect its 3D structure.</div></div></div>`; return; }
    const els = structureElements(c);
    const pick = Shared.pickCIF ? Shared.pickCIF(c) : null;
    pane.innerHTML = `<div class="crystal-wrap">
      <div class="viewport"><div id="nodeCrystalHost" style="position:relative;width:100%;height:100%;"></div>
        <div class="vp-hint">Drag to rotate · Scroll to zoom${pick ? ` · CIF: ${pick.key}` : ""}</div></div>
      <div class="crystal-side"><div class="cl-formula mono">${fmt(c.formula)}</div><div class="cl-id mono">${c.id} · ${c.source}</div>
        <div class="crystal-legend">${els.map((e) => `<span class="el"><span class="ed" style="background:${ELEMENT_COLORS[e] || "#888"}"></span>${e}</span>`).join("")}</div></div></div>`;
    if (Shared.renderCIFInto && pick) Shared.renderCIFInto($("#nodeCrystalHost"), pick.cif);
  }
  function structureElements(c) { const m = c.formula.match(/[A-Z][a-z]?/g) || [c.el]; return [...new Set(m)]; }

  /* ---------- results panel resize ---------- */
  (function () {
    let rz = null;
    $("#resGrip").addEventListener("mousedown", (e) => { rz = { sy: e.clientY, h: $("#results").offsetHeight }; e.preventDefault(); });
    window.addEventListener("mousemove", (e) => { if (!rz) return; const nh = Math.max(160, Math.min(560, rz.h - (e.clientY - rz.sy))); $("#results").style.height = nh + "px"; });
    window.addEventListener("mouseup", () => (rz = null));
  })();

  const toast = (kind, title, sub) => Shared.toast(kind, title, sub);

  /* ---------- AI propose-then-confirm (shared panel, node-specific behavior) ---------- */
  function updateAICtx() {
    const el = document.querySelector("#aiContext");
    if (el) el.innerHTML = `<span class="dotc"></span>${state.nodes.length ? `Node editor · <b>${state.nodes.length} nodes</b>` : "Node editor · empty canvas"}`;
  }
  Shared.refreshNodeContext = updateAICtx;
  function aiThink(cb) { const d = Shared.pushAI("bot", `<span class="typing"><i></i><i></i><i></i></span>`); setTimeout(() => { d.remove(); cb(); }, 850); }

  function aiHandle(text) {
    Shared.pushAI("user", text);
    const low = text.toLowerCase();
    aiThink(() => {
      // pick a template by intent
      let tplIdx = 1; // generate→screen→evaluate default
      if (/de.?novo|unconditioned|from scratch|generate new/.test(low)) tplIdx = 2;
      else if (/database|existing|known|pull|extract/.test(low) && !/generat/.test(low)) tplIdx = 0;
      const t = TEMPLATES[tplIdx];
      state.pendingProposal = { tplIdx };
      const d = Shared.pushAI("bot", `Here's a pipeline for that goal:
        <div class="pe"><b>${t.name}</b>: ${t.desc}</div>
        <div class="pp">${t.nodes.map((n) => KINDS[n[0]].name).join("  →  ")}</div>
        <div class="propose-actions"><button class="btn btn-primary btn-sm" id="propApply">Apply to canvas</button><button class="btn btn-ghost btn-sm" id="propDismiss">Not now</button></div>`);
      d.querySelector("#propApply").onclick = () => {
        const uids = loadTemplate(tplIdx, true);
        // settle proposed → real after a beat (confirm step)
        state.nodes.forEach((n) => (n.proposed = false));
        renderAll();
        d.querySelector(".propose-actions").innerHTML = `<span style="font-size:12px;color:var(--status-stable);font-weight:600;">✓ Applied · ${uids.length} nodes added</span>`;
        toast("ok", "Pipeline proposed", "Review each node's parameters, then Run when ready.");
      };
      d.querySelector("#propDismiss").onclick = () => { d.querySelector(".propose-actions").innerHTML = `<span style="font-size:12px;color:var(--grey-400);">Dismissed</span>`; };
    });
  }
  window.EmosShared.nodeAIHandle = aiHandle;
  $("#emptySend").onclick = () => { const v = $("#emptyInput").value.trim(); if (v) { Shared.openAI(); aiHandle(v); $("#emptyInput").value = ""; } };
  $("#emptyInput").onkeydown = (e) => { if (e.key === "Enter") $("#emptySend").click(); };

  /* ---------- save / export ---------- */
  $("#saveBtn").onclick = () => { localStorage.setItem("emos_pipeline", JSON.stringify({ nodes: state.nodes, edges: state.edges })); toast("ok", "Pipeline saved", "Stored locally in this browser."); };
  $("#loadBtn").onclick = () => {
    const raw = localStorage.getItem("emos_pipeline");
    if (!raw) { toast("warn", "Nothing saved", "Save a pipeline first, then it can be reloaded here."); return; }
    try {
      const data = JSON.parse(raw);
      if (!Array.isArray(data.nodes)) throw new Error("bad format");
      state.nodes = data.nodes;
      state.edges = Array.isArray(data.edges) ? data.edges : [];
      // keep the id sequence ahead of any restored node id
      const maxSeq = state.nodes.reduce((m, n) => Math.max(m, parseInt(String(n.uid).replace(/\D/g, ""), 10) || 0), 0);
      state.seq = maxSeq + 1;
      state.sel = null; closeDetail();
      recomputeStatuses(); renderAll(); updateAICtx();
      toast("ok", "Pipeline loaded", `${state.nodes.length} node${state.nodes.length === 1 ? "" : "s"} restored.`);
    } catch (e) { toast("warn", "Could not load", "The saved pipeline could not be read."); }
  };
  $("#exportBtn").onclick = () => {
    const spec = { nodes: state.nodes.map((n) => ({ id: n.uid, kind: n.kind, name: kindOf(n).name, params: n.params })), edges: state.edges };
    const blob = new Blob([JSON.stringify(spec, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "emos-pipeline.json"; a.click();
    toast("ok", "Exported", "emos-pipeline.json downloaded.");
  };
  // (help is now the shared "?" menu in the topbar, wired in form-app.js)

  /* ---------- helpers ---------- */
  function fmt(f) { return f.replace(/([0-9]+)/g, "<sub>$1</sub>"); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  /* ---------- boot ---------- */
  renderNodePalette(); renderTemplates(); renderAll(); applyView();
  // hooks the Form app calls when entering node mode / clearing the canvas
  window.EmosShared.nodeFitView = fitView;
  window.EmosShared.nodeCount = () => state.nodes.length;
  window.EmosShared.nodeClear = () => { clearGraph(); closeResults(); renderAll(); };
  window.EmosShared.nodeLoadTemplate = (i) => loadTemplate(i);
})();
