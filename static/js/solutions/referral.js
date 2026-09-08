/**
 * Referral Portal: table + detail/transition modal + create modal +
 * analytics tab. All rendering reads `ArrisePortal.state.solutions.referral`
 * so it reflects whatever this tab has done so far (see
 * state/bootstrap.js for how that state is seeded/persisted).
 *
 * The `TRANSITIONS` map below mirrors
 * `solutions.services.referral.TRANSITIONS` for optimistic UI only
 * (disabling buttons that the server would reject anyway) — Django is
 * still the authority and revalidates every transition server-side.
 */
(function (global) {
  "use strict";

  const STATUS_LABELS = readJSON("referral-statuses").reduce(function (acc, s) {
    acc[s.slug] = s.label;
    return acc;
  }, {});
  const JOB_OPENINGS = readJSON("referral-job-openings");
  const RELATIONS = readJSON("referral-relations");
  const COUNTRIES = readJSON("referral-countries");
  const EMPLOYEES = readJSON("referral-employees");
  const TERMINAL = new Set(["hired", "rejected"]);
  const TRANSITIONS = {
    submitted: ["under_review", "rejected"],
    under_review: ["recruiter_assigned", "rejected"],
    recruiter_assigned: ["interview", "rejected"],
    interview: ["hired", "rejected"],
    hired: [],
    rejected: [],
  };

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (e) { return []; }
  }

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    state.solutions.referral = state.solutions.referral || { records: [] };
    return state.solutions.referral;
  }

  function countryName(slug) {
    const c = COUNTRIES.find(function (x) { return x.slug === slug; });
    return c ? c.name : slug;
  }

  function statusBadgeClass(status) {
    if (status === "hired") return "badge-success";
    if (status === "rejected") return "badge-danger";
    if (status === "interview" || status === "recruiter_assigned") return "badge-info";
    return "badge-neutral";
  }

  // ---------------- Table ----------------

  function matchesFilters(record) {
    const q = (document.querySelector('[data-referral-filter="q"]').value || "").trim().toLowerCase();
    const status = document.querySelector('[data-referral-filter="status"]').value;
    const country = document.querySelector('[data-referral-filter="country"]').value;
    if (status && record.status !== status) return false;
    if (country && record.country !== country) return false;
    if (q && (record.candidate_name.toLowerCase().indexOf(q) === -1 && record.id.toLowerCase().indexOf(q) === -1)) return false;
    return true;
  }

  function renderTable() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const tbody = document.querySelector("[data-referral-table-body]");
    const empty = document.querySelector("[data-referral-empty]");
    if (!tbody) return;
    clear(tbody);
    const records = data().records.filter(matchesFilters).slice().sort(function (a, b) {
      return new Date(b.created_at) - new Date(a.created_at);
    });
    empty.hidden = records.length !== 0;

    records.forEach(function (record) {
      const lastEvent = record.history[record.history.length - 1];
      const row = h(
        "tr",
        { class: "row-link", tabindex: "0", role: "button", "aria-label": "Ver detalle de " + record.id,
          onClick: function () { openDetail(record.id); },
          onKeydown: function (evt) { if (evt.key === "Enter") openDetail(record.id); } },
        [
          h("td", { class: "mono" }, [record.id]),
          h("td", {}, [record.candidate_name]),
          h("td", {}, [record.vacancy_title]),
          h("td", {}, [countryName(record.country)]),
          h("td", {}, [record.referrer_name]),
          h("td", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status] || record.status])]),
          h("td", {}, [formatDateTime(lastEvent ? lastEvent.at : record.created_at)]),
        ]
      );
      tbody.append(row);
    });
  }

  // ---------------- Create modal ----------------

  function openCreateForm() {
    const { h } = global.ArriseDom;
    const form = h("form", { id: "referral-create-form" }, [
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "rf-candidate" }, ["Nombre del candidato", h("span", { class: "required-mark" }, ["*"])]),
        h("input", { id: "rf-candidate", name: "candidate_name", class: "input", required: "required", maxlength: "120" }),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "rf-vacancy" }, ["Vacante", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "rf-vacancy", name: "vacancy_id", class: "select", required: "required" },
            JOB_OPENINGS.map(function (j) { return h("option", { value: j.id }, [j.title]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "rf-country" }, ["País", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "rf-country", name: "country", class: "select", required: "required" },
            COUNTRIES.map(function (c) { return h("option", { value: c.slug }, [c.name]); })),
        ]),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "rf-referrer" }, ["Referente", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "rf-referrer", name: "referrer_id", class: "select", required: "required" },
            EMPLOYEES.map(function (e) { return h("option", { value: e.id }, [e.name]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "rf-relation" }, ["Relación con el candidato", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "rf-relation", name: "relation", class: "select", required: "required" },
            RELATIONS.map(function (r) { return h("option", { value: r.slug }, [r.label]); })),
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "rf-email" }, ["Correo del candidato (ejemplo)"]),
        h("input", { id: "rf-email", name: "candidate_email", class: "input", type: "email", placeholder: "candidato.demo@example.com" }),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "rf-cv" }, ["CV (simulado)"]),
        h("input", { id: "rf-cv", name: "cv_filename", class: "input", placeholder: "cv_candidato.pdf" }),
      ]),
      h("div", { "data-form-errors": "1" }, []),
    ]);

    const submitBtn = h("button", { type: "submit", form: "referral-create-form", class: "btn btn-primary" }, ["Registrar referido"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({
      title: "Nuevo referido",
      body: form,
      footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]),
    });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());
      payload.existing_ids = data().records.map(function (r) { return r.id; });

      const response = await global.ArrisePortalApi.postJSON("/soluciones/referral/api/crear/", payload);
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
      renderAnalytics();
      global.ArriseModal.close();
      global.ArriseToast.success("Referido " + response.result.record.id + " registrado.");
    });
  }

  // ---------------- Detail / transition modal ----------------

  function openDetail(recordId) {
    const record = data().records.find(function (r) { return r.id === recordId; });
    if (!record) return;
    const { h } = global.ArriseDom;

    function buildBody() {
      const allowed = TRANSITIONS[record.status] || [];
      const transitionButtons = allowed.map(function (target) {
        return h(
          "button",
          {
            type: "button",
            class: "btn btn-secondary btn-sm",
            onClick: function () { transition(record, target); },
          },
          ["Mover a " + STATUS_LABELS[target]]
        );
      });

      const timeline = h("ul", { class: "timeline" }, record.history.slice().reverse().map(function (entry) {
        return h("li", { class: "timeline-item" }, [
          h("time", {}, [global.ArriseDom.formatDateTime(entry.at)]),
          h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
        ]);
      }));

      const noteForm = h("form", { id: "referral-note-form", class: "field" }, [
        h("label", { class: "field-label", for: "referral-note-input" }, ["Agregar nota"]),
        h("textarea", { id: "referral-note-input", name: "note", class: "textarea", maxlength: "1000" }),
        h("div", { "data-note-errors": "1" }, []),
        h("button", { type: "submit", class: "btn btn-secondary btn-sm", style: "margin-top: var(--space-2);" }, ["Guardar nota"]),
      ]);

      return h("div", { class: "stack" }, [
        h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
          h("div", {}, [h("dt", {}, ["Vacante"]), h("dd", {}, [record.vacancy_title])]),
          h("div", {}, [h("dt", {}, ["País"]), h("dd", {}, [countryName(record.country)])]),
          h("div", {}, [h("dt", {}, ["Referente"]), h("dd", {}, [record.referrer_name])]),
          h("div", {}, [h("dt", {}, ["Correo candidato"]), h("dd", {}, [record.candidate_email])]),
          h("div", {}, [h("dt", {}, ["Etapa actual"]), h("dd", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status]])])]),
          h("div", {}, [h("dt", {}, ["CV"]), h("dd", {}, [record.cv_filename + " (simulado)"])]),
        ]),
        transitionButtons.length ? h("div", { class: "cluster" }, transitionButtons) : h("p", { class: "text-secondary" }, ["Etapa final: no admite más cambios."]),
        h("hr"),
        h("h3", {}, ["Historial"]),
        timeline,
        h("hr"),
        noteForm,
      ]);
    }

    global.ArriseModal.open({ title: record.id + " — " + record.candidate_name, body: buildBody() });

    const noteForm = document.getElementById("referral-note-form");
    if (noteForm) {
      noteForm.addEventListener("submit", async function (evt) {
        evt.preventDefault();
        const note = noteForm.querySelector("#referral-note-input").value;
        const response = await global.ArrisePortalApi.postJSON("/soluciones/referral/api/nota/", { id: record.id, note: note });
        const errBox = noteForm.querySelector("[data-note-errors]");
        global.ArriseDom.clear(errBox);
        if (!response.ok) {
          Object.keys(response.errors || {}).forEach(function (f) {
            errBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[f]]));
          });
          return;
        }
        record.notes.push(response.result.note);
        record.history.push(response.result.note);
        global.ArrisePortal.saveState();
        global.ArriseModal.close();
        renderTable();
        global.ArriseToast.success("Nota guardada.");
      });
    }
  }

  async function transition(record, target) {
    const response = await global.ArrisePortalApi.postJSON("/soluciones/referral/api/transicion/", {
      id: record.id,
      current_status: record.status,
      target_status: target,
    });
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo cambiar de etapa.");
      return;
    }
    record.status = response.result.status;
    record.history.push(response.result.history_entry);
    addNotification(response.result.notify, record.id);
    global.ArrisePortal.saveState();
    global.ArriseModal.close();
    renderTable();
    renderAnalytics();
    global.ArriseToast.success("Referido actualizado a " + STATUS_LABELS[target] + ".");
  }

  function addNotification(body, recordId) {
    const state = global.ArrisePortal.state;
    state.core = state.core || {};
    state.core.notifications = state.core.notifications || [];
    state.core.notifications.unshift({
      id: "notif-" + Date.now(),
      title: "Actualización de referido",
      body: body,
      read: false,
      at: new Date().toISOString(),
      link: "/soluciones/referral/",
    });
  }

  // ---------------- Analytics ----------------

  let funnelChart = null;
  let countryChart = null;

  function renderAnalytics() {
    const records = data().records;
    const total = records.length;
    const hired = records.filter(function (r) { return r.status === "hired"; }).length;
    const rejected = records.filter(function (r) { return r.status === "rejected"; }).length;
    const inProgress = total - hired - rejected;

    setKpi("total", total);
    setKpi("hire-rate", total ? Math.round((hired / total) * 100) + "%" : "Sin datos");
    setKpi("in-progress", inProgress);
    setKpi("rejected", rejected);

    const statusOrder = ["submitted", "under_review", "recruiter_assigned", "interview", "hired", "rejected"];
    const funnelCounts = statusOrder.map(function (s) { return records.filter(function (r) { return r.status === s; }).length; });

    const countryTotals = {};
    records.forEach(function (r) { countryTotals[r.country] = (countryTotals[r.country] || 0) + 1; });
    const countryLabels = Object.keys(countryTotals);

    const funnelCanvasVisible = document.querySelector('[data-chart="funnel"]');
    if (global.Chart && funnelCanvasVisible && funnelCanvasVisible.offsetParent !== null) {
      const funnelCanvas = funnelCanvasVisible;
      if (funnelChart) funnelChart.destroy();
      funnelChart = new global.Chart(funnelCanvas, {
        type: "bar",
        data: { labels: statusOrder.map(function (s) { return STATUS_LABELS[s]; }), datasets: [{ label: "Referidos", data: funnelCounts, backgroundColor: "#7f5af0" }] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });

      const countryCanvas = document.querySelector('[data-chart="country"]');
      if (countryChart) countryChart.destroy();
      countryChart = new global.Chart(countryCanvas, {
        type: "doughnut",
        data: { labels: countryLabels.map(countryName), datasets: [{ data: countryLabels.map(function (c) { return countryTotals[c]; }), backgroundColor: ["#35106a", "#7f5af0", "#0e9f6e", "#2f6fd6", "#b7791f"] }] },
        options: { responsive: true, maintainAspectRatio: false },
      });
    }

    const vacancyTotals = {};
    records.forEach(function (r) {
      vacancyTotals[r.vacancy_id] = vacancyTotals[r.vacancy_id] || { title: r.vacancy_title, country: r.country, count: 0 };
      vacancyTotals[r.vacancy_id].count += 1;
    });
    const ranked = Object.values(vacancyTotals).sort(function (a, b) { return b.count - a.count; }).slice(0, 8);
    const { h, clear } = global.ArriseDom;
    const tbody = document.querySelector("[data-referral-top-vacancies]");
    clear(tbody);
    ranked.forEach(function (v) {
      tbody.append(h("tr", {}, [h("td", {}, [v.title]), h("td", {}, [countryName(v.country)]), h("td", {}, [String(v.count)])]));
    });
  }

  function setKpi(key, value) {
    const el = document.querySelector('[data-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function init() {
    document.querySelectorAll("[data-referral-new]").forEach(function (btn) {
      btn.addEventListener("click", openCreateForm);
    });
    document.querySelectorAll('[data-referral-filter]').forEach(function (el) {
      el.addEventListener("input", renderTable);
      el.addEventListener("change", renderTable);
    });
    const analyticsPanel = document.getElementById("panel-analitica");
    if (analyticsPanel) {
      analyticsPanel.addEventListener("arrise:tab-shown", renderAnalytics);
    }

    renderTable();
    renderAnalytics();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
