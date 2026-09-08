/**
 * Security Database Hub: incidents table + detail/transition/assign modal +
 * create modal + floor controls tab + trend tab. All rendering reads
 * `ArrisePortal.state.solutions.security` so it reflects whatever this tab
 * has done so far (see state/bootstrap.js for how that state is seeded/
 * persisted).
 *
 * The `TRANSITIONS` map below mirrors
 * `solutions.services.security.GRAPH` / `mock_data.security.TRANSITIONS`
 * for optimistic UI only (disabling buttons the server would reject
 * anyway) — Django is still the authority and revalidates every
 * transition/assignment server-side.
 */
(function (global) {
  "use strict";

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (e) { return []; }
  }

  const STATUSES = readJSON("security-statuses");
  const CATEGORIES = readJSON("security-categories");
  const SEVERITIES = readJSON("security-severities");
  const CONTROL_TYPES = readJSON("security-control-types");
  const CONTROL_STATUSES = readJSON("security-control-statuses");
  const SITES = readJSON("security-sites");
  const FLOORS = readJSON("security-floors");
  const ASSIGNEES = readJSON("security-assignees");

  function toLabelMap(list) {
    return list.reduce(function (acc, item) { acc[item.slug] = item.label; return acc; }, {});
  }

  const STATUS_LABELS = toLabelMap(STATUSES);
  const CATEGORY_LABELS = toLabelMap(CATEGORIES);
  const SEVERITY_LABELS = toLabelMap(SEVERITIES);
  const CONTROL_TYPE_LABELS = toLabelMap(CONTROL_TYPES);
  const CONTROL_STATUS_LABELS = toLabelMap(CONTROL_STATUSES);
  const TERMINAL = new Set(["resolved", "closed"]);

  const TRANSITIONS = {
    new: ["assigned"],
    assigned: ["in_progress"],
    in_progress: ["resolved"],
    resolved: ["closed", "in_progress"],
    closed: ["in_progress"],
  };

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    // Merge field-by-field (not `||` on the whole object): a tab whose
    // sessionStorage was seeded before this module existed (or before a
    // field was added to initial_state()) would otherwise keep a stale
    // shape missing e.g. `controls` and crash every renderer that reads it.
    const existing = state.solutions.security || {};
    state.solutions.security = {
      records: existing.records || [],
      controls: existing.controls || [],
      monthly_series: existing.monthly_series || [],
      last_sync: existing.last_sync || null,
    };
    return state.solutions.security;
  }

  function siteName(slug) {
    const s = SITES.find(function (x) { return x.slug === slug; });
    return s ? s.name : slug;
  }

  function statusBadgeClass(status) {
    if (status === "resolved") return "badge-success";
    if (status === "closed") return "badge-neutral";
    if (status === "in_progress") return "badge-warning";
    if (status === "assigned") return "badge-info";
    return "badge-neutral";
  }

  function severityBadgeClass(severity) {
    if (severity === "critica") return "badge-danger";
    if (severity === "alta") return "badge-warning";
    if (severity === "media") return "badge-info";
    return "badge-neutral";
  }

  function lastActivityAt(record) {
    const last = record.history && record.history.length ? record.history[record.history.length - 1] : null;
    return last ? last.at : record.created_at;
  }

  // ---------------- KPIs / alerts ----------------

  function renderKpis() {
    const records = data().records;
    const controls = data().controls;
    const total = records.length;
    const open = records.filter(function (r) { return !TERMINAL.has(r.status); }).length;
    const critical = records.filter(function (r) { return r.severity === "critica" && !TERMINAL.has(r.status); }).length;
    const overdue = controls.filter(function (c) { return c.status === "vencido"; }).length;

    setKpi("total", total);
    setKpi("open", open);
    setKpi("critical", critical);
    setKpi("overdue", overdue);

    const lastSyncEl = document.querySelector("[data-security-last-sync]");
    if (lastSyncEl) lastSyncEl.textContent = global.ArriseDom.formatDateTime(data().last_sync);
  }

  function setKpi(key, value) {
    const el = document.querySelector('[data-security-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function renderAlerts() {
    const { h, clear } = global.ArriseDom;
    const box = document.querySelector("[data-security-alerts]");
    const list = document.querySelector("[data-security-alerts-list]");
    if (!box || !list) return;
    clear(list);
    const critical = data().records.filter(function (r) { return r.severity === "critica" && !TERMINAL.has(r.status); });
    box.hidden = critical.length === 0;
    critical.forEach(function (r) {
      list.append(h("li", {}, [
        h("a", { href: "#", onClick: function (evt) { evt.preventDefault(); openDetail(r.id); } }, [r.id + " — " + r.title]),
        " (" + siteName(r.site) + ", " + r.floor + ") — " + (STATUS_LABELS[r.status] || r.status),
      ]));
    });
  }

  // ---------------- Incidents table ----------------

  function matchesFilters(record) {
    const q = (document.querySelector('[data-security-filter="q"]').value || "").trim().toLowerCase();
    const site = document.querySelector('[data-security-filter="site"]').value;
    const floor = document.querySelector('[data-security-filter="floor"]').value;
    const category = document.querySelector('[data-security-filter="category"]').value;
    const severity = document.querySelector('[data-security-filter="severity"]').value;
    const status = document.querySelector('[data-security-filter="status"]').value;
    if (site && record.site !== site) return false;
    if (floor && record.floor !== floor) return false;
    if (category && record.category !== category) return false;
    if (severity && record.severity !== severity) return false;
    if (status && record.status !== status) return false;
    if (q && record.title.toLowerCase().indexOf(q) === -1 && record.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  function filteredRecords() {
    return data().records.filter(matchesFilters).slice().sort(function (a, b) {
      return new Date(lastActivityAt(b)) - new Date(lastActivityAt(a));
    });
  }

  function renderTable() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const tbody = document.querySelector("[data-security-table-body]");
    const empty = document.querySelector("[data-security-empty]");
    if (!tbody) return;
    clear(tbody);
    const records = filteredRecords();
    empty.hidden = records.length !== 0;

    records.forEach(function (record) {
      const row = h(
        "tr",
        {
          class: "row-link", tabindex: "0", role: "button", "aria-label": "Ver detalle de " + record.id,
          onClick: function () { openDetail(record.id); },
          onKeydown: function (evt) { if (evt.key === "Enter") openDetail(record.id); },
        },
        [
          h("td", { class: "mono" }, [record.id]),
          h("td", {}, [record.title]),
          h("td", {}, [siteName(record.site)]),
          h("td", {}, [record.floor]),
          h("td", {}, [CATEGORY_LABELS[record.category] || record.category]),
          h("td", {}, [h("span", { class: "badge " + severityBadgeClass(record.severity) }, [SEVERITY_LABELS[record.severity] || record.severity])]),
          h("td", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status] || record.status])]),
          h("td", {}, [record.assignee_name || "Sin asignar"]),
          h("td", {}, [formatDateTime(lastActivityAt(record))]),
        ]
      );
      tbody.append(row);
    });
  }

  // ---------------- Create modal ----------------

  function openCreateForm() {
    const { h } = global.ArriseDom;
    const form = h("form", { id: "security-create-form" }, [
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "sec-title" }, ["Título", h("span", { class: "required-mark" }, ["*"])]),
        h("input", { id: "sec-title", name: "title", class: "input", required: "required", maxlength: "140" }),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "sec-description" }, ["Descripción", h("span", { class: "required-mark" }, ["*"])]),
        h("textarea", { id: "sec-description", name: "description", class: "textarea", required: "required", maxlength: "1000" }),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sec-site" }, ["Sede", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sec-site", name: "site", class: "select", required: "required" },
            SITES.map(function (s) { return h("option", { value: s.slug }, [s.name]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sec-floor" }, ["Piso", h("span", { class: "required-mark" }, ["*"])]),
          h("input", { id: "sec-floor", name: "floor", class: "input", list: "security-floor-options", required: "required", maxlength: "40" }),
          h("datalist", { id: "security-floor-options" }, FLOORS.map(function (f) { return h("option", { value: f }, []); })),
        ]),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sec-category" }, ["Categoría", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sec-category", name: "category", class: "select", required: "required" },
            CATEGORIES.map(function (c) { return h("option", { value: c.slug }, [c.label]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sec-severity" }, ["Severidad", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sec-severity", name: "severity", class: "select", required: "required" },
            SEVERITIES.map(function (s) { return h("option", { value: s.slug }, [s.label]); })),
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "sec-assignee" }, ["Responsable (opcional)"]),
        h("select", { id: "sec-assignee", name: "assignee_id", class: "select" },
          [h("option", { value: "" }, ["Sin asignar"])].concat(
            ASSIGNEES.map(function (e) { return h("option", { value: e.id }, [e.name]); })
          )),
      ]),
      h("div", { "data-form-errors": "1" }, []),
    ]);

    const submitBtn = h("button", { type: "submit", form: "security-create-form", class: "btn btn-primary" }, ["Registrar incidente"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({
      title: "Nuevo incidente",
      body: form,
      footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]),
    });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());
      payload.existing_ids = data().records.map(function (r) { return r.id; });

      const response = await global.ArrisePortalApi.postJSON("/soluciones/security/api/crear/", payload);
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
      renderAlerts();
      global.ArriseModal.close();
      global.ArriseToast.success("Incidente " + response.result.record.id + " registrado.");
    });
  }

  // ---------------- Detail / assign / transition modal ----------------

  function openDetail(recordId) {
    const record = data().records.find(function (r) { return r.id === recordId; });
    if (!record) return;
    const { h } = global.ArriseDom;

    function buildBody() {
      const allowed = TRANSITIONS[record.status] || [];
      const transitionButtons = allowed.map(function (target) {
        return h(
          "button",
          { type: "button", class: "btn btn-secondary btn-sm", onClick: function () { transition(record, target); } },
          [(target === "in_progress" && TERMINAL.has(record.status) ? "Reabrir · " : "Mover a ") + STATUS_LABELS[target]]
        );
      });

      const assignSelect = h("select", { id: "security-assign-select", class: "select" },
        [h("option", { value: "" }, ["Selecciona un responsable…"])].concat(
          ASSIGNEES.map(function (e) {
            return h("option", { value: e.id, selected: e.id === record.assignee_id ? "selected" : null }, [e.name]);
          })
        ));
      const assignForm = h("form", { id: "security-assign-form", class: "field" }, [
        h("label", { class: "field-label", for: "security-assign-select" }, ["Responsable"]),
        assignSelect,
        h("div", { "data-assign-errors": "1" }, []),
        h("button", { type: "submit", class: "btn btn-secondary btn-sm", style: "margin-top: var(--space-2);" }, ["Guardar responsable"]),
      ]);

      const timeline = h("ul", { class: "timeline" }, record.history.slice().reverse().map(function (entry) {
        return h("li", { class: "timeline-item" }, [
          h("time", {}, [global.ArriseDom.formatDateTime(entry.at)]),
          h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
        ]);
      }));

      return h("div", { class: "stack" }, [
        h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
          h("div", {}, [h("dt", {}, ["Sede"]), h("dd", {}, [siteName(record.site)])]),
          h("div", {}, [h("dt", {}, ["Piso"]), h("dd", {}, [record.floor])]),
          h("div", {}, [h("dt", {}, ["Categoría"]), h("dd", {}, [CATEGORY_LABELS[record.category] || record.category])]),
          h("div", {}, [h("dt", {}, ["Severidad"]), h("dd", {}, [h("span", { class: "badge " + severityBadgeClass(record.severity) }, [SEVERITY_LABELS[record.severity]])])]),
          h("div", {}, [h("dt", {}, ["Estado"]), h("dd", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status]])])]),
          h("div", {}, [h("dt", {}, ["Última sincronización"]), h("dd", {}, [global.ArriseDom.formatDateTime(record.last_sync)])]),
        ]),
        h("p", {}, [record.description]),
        transitionButtons.length ? h("div", { class: "cluster" }, transitionButtons) : h("p", { class: "text-secondary" }, ["No hay transiciones disponibles desde este estado."]),
        h("hr"),
        assignForm,
        h("hr"),
        h("h3", {}, ["Historial"]),
        timeline,
      ]);
    }

    global.ArriseModal.open({ title: record.id + " — " + record.title, body: buildBody() });

    const assignForm = document.getElementById("security-assign-form");
    if (assignForm) {
      assignForm.addEventListener("submit", async function (evt) {
        evt.preventDefault();
        const assigneeId = document.getElementById("security-assign-select").value;
        const errBox = assignForm.querySelector("[data-assign-errors]");
        global.ArriseDom.clear(errBox);
        if (!assigneeId) {
          errBox.append(global.ArriseDom.h("p", { class: "field-error" }, ["Selecciona un responsable."]));
          return;
        }
        const response = await global.ArrisePortalApi.postJSON("/soluciones/security/api/asignar/", {
          id: record.id,
          current_status: record.status,
          assignee_id: assigneeId,
        });
        if (!response.ok) {
          Object.keys(response.errors || {}).forEach(function (f) {
            errBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[f]]));
          });
          return;
        }
        record.assignee_id = response.result.assignee_id;
        record.assignee_name = response.result.assignee_name;
        record.status = response.result.status;
        record.history.push(response.result.history_entry);
        global.ArrisePortal.saveState();
        global.ArriseModal.close();
        renderTable();
        renderKpis();
        renderAlerts();
        global.ArriseToast.success("Incidente asignado a " + record.assignee_name + ".");
      });
    }
  }

  async function transition(record, target) {
    const response = await global.ArrisePortalApi.postJSON("/soluciones/security/api/transicion/", {
      id: record.id,
      current_status: record.status,
      target_status: target,
    });
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo cambiar de estado.");
      return;
    }
    record.status = response.result.status;
    record.history.push(response.result.history_entry);
    addNotification(response.result.notify, record.id);
    global.ArrisePortal.saveState();
    global.ArriseModal.close();
    renderTable();
    renderKpis();
    renderAlerts();
    global.ArriseToast.success("Incidente actualizado a " + STATUS_LABELS[target] + ".");
  }

  function addNotification(body, recordId) {
    const state = global.ArrisePortal.state;
    state.core = state.core || {};
    state.core.notifications = state.core.notifications || [];
    state.core.notifications.unshift({
      id: "notif-" + Date.now(),
      title: "Actualización de incidente de seguridad",
      body: body,
      read: false,
      at: new Date().toISOString(),
      link: "/soluciones/security/",
    });
  }

  // ---------------- CSV export ----------------

  async function exportCsv() {
    const records = filteredRecords();
    if (!records.length) {
      global.ArriseToast.info("No hay incidentes para exportar con el filtro actual.");
      return;
    }
    const rows = records.map(function (r) {
      return {
        id: r.id,
        title: r.title,
        site: siteName(r.site),
        floor: r.floor,
        category: r.category,
        severity: r.severity,
        status: r.status,
        assignee_name: r.assignee_name || "Sin asignar",
        created_at: global.ArriseDom.formatDateTime(r.created_at),
        last_sync: global.ArriseDom.formatDateTime(r.last_sync),
      };
    });
    const csrfToken = global.ArrisePortalApi.readCookie("arrise_csrftoken") || "";
    let response;
    try {
      response = await fetch("/soluciones/security/api/exportar/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
        body: JSON.stringify({ rows: rows }),
      });
    } catch (networkError) {
      global.ArriseToast.danger("No se pudo contactar al servidor local.");
      return;
    }
    if (!response.ok) {
      let message = "No se pudo exportar el CSV.";
      try {
        const errJson = await response.json();
        message = Object.values(errJson.errors || {})[0] || message;
      } catch (parseError) { /* keep default message */ }
      global.ArriseToast.danger(message);
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "incidentes_seguridad.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    global.ArriseToast.success("CSV exportado.");
  }

  // ---------------- Floor controls table ----------------

  function matchesControlFilters(control) {
    const q = (document.querySelector('[data-security-control-filter="q"]').value || "").trim().toLowerCase();
    const site = document.querySelector('[data-security-control-filter="site"]').value;
    const floor = document.querySelector('[data-security-control-filter="floor"]').value;
    const controlType = document.querySelector('[data-security-control-filter="control_type"]').value;
    const status = document.querySelector('[data-security-control-filter="status"]').value;
    if (site && control.site !== site) return false;
    if (floor && control.floor !== floor) return false;
    if (controlType && control.control_type !== controlType) return false;
    if (status && control.status !== status) return false;
    if (q && control.label.toLowerCase().indexOf(q) === -1 && control.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  function renderControls() {
    const { h, clear, formatDate } = global.ArriseDom;
    const tbody = document.querySelector("[data-security-controls-body]");
    const empty = document.querySelector("[data-security-controls-empty]");
    if (!tbody) return;
    clear(tbody);
    const controls = data().controls.filter(matchesControlFilters).slice().sort(function (a, b) {
      return new Date(a.next_review) - new Date(b.next_review);
    });
    empty.hidden = controls.length !== 0;

    controls.forEach(function (control) {
      tbody.append(h("tr", {}, [
        h("td", { class: "mono" }, [control.id]),
        h("td", {}, [siteName(control.site)]),
        h("td", {}, [control.floor]),
        h("td", {}, [CONTROL_TYPE_LABELS[control.control_type] || control.control_type]),
        h("td", {}, [control.label]),
        h("td", {}, [h("span", { class: "badge " + (control.status === "vencido" ? "badge-danger" : "badge-success") }, [CONTROL_STATUS_LABELS[control.status] || control.status])]),
        h("td", {}, [formatDate(control.next_review)]),
        h("td", {}, [
          control.linked_incident_id
            ? h("a", { href: "#", onClick: function (evt) { evt.preventDefault(); openDetail(control.linked_incident_id); } }, [control.linked_incident_id])
            : "—",
        ]),
      ]));
    });
  }

  // ---------------- Trend tab ----------------

  let trendChart = null;

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

    const canvas = document.querySelector('[data-chart="trend"]');
    if (global.Chart && canvas && canvas.offsetParent !== null) {
      if (trendChart) trendChart.destroy();
      trendChart = new global.Chart(canvas, {
        type: "bar",
        data: {
          labels: series.map(function (m) { return m.month; }),
          datasets: [
            { label: "Resueltos", data: series.map(function (m) { return m.success; }), backgroundColor: "#0e9f6e", stack: "s" },
            { label: "Pendientes/fallidos", data: series.map(function (m) { return m.fail; }), backgroundColor: "#e02424", stack: "s" },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }

    const { h, clear } = global.ArriseDom;
    const tbody = document.querySelector("[data-security-monthly-body]");
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
  }

  function setTrendKpi(key, value) {
    const el = document.querySelector('[data-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function renderAll() {
    renderTable();
    renderControls();
    renderKpis();
    renderAlerts();
    renderAnalytics();
  }

  function init() {
    document.querySelectorAll("[data-security-new]").forEach(function (btn) {
      btn.addEventListener("click", openCreateForm);
    });
    document.querySelectorAll("[data-security-filter]").forEach(function (el) {
      el.addEventListener("input", renderTable);
      el.addEventListener("change", renderTable);
    });
    document.querySelectorAll("[data-security-control-filter]").forEach(function (el) {
      el.addEventListener("input", renderControls);
      el.addEventListener("change", renderControls);
    });
    const exportBtn = document.querySelector("[data-security-export]");
    if (exportBtn) exportBtn.addEventListener("click", exportCsv);

    const trendPanel = document.getElementById("panel-tendencia");
    if (trendPanel) trendPanel.addEventListener("arrise:tab-shown", renderAnalytics);

    renderAll();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
