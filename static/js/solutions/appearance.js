/**
 * Appearance Check: search-collaborator + create modal, reviews table with
 * filters, and a detail modal that walks pending -> in_review -> completed
 * (start review / complete review with the demo checklist). All rendering
 * reads `ArrisePortal.state.solutions.appearance` so it reflects whatever
 * this tab has done so far (see state/bootstrap.js).
 *
 * IMPORTANT (see mock_data/appearance.py and solutions/services/appearance.py
 * docstrings for the full ethics write-up): this file never computes
 * `approved`/`requires_review` from the checklist. The "complete review"
 * form always sends whatever the human reviewer explicitly picked in the
 * "Resultado de la revisión" radio group — the checklist checkboxes are
 * submitted purely as recorded context. There is no image upload or photo
 * analysis anywhere here: "evidence" is one plain text field, like the CV
 * filename field in Referral Portal.
 *
 * `TRANSITIONS` mirrors `solutions.services.appearance.GRAPH` /
 * `mock_data.appearance.TRANSITIONS` for optimistic UI only — Django is
 * still the authority and revalidates every transition server-side.
 */
(function (global) {
  "use strict";

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return null;
    try { return JSON.parse(node.textContent); } catch (e) { return null; }
  }

  const STATUSES = readJSON("appearance-statuses") || [];
  const RESULTS = readJSON("appearance-results") || [];
  const SHIFTS = readJSON("appearance-shifts") || [];
  const ROLES = readJSON("appearance-roles") || [];
  const CRITERIA = readJSON("appearance-criteria") || [];
  const SITES = readJSON("appearance-sites") || [];
  const EMPLOYEES = readJSON("appearance-employees") || [];
  const TODAY = readJSON("appearance-today") || "";

  function toLabelMap(list) {
    return list.reduce(function (acc, item) { acc[item.slug] = item.label; return acc; }, {});
  }

  const STATUS_LABELS = toLabelMap(STATUSES);
  const RESULT_LABELS = toLabelMap(RESULTS);
  const SHIFT_LABELS = toLabelMap(SHIFTS);
  const ROLE_LABELS = toLabelMap(ROLES);
  const EMPLOYEES_BY_ID = EMPLOYEES.reduce(function (acc, e) { acc[e.id] = e; return acc; }, {});
  const TERMINAL = new Set(["completed"]);

  const TRANSITIONS = { pending: ["in_review"], in_review: ["completed"], completed: [] };

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    // Merge field-by-field (not `||` on the whole object): a tab whose
    // sessionStorage was seeded before this field existed would otherwise
    // keep a stale shape and crash every renderer that reads it.
    const existing = state.solutions.appearance || {};
    state.solutions.appearance = {
      records: existing.records || [],
      monthly_series: existing.monthly_series || [],
      last_sync: existing.last_sync || null,
    };
    return state.solutions.appearance;
  }

  function siteName(slug) {
    const s = SITES.find(function (x) { return x.slug === slug; });
    return s ? s.name : slug;
  }

  function statusBadgeClass(status) {
    if (status === "completed") return "badge-success";
    if (status === "in_review") return "badge-warning";
    return "badge-info";
  }

  function resultBadgeClass(result) {
    if (result === "approved") return "badge-success";
    if (result === "requires_review") return "badge-danger";
    return "badge-neutral";
  }

  function lastActivityAt(record) {
    const last = record.history && record.history.length ? record.history[record.history.length - 1] : null;
    return last ? last.at : record.created_at;
  }

  function isOverdueFollowUp(record) {
    return !!(record.follow_up && record.follow_up.due_date && TODAY && record.follow_up.due_date < TODAY);
  }

  // ---------------- KPIs / alerts ----------------

  function renderKpis() {
    const records = data().records;
    const todayCount = records.filter(function (r) { return TODAY && (r.created_at || "").slice(0, 10) === TODAY; }).length;
    const completed = records.filter(function (r) { return r.status === "completed"; });
    const approved = completed.filter(function (r) { return r.result === "approved"; });
    const pending = records.filter(function (r) { return r.status !== "completed"; });

    let totalMinutes = 0;
    let timedCount = 0;
    completed.forEach(function (r) {
      if (r.started_at && r.completed_at) {
        const mins = (new Date(r.completed_at) - new Date(r.started_at)) / 60000;
        if (mins >= 0) { totalMinutes += mins; timedCount += 1; }
      }
    });

    setKpi("today", todayCount);
    setKpi("approval-rate", completed.length ? Math.round((approved.length / completed.length) * 100) + "%" : "Sin datos");
    setKpi("pending", pending.length);
    setKpi("avg-time", timedCount ? Math.round(totalMinutes / timedCount) + " min" : "Sin datos");

    const lastSyncEl = document.querySelector("[data-appearance-last-sync]");
    if (lastSyncEl) lastSyncEl.textContent = global.ArriseDom.formatDateTime(data().last_sync);
  }

  function setKpi(key, value) {
    const el = document.querySelector('[data-appearance-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function renderFollowUps() {
    const { h, clear } = global.ArriseDom;
    const box = document.querySelector("[data-appearance-followups]");
    const list = document.querySelector("[data-appearance-followups-list]");
    if (!box || !list) return;
    clear(list);
    const overdue = data().records.filter(isOverdueFollowUp);
    box.hidden = overdue.length === 0;
    overdue.forEach(function (r) {
      list.append(h("li", {}, [
        h("a", { href: "#", onClick: function (evt) { evt.preventDefault(); openDetail(r.id); } }, [r.id + " — " + r.employee_name]),
        " — seguimiento de " + r.follow_up.responsible_name + " venció el " + global.ArriseDom.formatDate(r.follow_up.due_date) + ".",
      ]));
    });
  }

  // ---------------- Reviews table ----------------

  function matchesFilters(record) {
    const q = (document.querySelector('[data-appearance-filter="q"]').value || "").trim().toLowerCase();
    const site = document.querySelector('[data-appearance-filter="site"]').value;
    const role = document.querySelector('[data-appearance-filter="role"]').value;
    const shift = document.querySelector('[data-appearance-filter="shift"]').value;
    const status = document.querySelector('[data-appearance-filter="status"]').value;
    const result = document.querySelector('[data-appearance-filter="result"]').value;
    if (site && record.site !== site) return false;
    if (role && record.role !== role) return false;
    if (shift && record.shift !== shift) return false;
    if (status && record.status !== status) return false;
    if (result && record.result !== result) return false;
    if (q && record.employee_name.toLowerCase().indexOf(q) === -1 && record.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  function filteredRecords() {
    return data().records.filter(matchesFilters).slice().sort(function (a, b) {
      return new Date(lastActivityAt(b)) - new Date(lastActivityAt(a));
    });
  }

  function renderTable() {
    const { h, clear } = global.ArriseDom;
    const tbody = document.querySelector("[data-appearance-table-body]");
    const empty = document.querySelector("[data-appearance-empty]");
    if (!tbody) return;
    clear(tbody);
    const records = filteredRecords();
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
          h("td", {}, [siteName(record.site)]),
          h("td", {}, [ROLE_LABELS[record.role] || record.role]),
          h("td", {}, [SHIFT_LABELS[record.shift] || record.shift]),
          h("td", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status] || record.status])]),
          h("td", {}, [record.result ? h("span", { class: "badge " + resultBadgeClass(record.result) }, [RESULT_LABELS[record.result]]) : "—"]),
          h("td", {}, [global.ArriseDom.formatDateTime(lastActivityAt(record))]),
        ]
      ));
    });
  }

  // ---------------- Create modal ----------------

  function parseEmployeeInput(value) {
    const raw = (value || "").trim();
    const match = raw.match(/^([A-Z]+-\d+)/);
    const id = match ? match[1] : raw;
    return EMPLOYEES_BY_ID[id] ? id : "";
  }

  function openCreateForm() {
    const { h } = global.ArriseDom;
    const employeeInput = h("input", {
      id: "apr-employee", name: "employee_display", class: "input", list: "apr-employee-options",
      placeholder: "Escribe un nombre o ID…", required: "required", autocomplete: "off",
    });
    const form = h("form", { id: "appearance-create-form" }, [
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "apr-employee" }, ["Colaborador ficticio", h("span", { class: "required-mark" }, ["*"])]),
        employeeInput,
        h("datalist", { id: "apr-employee-options" }, EMPLOYEES.map(function (e) {
          return h("option", { value: e.id + " — " + e.name }, []);
        })),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "apr-site" }, ["Sede", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "apr-site", name: "site", class: "select", required: "required" },
            SITES.map(function (s) { return h("option", { value: s.slug }, [s.name]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "apr-role" }, ["Área/rol", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "apr-role", name: "role", class: "select", required: "required" },
            ROLES.map(function (r) { return h("option", { value: r.slug }, [r.label]); })),
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "apr-shift" }, ["Turno", h("span", { class: "required-mark" }, ["*"])]),
        h("select", { id: "apr-shift", name: "shift", class: "select", required: "required" },
          SHIFTS.map(function (s) { return h("option", { value: s.slug }, [s.label]); })),
      ]),
      h("div", { "data-form-errors": "1" }, []),
    ]);

    const submitBtn = h("button", { type: "submit", form: "appearance-create-form", class: "btn btn-primary" }, ["Registrar revisión"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({
      title: "Nueva revisión de preparación",
      body: form,
      footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]),
    });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const payload = {
        employee_id: parseEmployeeInput(employeeInput.value),
        site: document.getElementById("apr-site").value,
        role: document.getElementById("apr-role").value,
        shift: document.getElementById("apr-shift").value,
        existing_ids: data().records.map(function (r) { return r.id; }),
      };
      const response = await global.ArrisePortalApi.postJSON("/soluciones/appearance/api/crear/", payload);
      const errorsBox = form.querySelector("[data-form-errors]");
      global.ArriseDom.clear(errorsBox);

      if (!response.ok) {
        Object.keys(response.errors || {}).forEach(function (field) {
          errorsBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[field]]));
        });
        return;
      }
      data().records.push(response.result.record);
      global.ArrisePortal.saveState();
      renderTable();
      renderKpis();
      renderFollowUps();
      global.ArriseModal.close();
      global.ArriseToast.success("Revisión " + response.result.record.id + " registrada como pendiente.");
    });
  }

  // ---------------- Detail / start / complete modal ----------------

  function openDetail(recordId) {
    const record = data().records.find(function (r) { return r.id === recordId; });
    if (!record) return;
    const { h } = global.ArriseDom;

    const meta = h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
      h("div", {}, [h("dt", {}, ["Colaborador"]), h("dd", {}, [record.employee_name])]),
      h("div", {}, [h("dt", {}, ["Correo"]), h("dd", {}, [record.employee_email])]),
      h("div", {}, [h("dt", {}, ["Sede"]), h("dd", {}, [siteName(record.site)])]),
      h("div", {}, [h("dt", {}, ["Área/rol"]), h("dd", {}, [ROLE_LABELS[record.role] || record.role])]),
      h("div", {}, [h("dt", {}, ["Turno"]), h("dd", {}, [SHIFT_LABELS[record.shift] || record.shift])]),
      h("div", {}, [h("dt", {}, ["Estado"]), h("dd", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status]])])]),
    ]);

    const timeline = h("ul", { class: "timeline" }, record.history.slice().reverse().map(function (entry) {
      return h("li", { class: "timeline-item" }, [
        h("time", {}, [global.ArriseDom.formatDateTime(entry.at)]),
        h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
      ]);
    }));

    const sections = [meta];

    if (record.status === "pending") {
      sections.push(h("div", { class: "cluster" }, [
        h("button", { type: "button", class: "btn btn-primary btn-sm", onClick: function () { startReview(record); } }, ["Iniciar revisión"]),
      ]));
    } else if (record.status === "in_review") {
      sections.push(buildCompleteForm(record));
    } else {
      sections.push(buildCompletedSummary(record));
    }

    sections.push(h("hr"));
    sections.push(h("h3", {}, ["Historial"]));
    sections.push(timeline);

    global.ArriseModal.open({ title: record.id + " — " + record.employee_name, body: h("div", { class: "stack" }, sections) });

    if (record.status === "in_review") wireCompleteForm(record);
  }

  function buildCompletedSummary(record) {
    const { h } = global.ArriseDom;
    const criteriaList = h("ul", { style: "margin:0; padding-left: 1.1em;" }, (record.criteria_results || []).map(function (c) {
      const crit = CRITERIA.find(function (item) { return item.slug === c.slug; });
      const label = crit ? crit.label : c.slug;
      return h("li", {}, [(c.checked ? "✔ " : "— ") + label + (c.note ? " (" + c.note + ")" : "")]);
    }));

    const parts = [
      h("h3", {}, ["Resultado de la revisión"]),
      h("p", {}, [record.result ? h("span", { class: "badge " + resultBadgeClass(record.result) }, [RESULT_LABELS[record.result]]) : "—"]),
      h("h3", {}, ["Criterios operativos demo"]),
      criteriaList,
      h("h3", {}, ["Observaciones de presentación"]),
      h("p", {}, [record.presentation_notes || "—"]),
    ];
    if (record.tattoo_notes) {
      parts.push(h("h3", {}, ["Observaciones sobre tatuajes (contexto operativo)"]));
      parts.push(h("p", {}, [record.tattoo_notes]));
    }
    parts.push(h("h3", {}, ["Evidencia"]));
    parts.push(h("p", {}, [record.evidence_filename || "—"]));
    if (record.follow_up) {
      parts.push(h("h3", {}, ["Seguimiento"]));
      parts.push(h("p", {}, [
        "Responsable: " + record.follow_up.responsible_name + " · Fecha límite: " + global.ArriseDom.formatDate(record.follow_up.due_date)
        + (isOverdueFollowUp(record) ? " (vencido)" : ""),
      ]));
    }
    return h("div", { class: "stack" }, parts);
  }

  function buildCompleteForm(record) {
    const { h } = global.ArriseDom;
    const criteriaFields = CRITERIA.map(function (c) {
      return h("div", { class: "field", style: "border-bottom: 1px solid var(--color-border); padding-bottom: var(--space-2);" }, [
        h("label", { class: "field-label" }, [
          h("input", { type: "checkbox", "data-criteria-check": c.slug, style: "margin-right: 6px;" }),
          c.label,
        ]),
        h("input", { type: "text", class: "input", "data-criteria-note": c.slug, placeholder: "Nota opcional…", maxlength: "280" }),
      ]);
    });

    return h("form", { id: "appearance-complete-form", class: "stack" }, [
      h("h3", { style: "margin-bottom:0;" }, ["Criterios operativos demo"]),
      h("p", { class: "text-secondary", style: "margin-top:2px;" }, ["Contexto de apoyo para la persona revisora; no calculan el resultado automáticamente."]),
      h("div", { class: "stack" }, criteriaFields),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "apr-presentation-notes" }, ["Observaciones de presentación", h("span", { class: "required-mark" }, ["*"])]),
        h("textarea", { id: "apr-presentation-notes", class: "textarea", required: "required", maxlength: "1000" }),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "apr-tattoo-notes" }, ["Observaciones sobre tatuajes (opcional, contexto operativo)"]),
        h("textarea", { id: "apr-tattoo-notes", class: "textarea", maxlength: "500" }),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "apr-evidence" }, ["Evidencia (nombre de archivo simulado, opcional)"]),
        h("input", { id: "apr-evidence", class: "input", maxlength: "120", placeholder: "registro_ingreso_demo.jpg" }),
      ]),
      h("div", { class: "field" }, [
        h("span", { class: "field-label" }, ["Resultado de la revisión (decisión humana)", h("span", { class: "required-mark" }, ["*"])]),
        h("label", { style: "display:block;" }, [
          h("input", { type: "radio", name: "resultado", value: "approved", required: "required" }), " Aprobado",
        ]),
        h("label", { style: "display:block;" }, [
          h("input", { type: "radio", name: "resultado", value: "requires_review", required: "required" }), " Requiere revisión",
        ]),
      ]),
      h("div", { "data-followup-fields": "1", hidden: true, class: "stack" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "apr-followup-responsible" }, ["Responsable del seguimiento"]),
          h("select", { id: "apr-followup-responsible", class: "select" },
            [h("option", { value: "" }, ["Selecciona…"])].concat(
              EMPLOYEES.map(function (e) { return h("option", { value: e.id }, [e.name]); })
            )),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "apr-followup-due" }, ["Fecha límite de seguimiento"]),
          h("input", { id: "apr-followup-due", type: "date", class: "input" }),
        ]),
      ]),
      h("div", { "data-form-errors": "1" }, []),
      h("div", { class: "cluster" }, [
        h("button", { type: "submit", class: "btn btn-primary" }, ["Completar revisión"]),
      ]),
    ]);
  }

  function wireCompleteForm(record) {
    const form = document.getElementById("appearance-complete-form");
    if (!form) return;
    const followupFields = form.querySelector("[data-followup-fields]");

    form.querySelectorAll('input[name="resultado"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        followupFields.hidden = radio.value !== "requires_review" || !radio.checked;
      });
    });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const resultado = (form.querySelector('input[name="resultado"]:checked') || {}).value;
      const criteria = CRITERIA.map(function (c) {
        const checkbox = form.querySelector('[data-criteria-check="' + c.slug + '"]');
        const noteInput = form.querySelector('[data-criteria-note="' + c.slug + '"]');
        return { slug: c.slug, checked: !!(checkbox && checkbox.checked), note: noteInput ? noteInput.value : "" };
      });
      const payload = {
        id: record.id,
        current_status: record.status,
        presentation_notes: document.getElementById("apr-presentation-notes").value,
        tattoo_notes: document.getElementById("apr-tattoo-notes").value,
        evidence_filename: document.getElementById("apr-evidence").value,
        resultado: resultado,
        criteria: criteria,
      };
      if (resultado === "requires_review") {
        payload.follow_up = {
          responsible_id: document.getElementById("apr-followup-responsible").value,
          due_date: document.getElementById("apr-followup-due").value,
        };
      }

      const response = await global.ArrisePortalApi.postJSON("/soluciones/appearance/api/completar/", payload);
      const errorsBox = form.querySelector("[data-form-errors]");
      global.ArriseDom.clear(errorsBox);
      if (!response.ok) {
        Object.keys(response.errors || {}).forEach(function (field) {
          errorsBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[field]]));
        });
        return;
      }

      record.status = response.result.status;
      record.completed_at = response.result.completed_at;
      record.criteria_results = response.result.criteria_results;
      record.presentation_notes = response.result.presentation_notes;
      record.tattoo_notes = response.result.tattoo_notes;
      record.evidence_filename = response.result.evidence_filename;
      record.result = response.result.result;
      record.follow_up = response.result.follow_up;
      (response.result.history_entries || []).forEach(function (entry) { record.history.push(entry); });
      addNotification(response.result.notify, record.id);
      global.ArrisePortal.saveState();
      global.ArriseModal.close();
      renderTable();
      renderKpis();
      renderFollowUps();
      global.ArriseToast.success("Revisión " + record.id + " completada.");
    });
  }

  async function startReview(record) {
    const response = await global.ArrisePortalApi.postJSON("/soluciones/appearance/api/iniciar/", {
      id: record.id,
      current_status: record.status,
    });
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo iniciar la revisión.");
      return;
    }
    record.status = response.result.status;
    record.started_at = response.result.started_at;
    record.history.push(response.result.history_entry);
    global.ArrisePortal.saveState();
    renderTable();
    renderKpis();
    global.ArriseModal.close();
    global.ArriseToast.success("Revisión " + record.id + " iniciada.");
    openDetail(record.id);
  }

  function addNotification(body, recordId) {
    const state = global.ArrisePortal.state;
    state.core = state.core || {};
    state.core.notifications = state.core.notifications || [];
    state.core.notifications.unshift({
      id: "notif-" + Date.now(),
      title: "Actualización de Appearance Check",
      body: body,
      read: false,
      at: new Date().toISOString(),
      link: "/soluciones/appearance/",
    });
  }

  // ---------------- Analítica tab ----------------

  let trendChart = null;
  let siteChart = null;

  function renderAnalytics() {
    const series = data().monthly_series || [];
    const executions = series.reduce(function (sum, m) { return sum + m.executions; }, 0);
    const success = series.reduce(function (sum, m) { return sum + m.success; }, 0);
    const hoursSaved = series.reduce(function (sum, m) { return sum + m.hours_saved; }, 0);
    const allScores = series.reduce(function (acc, m) { return acc.concat(m.satisfaction_scores || []); }, []);
    const avgSatisfaction = allScores.length ? (allScores.reduce(function (a, b) { return a + b; }, 0) / allScores.length) : null;

    setTrendKpi("executions", executions);
    setTrendKpi("success-rate", executions ? Math.round((success / executions) * 100) + "%" : "Sin datos");
    setTrendKpi("hours-saved", Math.round(hoursSaved) + " h");
    setTrendKpi("satisfaction", avgSatisfaction !== null ? avgSatisfaction.toFixed(1) + " / 5" : "Sin datos");

    const trendCanvas = document.querySelector('[data-chart="trend"]');
    if (global.Chart && trendCanvas && trendCanvas.offsetParent !== null) {
      if (trendChart) trendChart.destroy();
      trendChart = new global.Chart(trendCanvas, {
        type: "bar",
        data: {
          labels: series.map(function (m) { return m.month; }),
          datasets: [
            { label: "Aprobadas", data: series.map(function (m) { return m.success; }), backgroundColor: "#0e9f6e", stack: "s" },
            { label: "Requieren revisión", data: series.map(function (m) { return m.fail; }), backgroundColor: "#e02424", stack: "s" },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }

    const siteCanvas = document.querySelector('[data-chart="site"]');
    const records = data().records;
    const bySite = SITES.map(function (s) {
      return { site: s, count: records.filter(function (r) { return r.site === s.slug; }).length };
    });
    if (global.Chart && siteCanvas && siteCanvas.offsetParent !== null) {
      if (siteChart) siteChart.destroy();
      siteChart = new global.Chart(siteCanvas, {
        type: "bar",
        data: {
          labels: bySite.map(function (x) { return x.site.name; }),
          datasets: [{ label: "Revisiones", data: bySite.map(function (x) { return x.count; }), backgroundColor: "#1c64f2" }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }

    const { h, clear } = global.ArriseDom;
    const tbody = document.querySelector("[data-appearance-monthly-body]");
    if (tbody) {
      clear(tbody);
      series.forEach(function (m) {
        tbody.append(h("tr", {}, [
          h("td", {}, [m.month]),
          h("td", {}, [String(m.executions)]),
          h("td", {}, [String(m.success)]),
          h("td", {}, [String(m.fail)]),
          h("td", {}, [String(m.hours_saved)]),
        ]));
      });
    }

    const activityList = document.querySelector("[data-appearance-activity]");
    if (activityList) {
      clear(activityList);
      const events = [];
      records.forEach(function (r) {
        (r.history || []).forEach(function (entry) {
          events.push({ record: r, entry: entry });
        });
      });
      events.sort(function (a, b) { return new Date(b.entry.at) - new Date(a.entry.at); });
      events.slice(0, 12).forEach(function (item) {
        activityList.append(h("li", {}, [
          h("a", { href: "#", onClick: function (evt) { evt.preventDefault(); openDetail(item.record.id); } }, [item.record.id]),
          " — " + item.entry.detail + " (" + global.ArriseDom.formatDateTime(item.entry.at) + ")",
        ]));
      });
    }
  }

  function setTrendKpi(key, value) {
    const el = document.querySelector('[data-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function renderAll() {
    renderTable();
    renderKpis();
    renderFollowUps();
    renderAnalytics();
  }

  function init() {
    document.querySelectorAll("[data-appearance-new]").forEach(function (btn) {
      btn.addEventListener("click", openCreateForm);
    });
    document.querySelectorAll("[data-appearance-filter]").forEach(function (el) {
      el.addEventListener("input", renderTable);
      el.addEventListener("change", renderTable);
    });

    const analyticsPanel = document.getElementById("panel-analitica");
    if (analyticsPanel) analyticsPanel.addEventListener("arrise:tab-shown", renderAnalytics);

    renderAll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
