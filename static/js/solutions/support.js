/**
 * Solutions Support: ticket table (+ "Mis tickets" / Manager scope toggle),
 * create modal (with a "Reportar un problema" prefill path), detail modal
 * (assign / comment / transition / confirm resolution / rate / reopen) and
 * an analytics tab. All rendering reads
 * `ArrisePortal.state.solutions.support` (see state/bootstrap.js) — nothing
 * here is rendered from server HTML beyond the very first paint.
 *
 * The `TRANSITIONS` map mirrors `solutions.services.support.GRAPH` for
 * optimistic UI only (disabling buttons the server would reject anyway);
 * Django revalidates every transition. Status graph, reminder:
 *   new -> assigned
 *   assigned -> in_progress, waiting_for_requester, resolved
 *   in_progress -> waiting_for_requester, resolved
 *   waiting_for_requester -> in_progress, resolved
 *   resolved -> closed (confirm resolution), in_progress (reopen, keeps history)
 *   closed -> (terminal)
 *
 * "Mis tickets" is simulated with a fixed CURRENT_USER_ID (the first demo
 * employee) since this MVP has no real login/session — see
 * docs/implementation-notes.md for the no-database/no-auth contract.
 */
(function (global) {
  "use strict";

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return null;
    try { return JSON.parse(node.textContent); } catch (e) { return null; }
  }

  const TICKET_TYPES = readJSON("support-ticket-types") || [];
  const IMPACTS = readJSON("support-impacts") || [];
  const PRIORITIES = readJSON("support-priorities") || [];
  const STATUSES = readJSON("support-statuses") || [];
  const AFFECTED_SOLUTIONS = readJSON("support-affected-solutions") || [];
  const SLA_HOURS_BY_PRIORITY = readJSON("support-sla-hours") || {};
  const EMPLOYEES = readJSON("support-employees") || [];
  const PREFILL = readJSON("support-prefill") || {};

  const STATUS_LABELS = STATUSES.reduce(function (acc, s) { acc[s.slug] = s.label; return acc; }, {});
  const PRIORITY_LABELS = PRIORITIES.reduce(function (acc, p) { acc[p.slug] = p.label; return acc; }, {});
  const TICKET_TYPE_LABELS = TICKET_TYPES.reduce(function (acc, t) { acc[t.slug] = t.label; return acc; }, {});
  const SOLUTION_NAME_BY_SLUG = AFFECTED_SOLUTIONS.reduce(function (acc, s) { acc[s.slug] = s.name; return acc; }, {});

  const OPEN_STATUSES = new Set(["new", "assigned", "in_progress", "waiting_for_requester"]);
  const TRANSITIONS = {
    new: ["assigned"],
    assigned: ["in_progress", "waiting_for_requester", "resolved"],
    in_progress: ["waiting_for_requester", "resolved"],
    waiting_for_requester: ["in_progress", "resolved"],
    resolved: ["closed", "in_progress"],
    closed: [],
  };

  // Simulated "current user" for the "Mis tickets" view — see module docblock.
  const CURRENT_USER_ID = EMPLOYEES.length ? EMPLOYEES[0].id : null;
  const CURRENT_USER_NAME = EMPLOYEES.length ? EMPLOYEES[0].name : "Colaborador Demo";
  let scope = "mine";

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    state.solutions.support = state.solutions.support || { records: [] };
    return state.solutions.support;
  }

  // ---------------- Demo SLA mirror (UX only; server is authoritative) ----

  function slaHoursFor(priority) {
    return SLA_HOURS_BY_PRIORITY[priority] || 48;
  }

  function isOverdue(record) {
    if (record.status === "resolved" || record.status === "closed") return false;
    const ageHours = (Date.now() - new Date(record.created_at).getTime()) / 3600000;
    return ageHours > slaHoursFor(record.priority);
  }

  function ageLabel(createdAt) {
    const days = Math.floor((Date.now() - new Date(createdAt).getTime()) / 86400000);
    if (days <= 0) return "Hoy";
    if (days === 1) return "1 día";
    return days + " días";
  }

  // Demo-only priority suggestion, mirrors
  // solutions.services.support.suggested_priority (see that docstring for
  // the "Guía de demostración" rationale). The server recomputes/validates
  // regardless; this is only used to hint the form before submit.
  const URGENCY_LEANING_TYPES = new Set(["problema_tecnico", "datos_incorrectos"]);
  const PRIORITY_OPTIONS_BY_IMPACT = {
    solo_yo: ["baja", "media"],
    mi_equipo: ["media", "alta"],
    bloquea_operacion: ["alta", "urgente"],
  };
  function suggestedPriority(impact, ticketType) {
    const pair = PRIORITY_OPTIONS_BY_IMPACT[impact] || ["media", "media"];
    return URGENCY_LEANING_TYPES.has(ticketType) ? pair[1] : pair[0];
  }

  // ---------------- Badges ----------------

  function statusBadgeClass(status) {
    if (status === "closed") return "badge-neutral";
    if (status === "resolved") return "badge-success";
    if (status === "waiting_for_requester") return "badge-warning";
    if (status === "in_progress") return "badge-info";
    return "badge-neutral";
  }

  function priorityBadgeClass(priority) {
    if (priority === "urgente") return "badge-danger";
    if (priority === "alta") return "badge-warning";
    if (priority === "media") return "badge-info";
    return "badge-neutral";
  }

  // ---------------- Table ----------------

  function matchesFilters(record) {
    if (scope === "mine" && record.requester_id !== CURRENT_USER_ID) return false;
    const q = (document.querySelector('[data-support-filter="q"]').value || "").trim().toLowerCase();
    const status = document.querySelector('[data-support-filter="status"]').value;
    const priority = document.querySelector('[data-support-filter="priority"]').value;
    const affected = document.querySelector('[data-support-filter="affected_solution"]').value;
    if (status && record.status !== status) return false;
    if (priority && record.priority !== priority) return false;
    if (affected && record.affected_solution !== affected) return false;
    if (q && record.subject.toLowerCase().indexOf(q) === -1 && record.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  const PRIORITY_RANK = { urgente: 0, alta: 1, media: 2, baja: 3 };

  function sortRecords(records) {
    const sortBy = document.querySelector("[data-support-sort]").value;
    const sorted = records.slice();
    if (sortBy === "oldest") {
      sorted.sort(function (a, b) { return new Date(a.created_at) - new Date(b.created_at); });
    } else if (sortBy === "priority") {
      sorted.sort(function (a, b) { return (PRIORITY_RANK[a.priority] ?? 9) - (PRIORITY_RANK[b.priority] ?? 9); });
    } else {
      sorted.sort(function (a, b) { return new Date(b.created_at) - new Date(a.created_at); });
    }
    return sorted;
  }

  function renderTable() {
    const { h, clear } = global.ArriseDom;
    const tbody = document.querySelector("[data-support-table-body]");
    const empty = document.querySelector("[data-support-empty]");
    if (!tbody) return;
    clear(tbody);
    const records = sortRecords(data().records.filter(matchesFilters));
    empty.hidden = records.length !== 0;

    records.forEach(function (record) {
      const overdue = isOverdue(record);
      const row = h(
        "tr",
        {
          class: "row-link", tabindex: "0", role: "button", "aria-label": "Ver detalle de " + record.id,
          onClick: function () { openDetail(record.id); },
          onKeydown: function (evt) { if (evt.key === "Enter") openDetail(record.id); },
        },
        [
          h("td", { class: "mono" }, [record.id]),
          h("td", {}, [record.subject]),
          h("td", {}, [SOLUTION_NAME_BY_SLUG[record.affected_solution] || record.affected_solution]),
          h("td", {}, [TICKET_TYPE_LABELS[record.ticket_type] || record.ticket_type]),
          h("td", {}, [h("span", { class: "badge " + priorityBadgeClass(record.priority) }, [PRIORITY_LABELS[record.priority] || record.priority])]),
          h("td", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status] || record.status])]),
          h("td", {}, [record.requester_name]),
          h("td", {}, [record.assignee_name || "Sin asignar"]),
          h("td", {}, [ageLabel(record.created_at), overdue ? h("span", { class: "badge badge-danger", style: "margin-left:6px;" }, ["Vencido"]) : null]),
        ]
      );
      tbody.append(row);
    });
  }

  function setScope(next) {
    scope = next;
    document.querySelectorAll("[data-support-scope]").forEach(function (btn) {
      const active = btn.getAttribute("data-support-scope") === next;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", String(active));
    });
    renderTable();
  }

  // ---------------- Create modal ----------------

  function openCreateForm(prefill) {
    prefill = prefill || {};
    const { h } = global.ArriseDom;

    const prioritySelect = h(
      "select",
      { id: "sf-priority", name: "priority", class: "select" },
      [h("option", { value: "" }, ["Automática (sugerida por el impacto)"])].concat(
        PRIORITIES.map(function (p) { return h("option", { value: p.slug }, [p.label]); })
      )
    );
    const priorityHint = h("p", { class: "text-secondary", "data-priority-hint": "1", style: "margin: 4px 0 0; font-size: var(--font-size-xs);" }, []);

    function updateHint() {
      const impact = form.querySelector("#sf-impact").value;
      const ticketType = form.querySelector("#sf-type").value;
      if (!impact) { priorityHint.textContent = ""; return; }
      const suggestion = suggestedPriority(impact, ticketType);
      priorityHint.textContent = "Sugerencia: " + (PRIORITY_LABELS[suggestion] || suggestion) + " (Guía de demostración). Puedes ajustarla.";
    }

    const originNote = prefill.origin
      ? h("p", { class: "text-secondary" }, ["Precargado automáticamente desde: " + prefill.origin + ". Revisa y ajusta antes de enviar."])
      : null;

    const form = h("form", { id: "support-create-form" }, [
      originNote,
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sf-solution" }, ["Solución afectada", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sf-solution", name: "affected_solution", class: "select", required: "required" },
            [h("option", { value: "" }, ["Selecciona una opción"])].concat(
              AFFECTED_SOLUTIONS.map(function (s) { return h("option", { value: s.slug, selected: s.slug === prefill.affected_solution ? "selected" : null }, [s.name]); })
            )),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sf-type" }, ["Tipo de ticket", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sf-type", name: "ticket_type", class: "select", required: "required", onChange: updateHint },
            [h("option", { value: "" }, ["Selecciona una opción"])].concat(
              TICKET_TYPES.map(function (t) { return h("option", { value: t.slug }, [t.label]); })
            )),
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "sf-subject" }, ["Asunto", h("span", { class: "required-mark" }, ["*"])]),
        h("input", { id: "sf-subject", name: "subject", class: "input", required: "required", maxlength: "160", value: prefill.subject || "" }),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "sf-description" }, ["Descripción", h("span", { class: "required-mark" }, ["*"])]),
        h("textarea", { id: "sf-description", name: "description", class: "textarea", required: "required", maxlength: "4000" }, [prefill.description || ""]),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sf-impact" }, ["Impacto", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sf-impact", name: "impact", class: "select", required: "required", onChange: updateHint },
            [h("option", { value: "" }, ["Selecciona una opción"])].concat(
              IMPACTS.map(function (i) { return h("option", { value: i.slug }, [i.label]); })
            )),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sf-priority" }, ["Prioridad sugerida"]),
          prioritySelect,
          priorityHint,
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "sf-repro" }, ["Pasos para reproducir (opcional)"]),
        h("textarea", { id: "sf-repro", name: "repro_steps", class: "textarea", maxlength: "2000" }, []),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sf-requester" }, ["Solicitante", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "sf-requester", name: "requester_id", class: "select", required: "required" },
            EMPLOYEES.map(function (e) { return h("option", { value: e.id, selected: e.id === CURRENT_USER_ID ? "selected" : null }, [e.name]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "sf-attachments" }, ["Adjuntos simulados (opcional)"]),
          h("input", { id: "sf-attachments", name: "attachments", class: "input", placeholder: "captura_demo.png, log_demo.txt" }),
        ]),
      ]),
      h("div", { "data-form-errors": "1" }, []),
    ]);

    const submitBtn = h("button", { type: "submit", form: "support-create-form", class: "btn btn-primary" }, ["Crear ticket"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({
      title: "Nuevo ticket",
      body: form,
      footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]),
    });
    updateHint();

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const formData = new FormData(form);
      const payload = Object.fromEntries(formData.entries());
      payload.attachments = (payload.attachments || "").split(",").map(function (s) { return s.trim(); }).filter(Boolean);
      payload.existing_ids = data().records.map(function (r) { return r.id; });

      const response = await global.ArrisePortalApi.postJSON("/soluciones/support/api/crear/", payload);
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
      renderAnalytics();
      global.ArriseModal.close();
      global.ArriseToast.success("Ticket " + response.result.record.id + " creado.");
      openDetail(response.result.record.id);
    });
  }

  // ---------------- Detail modal ----------------

  function openDetail(ticketId) {
    const record = data().records.find(function (r) { return r.id === ticketId; });
    if (!record) return;
    const { h } = global.ArriseDom;

    function buildBody() {
      const allowed = TRANSITIONS[record.status] || [];
      const transitionButtons = allowed.map(function (target) {
        let label = "Mover a " + STATUS_LABELS[target];
        if (record.status === "resolved" && target === "closed") label = "Confirmar resolución";
        if (record.status === "resolved" && target === "in_progress") label = "Reabrir ticket";
        return h("button", { type: "button", class: "btn btn-secondary btn-sm", onClick: function () { transition(record, target); } }, [label]);
      });

      const assignForm = record.status === "closed" ? null : h("form", { id: "support-assign-form", class: "field" }, [
        h("label", { class: "field-label", for: "support-assignee-select" }, [record.assignee_id ? "Reasignar a" : "Asignar a"]),
        h("div", { class: "cluster" }, [
          h("select", { id: "support-assignee-select", class: "select", style: "max-width:220px;" },
            EMPLOYEES.map(function (e) { return h("option", { value: e.id, selected: e.id === record.assignee_id ? "selected" : null }, [e.name]); })),
          h("button", { type: "submit", class: "btn btn-secondary btn-sm" }, ["Asignar"]),
        ]),
      ]);

      const ratingSection = (record.status === "resolved" || record.status === "closed")
        ? (record.rating
          ? h("p", {}, ["Valoración del solicitante: " + record.rating.score + "/5" + (record.rating.comment ? " — " + record.rating.comment : "")])
          : h("form", { id: "support-rate-form", class: "field" }, [
            h("label", { class: "field-label", for: "support-rate-score" }, ["Valorar la resolución"]),
            h("div", { class: "cluster" }, [
              h("select", { id: "support-rate-score", class: "select", style: "max-width:120px;" },
                [1, 2, 3, 4, 5].map(function (n) { return h("option", { value: String(n), selected: n === 5 ? "selected" : null }, [n + " / 5"]); })),
              h("input", { id: "support-rate-comment", class: "input", placeholder: "Comentario (opcional)" }),
              h("button", { type: "submit", class: "btn btn-secondary btn-sm" }, ["Enviar valoración"]),
            ]),
          ]))
        : null;

      const timeline = h("ul", { class: "timeline" }, record.history.slice().reverse().map(function (entry) {
        return h("li", { class: "timeline-item" }, [
          h("time", {}, [global.ArriseDom.formatDateTime(entry.at)]),
          h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
        ]);
      }));

      const noteForm = h("form", { id: "support-note-form", class: "field" }, [
        h("label", { class: "field-label", for: "support-note-input" }, ["Agregar comentario"]),
        h("textarea", { id: "support-note-input", class: "textarea", maxlength: "1000" }),
        h("div", { "data-note-errors": "1" }, []),
        h("button", { type: "submit", class: "btn btn-secondary btn-sm", style: "margin-top: var(--space-2);" }, ["Guardar comentario"]),
      ]);

      const overdue = isOverdue(record);
      return h("div", { class: "stack" }, [
        h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
          h("div", {}, [h("dt", {}, ["Solución afectada"]), h("dd", {}, [SOLUTION_NAME_BY_SLUG[record.affected_solution] || record.affected_solution])]),
          h("div", {}, [h("dt", {}, ["Tipo"]), h("dd", {}, [TICKET_TYPE_LABELS[record.ticket_type] || record.ticket_type])]),
          h("div", {}, [h("dt", {}, ["Solicitante"]), h("dd", {}, [record.requester_name])]),
          h("div", {}, [h("dt", {}, ["Responsable"]), h("dd", {}, [record.assignee_name || "Sin asignar"])]),
          h("div", {}, [h("dt", {}, ["Estado"]), h("dd", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status]])])]),
          h("div", {}, [h("dt", {}, ["Prioridad"]), h("dd", {}, [h("span", { class: "badge " + priorityBadgeClass(record.priority) }, [PRIORITY_LABELS[record.priority]])])]),
          h("div", {}, [h("dt", {}, ["Antigüedad"]), h("dd", {}, [ageLabel(record.created_at) + (overdue ? " — vencido (SLA demo " + slaHoursFor(record.priority) + "h)" : " — dentro del SLA demo (" + slaHoursFor(record.priority) + "h)")])]),
          h("div", {}, [h("dt", {}, ["Adjuntos"]), h("dd", {}, [record.attachments && record.attachments.length ? record.attachments.join(", ") + " (simulados)" : "Ninguno"])]),
        ]),
        h("p", {}, [record.description]),
        record.repro_steps ? h("p", { class: "text-secondary" }, ["Pasos para reproducir: " + record.repro_steps]) : null,
        h("hr"),
        transitionButtons.length ? h("div", { class: "cluster" }, transitionButtons) : h("p", { class: "text-secondary" }, ["Estado final: no admite más cambios."]),
        assignForm,
        ratingSection,
        h("hr"),
        h("h3", {}, ["Historial"]),
        timeline,
        h("hr"),
        noteForm,
      ]);
    }

    global.ArriseModal.open({ title: record.id + " — " + record.subject, body: buildBody() });

    const noteForm = document.getElementById("support-note-form");
    if (noteForm) {
      noteForm.addEventListener("submit", async function (evt) {
        evt.preventDefault();
        const note = document.getElementById("support-note-input").value;
        const response = await global.ArrisePortalApi.postJSON("/soluciones/support/api/nota/", { id: record.id, note: note, actor: CURRENT_USER_NAME });
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
        global.ArriseToast.success("Comentario guardado.");
        openDetail(record.id);
      });
    }

    const assignForm = document.getElementById("support-assign-form");
    if (assignForm) {
      assignForm.addEventListener("submit", async function (evt) {
        evt.preventDefault();
        const assigneeId = document.getElementById("support-assignee-select").value;
        const response = await global.ArrisePortalApi.postJSON("/soluciones/support/api/asignar/", {
          id: record.id, assignee_id: assigneeId, current_status: record.status, actor: CURRENT_USER_NAME,
        });
        if (!response.ok) {
          global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo asignar el ticket.");
          return;
        }
        record.assignee_id = response.result.assignee_id;
        record.assignee_name = response.result.assignee_name;
        record.status = response.result.status;
        record.history.push(response.result.history_entry);
        global.ArrisePortal.saveState();
        renderTable();
        global.ArriseToast.success("Ticket asignado a " + record.assignee_name + ".");
        openDetail(record.id);
      });
    }

    const rateForm = document.getElementById("support-rate-form");
    if (rateForm) {
      rateForm.addEventListener("submit", async function (evt) {
        evt.preventDefault();
        const score = document.getElementById("support-rate-score").value;
        const comment = document.getElementById("support-rate-comment").value;
        const response = await global.ArrisePortalApi.postJSON("/soluciones/support/api/valorar/", {
          id: record.id, score: score, comment: comment, current_status: record.status, actor: CURRENT_USER_NAME,
        });
        if (!response.ok) {
          global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo registrar la valoración.");
          return;
        }
        record.rating = response.result.rating;
        record.history.push(response.result.history_entry);
        global.ArrisePortal.saveState();
        renderKpis();
        global.ArriseToast.success("Valoración registrada.");
        openDetail(record.id);
      });
    }
  }

  async function transition(record, target) {
    const response = await global.ArrisePortalApi.postJSON("/soluciones/support/api/transicion/", {
      id: record.id,
      current_status: record.status,
      target_status: target,
      actor: CURRENT_USER_NAME,
    });
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo cambiar de estado.");
      return;
    }
    record.status = response.result.status;
    record.history.push(response.result.history_entry);
    addNotification(response.result.notify, record.id);
    global.ArrisePortal.saveState();
    renderTable();
    renderKpis();
    renderAnalytics();
    global.ArriseToast.success("Ticket actualizado a " + STATUS_LABELS[target] + ".");
    openDetail(record.id);
  }

  function addNotification(body, ticketId) {
    const state = global.ArrisePortal.state;
    state.core = state.core || {};
    state.core.notifications = state.core.notifications || [];
    state.core.notifications.unshift({
      id: "notif-" + Date.now(),
      title: "Actualización de ticket",
      body: body,
      read: false,
      at: new Date().toISOString(),
      link: "/soluciones/support/",
    });
  }

  // ---------------- KPIs + Analytics ----------------

  function setKpi(key, value) {
    const el = document.querySelector('[data-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function renderKpis() {
    const records = data().records;
    const total = records.length;
    const open = records.filter(function (r) { return OPEN_STATUSES.has(r.status); }).length;
    const waiting = records.filter(function (r) { return r.status === "waiting_for_requester"; }).length;
    const finished = records.filter(function (r) { return r.status === "resolved" || r.status === "closed"; }).length;
    const overdue = records.filter(isOverdue).length;

    setKpi("open", open);
    setKpi("waiting", waiting);
    setKpi("resolution-rate", total ? Math.round((finished / total) * 100) + "%" : "Sin datos");
    setKpi("overdue", overdue);
  }

  let solutionChart = null;
  let typeChart = null;
  let statusChart = null;
  const CHART_COLORS = ["#35106a", "#7f5af0", "#0e9f6e", "#2f6fd6", "#b7791f", "#c0392b", "#0e7490", "#6d28d9", "#a16207"];

  function renderAnalytics() {
    const records = data().records;

    const bySolution = {};
    records.forEach(function (r) { bySolution[r.affected_solution] = (bySolution[r.affected_solution] || 0) + 1; });
    const solutionLabels = Object.keys(bySolution);

    const byType = {};
    records.forEach(function (r) { byType[r.ticket_type] = (byType[r.ticket_type] || 0) + 1; });
    const typeLabels = Object.keys(byType);

    const statusOrder = STATUSES.map(function (s) { return s.slug; });
    const statusCounts = statusOrder.map(function (s) { return records.filter(function (r) { return r.status === s; }).length; });

    const solutionCanvas = document.querySelector('[data-chart="solution"]');
    if (global.Chart && solutionCanvas && solutionCanvas.offsetParent !== null) {
      if (solutionChart) solutionChart.destroy();
      solutionChart = new global.Chart(solutionCanvas, {
        type: "doughnut",
        data: {
          labels: solutionLabels.map(function (s) { return SOLUTION_NAME_BY_SLUG[s] || s; }),
          datasets: [{ data: solutionLabels.map(function (s) { return bySolution[s]; }), backgroundColor: CHART_COLORS }],
        },
        options: { responsive: true, maintainAspectRatio: false },
      });

      const typeCanvas = document.querySelector('[data-chart="type"]');
      if (typeChart) typeChart.destroy();
      typeChart = new global.Chart(typeCanvas, {
        type: "bar",
        data: {
          labels: typeLabels.map(function (t) { return TICKET_TYPE_LABELS[t] || t; }),
          datasets: [{ label: "Tickets", data: typeLabels.map(function (t) { return byType[t]; }), backgroundColor: "#7f5af0" }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });

      const statusCanvas = document.querySelector('[data-chart="status"]');
      if (statusChart) statusChart.destroy();
      statusChart = new global.Chart(statusCanvas, {
        type: "bar",
        data: {
          labels: statusOrder.map(function (s) { return STATUS_LABELS[s]; }),
          datasets: [{ label: "Tickets", data: statusCounts, backgroundColor: "#2f6fd6" }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });
    }
  }

  // ---------------- Init ----------------

  function init() {
    document.querySelectorAll("[data-support-new]").forEach(function (btn) {
      btn.addEventListener("click", function () { openCreateForm({}); });
    });
    const reportBtn = document.querySelector("[data-support-report]");
    if (reportBtn) {
      // Design decision: this page's own "Reportar un problema" opens the
      // create-ticket modal pre-filled for sol=portal instead of navigating
      // to /soluciones/support/?sol=portal (that would just reload this
      // same page) — see docs/implementation-notes.md write-up for this
      // module.
      reportBtn.addEventListener("click", function () {
        openCreateForm({ affected_solution: "portal", origin: "solutions_support" });
      });
    }
    document.querySelectorAll("[data-support-scope]").forEach(function (btn) {
      btn.addEventListener("click", function () { setScope(btn.getAttribute("data-support-scope")); });
    });
    document.querySelectorAll("[data-support-filter]").forEach(function (el) {
      el.addEventListener("input", renderTable);
      el.addEventListener("change", renderTable);
    });
    const sortSelect = document.querySelector("[data-support-sort]");
    if (sortSelect) sortSelect.addEventListener("change", renderTable);

    const analyticsPanel = document.getElementById("panel-analitica");
    if (analyticsPanel) {
      analyticsPanel.addEventListener("arrise:tab-shown", renderAnalytics);
    }

    setScope("mine");
    renderTable();
    renderKpis();
    renderAnalytics();

    if (PREFILL && PREFILL.active) {
      openCreateForm(PREFILL);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
