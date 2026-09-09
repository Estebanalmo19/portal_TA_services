/**
 * Uniform Compliance Check: inspections table + create-inspection modal
 * (with live score preview) + detail modal, corrective-followups tab
 * (with a "marcar resuelto" action), and an analytics tab (compliance by
 * site/shift + top checklist violations). All rendering reads
 * `ArrisePortal.state.solutions.uniform` so it reflects whatever this tab
 * has done so far (see state/bootstrap.js for how that state is seeded/
 * persisted).
 *
 * Score formula (must match `solutions.services.uniform.compute_score`
 * exactly — see that function's docstring): conformes / aplicables × 100,
 * excluding items in status 'no_aplica'. If there are zero applicable
 * items the score is `null` and the UI must show "Sin evaluación" — never
 * "Infinity"/"NaN". The Python copy is authoritative; `computeScorePreview`
 * below only drives the client-side live preview while filling the form.
 *
 * The demo approval rule (100% of applicable items conforme -> "conforme";
 * any other evaluable result -> "seguimiento") is a documented demo-only
 * guide, never presented as an official ARRISE policy — see the notice in
 * templates/solutions/uniform/home.html and the same wording repeated in
 * the detail modal below.
 */
(function (global) {
  "use strict";

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (e) { return []; }
  }

  const SITES = readJSON("uniform-sites");
  const SHIFTS = readJSON("uniform-shifts");
  const CHECKLIST_ITEMS = readJSON("uniform-checklist-items");
  const ITEM_STATUSES = readJSON("uniform-item-statuses");
  const ROLES = readJSON("uniform-roles");
  const INSPECTORS = readJSON("uniform-inspectors");
  const EMPLOYEES = readJSON("uniform-employees");

  function toLabelMap(list) {
    return list.reduce(function (acc, item) { acc[item.slug] = item.label; return acc; }, {});
  }

  const SHIFT_LABELS = toLabelMap(SHIFTS);
  const CHECKLIST_ITEM_LABELS = toLabelMap(CHECKLIST_ITEMS);
  const ITEM_STATUS_LABELS = toLabelMap(ITEM_STATUSES);
  const INSPECTION_STATUS_LABELS = {
    conforme: "Conforme",
    seguimiento: "Requiere seguimiento",
    sin_evaluacion: "Sin evaluación",
  };
  const FOLLOWUP_STATUS_LABELS = { pendiente: "Pendiente", resuelto: "Resuelto" };

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    // Merge field-by-field (not `||` on the whole object): a tab whose
    // sessionStorage was seeded before this module existed (the stub used
    // to store `{records: [], not_implemented: true}`) would otherwise keep
    // that stale shape and crash every renderer that reads `.inspections`.
    const existing = state.solutions.uniform || {};
    state.solutions.uniform = {
      inspections: existing.inspections || [],
      followups: existing.followups || [],
      last_sync: existing.last_sync || null,
    };
    return state.solutions.uniform;
  }

  // ---------------- Score preview (client-side mirror) ----------------

  function computeScorePreview(items) {
    // Mirrors solutions.services.uniform.compute_score: conformes /
    // aplicables × 100, excluding 'no_aplica'; null when 0 aplicables.
    const applicable = items.filter(function (it) { return it.status !== "no_aplica"; });
    if (!applicable.length) return null;
    const conformes = applicable.filter(function (it) { return it.status === "conforme"; }).length;
    return Math.round((conformes / applicable.length) * 1000) / 10;
  }

  function statusForScore(score) {
    if (score === null) return "sin_evaluacion";
    if (score === 100) return "seguimiento" === "seguimiento" && score === 100 ? "conforme" : "seguimiento";
    return "seguimiento";
  }

  function siteName(slug) {
    const s = SITES.find(function (x) { return x.slug === slug; });
    return s ? s.name : slug;
  }

  function statusBadgeClass(status) {
    if (status === "conforme") return "badge-success";
    if (status === "seguimiento") return "badge-warning";
    return "badge-neutral";
  }

  function followupBadgeClass(status) {
    return status === "resuelto" ? "badge-success" : "badge-warning";
  }

  function itemBadgeClass(status) {
    if (status === "conforme") return "badge-success";
    if (status === "no_aplica") return "badge-neutral";
    return "badge-danger";
  }

  function scoreLabel(score) {
    return score === null || score === undefined ? "Sin evaluación" : score + "%";
  }

  // ---------------- KPIs ----------------

  function renderKpis() {
    const inspections = data().inspections;
    const followups = data().followups;
    const evaluable = inspections.filter(function (i) { return i.score !== null && i.score !== undefined; });
    const conformes = evaluable.filter(function (i) { return i.score === 100; }).length;
    const pending = followups.filter(function (f) { return f.status === "pendiente"; }).length;
    const noEval = inspections.length - evaluable.length;

    setKpi("total", inspections.length);
    setKpi("conformance", evaluable.length ? Math.round((conformes / evaluable.length) * 100) + "%" : "Sin datos");
    setKpi("pending", pending);
    setKpi("no-eval", noEval);

    const lastSyncEl = document.querySelector("[data-uniform-last-sync]");
    if (lastSyncEl) lastSyncEl.textContent = global.ArriseDom.formatDateTime(data().last_sync);
  }

  function setKpi(key, value) {
    const el = document.querySelector('[data-uniform-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  // ---------------- Inspections table ----------------

  function matchesFilters(record) {
    const q = (document.querySelector('[data-uniform-filter="q"]').value || "").trim().toLowerCase();
    const site = document.querySelector('[data-uniform-filter="site"]').value;
    const shift = document.querySelector('[data-uniform-filter="shift"]').value;
    const status = document.querySelector('[data-uniform-filter="status"]').value;
    if (site && record.site !== site) return false;
    if (shift && record.shift !== shift) return false;
    if (status && record.status !== status) return false;
    if (q && record.employee_name.toLowerCase().indexOf(q) === -1 && record.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  function filteredInspections() {
    return data().inspections.filter(matchesFilters).slice().sort(function (a, b) {
      return new Date(b.created_at) - new Date(a.created_at);
    });
  }

  function renderTable() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const tbody = document.querySelector("[data-uniform-table-body]");
    const empty = document.querySelector("[data-uniform-empty]");
    if (!tbody) return;
    clear(tbody);
    const records = filteredInspections();
    empty.hidden = records.length !== 0;

    records.forEach(function (record) {
      tbody.append(h(
        "tr",
        {
          class: "row-link", tabindex: "0", role: "button", "aria-label": "Ver detalle de " + record.id,
          onClick: function () { openDetail(record.id); },
          onKeydown: function (evt) { if (evt.key === "Enter") openDetail(record.id); },
        },
        [
          h("td", { class: "mono" }, [record.id]),
          h("td", {}, [record.employee_name]),
          h("td", {}, [record.role_label]),
          h("td", {}, [siteName(record.site)]),
          h("td", {}, [SHIFT_LABELS[record.shift] || record.shift]),
          h("td", {}, [scoreLabel(record.score)]),
          h("td", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [INSPECTION_STATUS_LABELS[record.status] || record.status])]),
          h("td", {}, [record.inspector]),
          h("td", {}, [formatDateTime(record.created_at)]),
        ]
      ));
    });
  }

  // ---------------- Create-inspection modal ----------------

  function openCreateForm() {
    if (!EMPLOYEES.length) {
      global.ArriseToast.danger("No hay colaboradores elegibles configurados para esta solución.");
      return;
    }
    const { h } = global.ArriseDom;
    let selectedEmployee = EMPLOYEES[0];

    const employeeSelect = h("select", { id: "uni-employee", class: "select", required: "required" },
      EMPLOYEES.map(function (e) { return h("option", { value: e.id }, [e.name + " — " + e.role_label]); }));

    const siteSelect = h("select", { id: "uni-site", class: "select", required: "required" },
      SITES.map(function (s) { return h("option", { value: s.slug }, [s.name]); }));

    const shiftSelect = h("select", { id: "uni-shift", class: "select", required: "required" },
      SHIFTS.map(function (s) { return h("option", { value: s.slug }, [s.label]); }));

    const inspectorSelect = h("select", { id: "uni-inspector", class: "select", required: "required" },
      INSPECTORS.map(function (name) { return h("option", { value: name }, [name]); }));

    const itemSelects = {};
    const roleLabelEl = h("span", {}, [selectedEmployee.role_item_label]);
    const itemRows = CHECKLIST_ITEMS.map(function (item) {
      const select = h("select", { class: "select" },
        ITEM_STATUSES.map(function (s) { return h("option", { value: s.slug, selected: s.slug === "conforme" ? "selected" : null }, [s.label]); }));
      itemSelects[item.slug] = select;
      const labelNode = item.slug === "elementos_rol" ? roleLabelEl : item.label;
      return h("div", { class: "field" }, [
        h("label", { class: "field-label" }, [labelNode]),
        select,
      ]);
    });

    function currentItems() {
      return CHECKLIST_ITEMS.map(function (item) {
        return { slug: item.slug, status: itemSelects[item.slug].value };
      });
    }

    const scoreText = h("p", { style: "margin: var(--space-2) 0 4px; font-weight: 600;" }, ["Score estimado: —"]);
    const progressFill = h("div", { class: "progress-bar-fill", style: "width:0%;" }, []);
    const progressBar = h("div", { class: "progress-bar" }, [progressFill]);

    function updatePreview() {
      const score = computeScorePreview(currentItems());
      if (score === null) {
        scoreText.textContent = "Score estimado: Sin evaluación (ningún elemento aplicable)";
        progressFill.style.width = "0%";
      } else {
        const verdict = score === 100 ? "conforme" : "requiere seguimiento — guía de demostración";
        scoreText.textContent = "Score estimado: " + score + "% (" + verdict + ")";
        progressFill.style.width = score + "%";
      }
    }

    Object.keys(itemSelects).forEach(function (slug) {
      itemSelects[slug].addEventListener("change", updatePreview);
    });

    employeeSelect.addEventListener("change", function () {
      selectedEmployee = EMPLOYEES.find(function (e) { return e.id === employeeSelect.value; }) || EMPLOYEES[0];
      roleLabelEl.textContent = selectedEmployee.role_item_label;
    });

    const observationsInput = h("textarea", { id: "uni-observations", class: "textarea", maxlength: "800" });
    const evidenceInput = h("input", { id: "uni-evidence", class: "input", placeholder: "foto_uniforme_demo.jpg", required: "required", maxlength: "120" });

    const form = h("form", { id: "uniform-create-form" }, [
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "uni-employee" }, ["Colaborador", h("span", { class: "required-mark" }, ["*"])]),
        employeeSelect,
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "uni-site" }, ["Sede", h("span", { class: "required-mark" }, ["*"])]),
          siteSelect,
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "uni-shift" }, ["Turno", h("span", { class: "required-mark" }, ["*"])]),
          shiftSelect,
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "uni-inspector" }, ["Inspector", h("span", { class: "required-mark" }, ["*"])]),
        inspectorSelect,
      ]),
      h("hr"),
      h("h3", { style: "margin-top:0;" }, ["Checklist de uniforme"]),
      h("div", { class: "stack" }, itemRows),
      scoreText,
      progressBar,
      h("hr"),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "uni-observations" }, ["Observaciones"]),
        observationsInput,
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "uni-evidence" }, ["Evidencia (nombre de archivo simulado)", h("span", { class: "required-mark" }, ["*"])]),
        evidenceInput,
      ]),
      h("div", { "data-form-errors": "1" }, []),
    ]);

    updatePreview();

    const submitBtn = h("button", { type: "submit", form: "uniform-create-form", class: "btn btn-primary" }, ["Confirmar inspección"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({
      title: "Nueva inspección de uniforme",
      body: form,
      footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]),
    });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const items = {};
      Object.keys(itemSelects).forEach(function (slug) { items[slug] = itemSelects[slug].value; });

      const payload = {
        employee_id: employeeSelect.value,
        site: siteSelect.value,
        shift: shiftSelect.value,
        inspector: inspectorSelect.value,
        observations: observationsInput.value,
        evidence_filename: evidenceInput.value,
        items: items,
        existing_ids: data().inspections.map(function (r) { return r.id; }),
        existing_followup_ids: data().followups.map(function (f) { return f.id; }),
      };

      const response = await global.ArrisePortalApi.postJSON("/soluciones/uniform/api/crear/", payload);
      const errorsBox = form.querySelector("[data-form-errors]");
      global.ArriseDom.clear(errorsBox);

      if (!response.ok) {
        Object.keys(response.errors || {}).forEach(function (field) {
          errorsBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[field]]));
        });
        return;
      }
      data().inspections.push(response.result.inspection);
      if (response.result.followup) {
        data().followups.push(response.result.followup);
      }
      global.ArrisePortal.saveState();
      renderTable();
      renderFollowups();
      renderKpis();
      renderAnalytics();
      global.ArriseModal.close();
      const inspection = response.result.inspection;
      if (inspection.status === "conforme") {
        global.ArriseToast.success("Inspección " + inspection.id + " registrada: conforme.");
      } else if (inspection.status === "seguimiento") {
        global.ArriseToast.info("Inspección " + inspection.id + " registrada: requiere seguimiento" + (response.result.followup ? " (" + response.result.followup.id + ")" : "") + ".");
      } else {
        global.ArriseToast.success("Inspección " + inspection.id + " registrada: sin evaluación.");
      }
    });
  }

  // ---------------- Inspection detail modal ----------------

  function openDetail(inspectionId) {
    const record = data().inspections.find(function (r) { return r.id === inspectionId; });
    if (!record) return;
    const { h } = global.ArriseDom;

    const followup = record.followup_id ? data().followups.find(function (f) { return f.id === record.followup_id; }) : null;

    const itemsTable = h("table", { class: "data-table" }, [
      h("thead", {}, [h("tr", {}, [h("th", {}, ["Elemento"]), h("th", {}, ["Estado"])])]),
      h("tbody", {}, record.items.map(function (it) {
        return h("tr", {}, [
          h("td", {}, [it.label]),
          h("td", {}, [h("span", { class: "badge " + itemBadgeClass(it.status) }, [ITEM_STATUS_LABELS[it.status] || it.status])]),
        ]);
      })),
    ]);

    const timeline = h("ul", { class: "timeline" }, record.history.slice().reverse().map(function (entry) {
      return h("li", { class: "timeline-item" }, [
        h("time", {}, [global.ArriseDom.formatDateTime(entry.at)]),
        h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
      ]);
    }));

    const followupBlock = followup
      ? h("div", { class: "card card-padded" }, [
          h("p", { style: "margin:0 0 4px;" }, [
            "Seguimiento correctivo ",
            h("strong", {}, [followup.id]),
            " — ",
            h("span", { class: "badge " + followupBadgeClass(followup.status) }, [FOLLOWUP_STATUS_LABELS[followup.status]]),
          ]),
          h("p", { class: "text-secondary", style: "margin:0;" }, ["Responsable: " + followup.responsible_name + " · Fecha límite: " + global.ArriseDom.formatDate(followup.due_date)]),
        ])
      : null;

    const body = h("div", { class: "stack" }, [
      h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
        h("div", {}, [h("dt", {}, ["Colaborador"]), h("dd", {}, [record.employee_name])]),
        h("div", {}, [h("dt", {}, ["Rol"]), h("dd", {}, [record.role_label])]),
        h("div", {}, [h("dt", {}, ["Sede"]), h("dd", {}, [siteName(record.site)])]),
        h("div", {}, [h("dt", {}, ["Turno"]), h("dd", {}, [SHIFT_LABELS[record.shift] || record.shift])]),
        h("div", {}, [h("dt", {}, ["Inspector"]), h("dd", {}, [record.inspector])]),
        h("div", {}, [h("dt", {}, ["Evidencia (simulada)"]), h("dd", {}, [record.evidence_filename])]),
        h("div", {}, [h("dt", {}, ["Score"]), h("dd", {}, [scoreLabel(record.score)])]),
        h("div", {}, [h("dt", {}, ["Resultado"]), h("dd", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [INSPECTION_STATUS_LABELS[record.status]])])]),
      ]),
      record.observations ? h("p", {}, [h("strong", {}, ["Observaciones: "]), record.observations]) : null,
      h("p", { class: "text-secondary", style: "font-size: 0.85em;" }, ["Guía de demostración: 100% de elementos aplicables «Conforme» = conforme; cualquier otro resultado evaluable requiere seguimiento. No es una política oficial de ARRISE."]),
      h("h3", {}, ["Checklist"]),
      itemsTable,
      followupBlock,
      h("hr"),
      h("h3", {}, ["Historial"]),
      timeline,
    ]);

    global.ArriseModal.open({ title: record.id + " — " + record.employee_name, body: body });
  }

  // ---------------- Followups tab ----------------

  function matchesFollowupFilters(followup) {
    const q = (document.querySelector('[data-uniform-followup-filter="q"]').value || "").trim().toLowerCase();
    const site = document.querySelector('[data-uniform-followup-filter="site"]').value;
    const status = document.querySelector('[data-uniform-followup-filter="status"]').value;
    if (site && followup.site !== site) return false;
    if (status && followup.status !== status) return false;
    if (q && followup.employee_name.toLowerCase().indexOf(q) === -1 && followup.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  function filteredFollowups() {
    return data().followups.filter(matchesFollowupFilters).slice().sort(function (a, b) {
      return new Date(a.due_date) - new Date(b.due_date);
    });
  }

  function renderFollowups() {
    const { h, clear, formatDate } = global.ArriseDom;
    const tbody = document.querySelector("[data-uniform-followups-body]");
    const empty = document.querySelector("[data-uniform-followups-empty]");
    if (!tbody) return;
    clear(tbody);
    const followups = filteredFollowups();
    empty.hidden = followups.length !== 0;

    followups.forEach(function (followup) {
      const issuesText = followup.issues.map(function (i) { return i.label; }).join(", ") || "—";
      tbody.append(h("tr", {}, [
        h("td", { class: "mono" }, [followup.id]),
        h("td", {}, [h("a", { href: "#", onClick: function (evt) { evt.preventDefault(); openDetail(followup.inspection_id); } }, [followup.inspection_id])]),
        h("td", {}, [followup.employee_name]),
        h("td", {}, [siteName(followup.site)]),
        h("td", {}, [issuesText]),
        h("td", {}, [followup.responsible_name]),
        h("td", {}, [formatDate(followup.due_date)]),
        h("td", {}, [h("span", { class: "badge " + followupBadgeClass(followup.status) }, [FOLLOWUP_STATUS_LABELS[followup.status]])]),
        h("td", {}, [
          followup.status === "pendiente"
            ? h("button", { type: "button", class: "btn btn-secondary btn-sm", onClick: function () { openResolveForm(followup); } }, ["Marcar resuelto"])
            : "",
        ]),
      ]));
    });
  }

  function openResolveForm(followup) {
    const { h } = global.ArriseDom;
    const noteInput = h("textarea", { id: "uniform-resolve-note", class: "textarea", maxlength: "500" });
    const form = h("form", { id: "uniform-resolve-form" }, [
      h("p", {}, ["Seguimiento ", h("strong", {}, [followup.id]), " — colaborador ", followup.employee_name, "."]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "uniform-resolve-note" }, ["Nota de cierre (opcional)"]),
        noteInput,
      ]),
      h("div", { "data-form-errors": "1" }, []),
    ]);
    const submitBtn = h("button", { type: "submit", form: "uniform-resolve-form", class: "btn btn-primary" }, ["Confirmar resolución"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({ title: "Resolver seguimiento correctivo", body: form, footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]) });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const response = await global.ArrisePortalApi.postJSON("/soluciones/uniform/api/seguimiento/resolver/", {
        id: followup.id,
        current_status: followup.status,
        actor: followup.responsible_name,
        note: noteInput.value,
      });
      const errorsBox = form.querySelector("[data-form-errors]");
      global.ArriseDom.clear(errorsBox);
      if (!response.ok) {
        Object.keys(response.errors || {}).forEach(function (field) {
          errorsBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[field]]));
        });
        return;
      }
      followup.status = response.result.status;
      followup.history.push(response.result.history_entry);
      global.ArrisePortal.saveState();
      global.ArriseModal.close();
      renderFollowups();
      renderKpis();
      renderAnalytics();
      global.ArriseToast.success("Seguimiento " + followup.id + " marcado como resuelto.");
    });
  }

  // ---------------- Analytics tab ----------------

  let siteChart = null;
  let shiftChart = null;
  let violationsChart = null;

  function complianceByKey(inspections, keyFn, keys) {
    return keys.map(function (key) {
      const subset = inspections.filter(function (i) { return keyFn(i) === key && i.score !== null && i.score !== undefined; });
      const conformes = subset.filter(function (i) { return i.score === 100; }).length;
      return subset.length ? Math.round((conformes / subset.length) * 100) : 0;
    });
  }

  function renderAnalytics() {
    const inspections = data().inspections;
    const siteSlugs = SITES.map(function (s) { return s.slug; });
    const siteLabels = SITES.map(function (s) { return s.name; });
    const shiftSlugs = SHIFTS.map(function (s) { return s.slug; });
    const shiftLabels = SHIFTS.map(function (s) { return s.label; });

    const siteRates = complianceByKey(inspections, function (i) { return i.site; }, siteSlugs);
    const shiftRates = complianceByKey(inspections, function (i) { return i.shift; }, shiftSlugs);

    const violationCounts = {};
    CHECKLIST_ITEMS.forEach(function (item) { violationCounts[item.slug] = 0; });
    inspections.forEach(function (inspection) {
      inspection.items.forEach(function (it) {
        if (it.status === "faltante" || it.status === "danado") {
          violationCounts[it.slug] = (violationCounts[it.slug] || 0) + 1;
        }
      });
    });
    const rankedViolations = CHECKLIST_ITEMS
      .map(function (item) { return { slug: item.slug, label: CHECKLIST_ITEM_LABELS[item.slug], count: violationCounts[item.slug] || 0 }; })
      .sort(function (a, b) { return b.count - a.count; });

    const siteCanvas = document.querySelector('[data-chart="site"]');
    if (global.Chart && siteCanvas && siteCanvas.offsetParent !== null) {
      if (siteChart) siteChart.destroy();
      siteChart = new global.Chart(siteCanvas, {
        type: "bar",
        data: { labels: siteLabels, datasets: [{ label: "% conforme", data: siteRates, backgroundColor: "#0e9f6e" }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, max: 100, ticks: { callback: function (v) { return v + "%"; } } } },
        },
      });

      const shiftCanvas = document.querySelector('[data-chart="shift"]');
      if (shiftChart) shiftChart.destroy();
      shiftChart = new global.Chart(shiftCanvas, {
        type: "bar",
        data: { labels: shiftLabels, datasets: [{ label: "% conforme", data: shiftRates, backgroundColor: "#2f6fd6" }] },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, max: 100, ticks: { callback: function (v) { return v + "%"; } } } },
        },
      });

      const violationsCanvas = document.querySelector('[data-chart="violations"]');
      if (violationsChart) violationsChart.destroy();
      violationsChart = new global.Chart(violationsCanvas, {
        type: "bar",
        data: {
          labels: rankedViolations.map(function (v) { return v.label; }),
          datasets: [{ label: "Incumplimientos", data: rankedViolations.map(function (v) { return v.count; }), backgroundColor: "#e02424" }],
        },
        options: {
          indexAxis: "y",
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }

    const { h, clear } = global.ArriseDom;
    const tbody = document.querySelector("[data-uniform-violations-body]");
    if (tbody) {
      clear(tbody);
      rankedViolations.forEach(function (v) {
        tbody.append(h("tr", {}, [h("td", {}, [v.label]), h("td", {}, [String(v.count)])]));
      });
    }
  }

  function init() {
    document.querySelectorAll("[data-uniform-new]").forEach(function (btn) {
      btn.addEventListener("click", openCreateForm);
    });
    document.querySelectorAll("[data-uniform-filter]").forEach(function (el) {
      el.addEventListener("input", renderTable);
      el.addEventListener("change", renderTable);
    });
    document.querySelectorAll("[data-uniform-followup-filter]").forEach(function (el) {
      el.addEventListener("input", renderFollowups);
      el.addEventListener("change", renderFollowups);
    });

    const analyticsPanel = document.getElementById("panel-analitica");
    if (analyticsPanel) analyticsPanel.addEventListener("arrise:tab-shown", renderAnalytics);

    renderTable();
    renderFollowups();
    renderKpis();
    renderAnalytics();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
