/**
 * HR Colombia Ticketing: table + kanban + detail/transition modal + create
 * modal (fields vary by category) + analytics tab. All rendering reads
 * `ArrisePortal.state.solutions.hr` so it reflects whatever this tab has
 * done so far (see state/bootstrap.js for how that state is seeded/persisted).
 *
 * The `TRANSITIONS` map below mirrors `solutions.services.hr.GRAPH`
 * (itself built from `mock_data.hr.TRANSITIONS`) for optimistic UI only
 * (disabling/hiding buttons the server would reject anyway) — Django is
 * still the authority and revalidates every transition server-side.
 *
 * Satisfaction survey: implemented as extra fields sent inside the same
 * "transicion" payload that moves a ticket to "resolved" (see
 * `transitionTicket()` below and `solutions.services.hr.transition_ticket`)
 * rather than a separate endpoint, since it only ever applies to that one
 * transition.
 */
(function (global) {
  "use strict";

  const STATUSES = readJSON("hr-statuses");
  const STATUS_LABELS = STATUSES.reduce(function (acc, s) { acc[s.slug] = s.label; return acc; }, {});
  const STATUS_SLUGS = STATUSES.map(function (s) { return s.slug; });
  const PRIORITIES = readJSON("hr-priorities");
  const PRIORITY_LABELS = PRIORITIES.reduce(function (acc, p) { acc[p.slug] = p.label; return acc; }, {});
  const CATEGORIES = readJSON("hr-categories");
  const CATEGORY_LABELS = CATEGORIES.reduce(function (acc, c) { acc[c.slug] = c.label; return acc; }, {});
  const CATEGORY_BY_SLUG = CATEGORIES.reduce(function (acc, c) { acc[c.slug] = c; return acc; }, {});
  const REQUESTERS = readJSON("hr-requesters");
  const AGENTS = readJSON("hr-agents");

  const OPEN_STATUSES = new Set(["new", "assigned", "in_progress", "waiting_for_employee"]);
  const TRANSITIONS = {
    new: ["assigned", "in_progress", "closed"],
    assigned: ["in_progress", "waiting_for_employee", "closed"],
    in_progress: ["waiting_for_employee", "resolved", "closed"],
    waiting_for_employee: ["in_progress", "resolved", "closed"],
    resolved: ["in_progress", "closed"],
    closed: [],
  };
  const DUE_SOON_MS = 24 * 60 * 60 * 1000;

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (e) { return []; }
  }

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    state.solutions.hr = state.solutions.hr || { records: [] };
    return state.solutions.hr;
  }

  function statusBadgeClass(status) {
    if (status === "resolved") return "badge-success";
    if (status === "waiting_for_employee") return "badge-warning";
    if (status === "assigned" || status === "in_progress") return "badge-info";
    return "badge-neutral";
  }

  function priorityBadgeClass(priority) {
    if (priority === "urgente") return "badge-danger";
    if (priority === "alta") return "badge-warning";
    if (priority === "media") return "badge-info";
    return "badge-neutral";
  }

  function isOverdue(record) {
    if (!OPEN_STATUSES.has(record.status) || !record.due_at) return false;
    return new Date(record.due_at).getTime() < Date.now();
  }

  function isDueSoon(record) {
    if (!OPEN_STATUSES.has(record.status) || !record.due_at) return false;
    const diff = new Date(record.due_at).getTime() - Date.now();
    return diff >= 0 && diff <= DUE_SOON_MS;
  }

  function slaBadge(record) {
    const { h, formatDateTime } = global.ArriseDom;
    if (!OPEN_STATUSES.has(record.status)) {
      return h("span", { class: "badge badge-neutral" }, ["N/A"]);
    }
    if (isOverdue(record)) {
      return h("span", { class: "badge badge-danger" }, ["Vencido · " + formatDateTime(record.due_at)]);
    }
    if (isDueSoon(record)) {
      return h("span", { class: "badge badge-warning" }, ["Vence pronto · " + formatDateTime(record.due_at)]);
    }
    return h("span", { class: "badge badge-neutral" }, ["Vence " + formatDateTime(record.due_at)]);
  }

  function requesterLabel(record) {
    return record.requester_name;
  }

  function assigneeLabel(record) {
    return record.assignee_name || "Sin asignar";
  }

  // ---------------- Filtering (shared by table + kanban) ----------------

  function matchesFilters(record) {
    const q = (document.querySelector('[data-hr-filter="q"]').value || "").trim().toLowerCase();
    const status = document.querySelector('[data-hr-filter="status"]').value;
    const category = document.querySelector('[data-hr-filter="category"]').value;
    const priority = document.querySelector('[data-hr-filter="priority"]').value;
    const onlyOverdue = document.querySelector('[data-hr-filter="overdue"]').checked;
    if (status && record.status !== status) return false;
    if (category && record.category !== category) return false;
    if (priority && record.priority !== priority) return false;
    if (onlyOverdue && !isOverdue(record)) return false;
    if (q && record.subject.toLowerCase().indexOf(q) === -1 && record.id.toLowerCase().indexOf(q) === -1 && record.requester_name.toLowerCase().indexOf(q) === -1) {
      return false;
    }
    return true;
  }

  function filteredRecords() {
    return data().records.filter(matchesFilters).slice().sort(function (a, b) {
      return new Date(b.created_at) - new Date(a.created_at);
    });
  }

  // ---------------- Table ----------------

  function renderTable() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const tbody = document.querySelector("[data-hr-table-body]");
    const empty = document.querySelector("[data-hr-empty]");
    if (!tbody) return;
    clear(tbody);
    const records = filteredRecords();
    empty.hidden = records.length !== 0;

    records.forEach(function (record) {
      const lastEvent = record.history[record.history.length - 1];
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
          h("td", {}, [requesterLabel(record)]),
          h("td", {}, [CATEGORY_LABELS[record.category] || record.category]),
          h("td", {}, [h("span", { class: "badge " + priorityBadgeClass(record.priority) }, [PRIORITY_LABELS[record.priority] || record.priority])]),
          h("td", {}, [assigneeLabel(record)]),
          h("td", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status] || record.status])]),
          h("td", {}, [slaBadge(record)]),
          h("td", {}, [formatDateTime(lastEvent ? lastEvent.at : record.created_at)]),
        ]
      );
      tbody.append(row);
    });
  }

  // ---------------- Kanban ----------------

  function renderKanban() {
    const { h, clear } = global.ArriseDom;
    const board = document.querySelector("[data-hr-kanban-board]");
    if (!board) return;
    clear(board);
    const records = filteredRecords();

    STATUS_SLUGS.forEach(function (status) {
      const columnRecords = records.filter(function (r) { return r.status === status; });
      const cards = columnRecords.map(function (record) {
        return h(
          "div",
          {
            class: "kanban-card", tabindex: "0", role: "button", "aria-label": "Ver detalle de " + record.id,
            onClick: function () { openDetail(record.id); },
            onKeydown: function (evt) { if (evt.key === "Enter") openDetail(record.id); },
          },
          [
            h("div", { class: "kanban-card-title" }, [record.id + " · " + record.subject]),
            h("div", { class: "text-secondary", style: "font-size: var(--font-size-xs);" }, [requesterLabel(record)]),
            h("div", { class: "cluster", style: "margin-top: var(--space-2); gap: var(--space-1);" }, [
              h("span", { class: "badge " + priorityBadgeClass(record.priority) }, [PRIORITY_LABELS[record.priority] || record.priority]),
              slaBadge(record),
            ]),
          ]
        );
      });
      board.append(
        h("div", { class: "kanban-column" }, [
          h("div", { class: "kanban-column-title" }, [STATUS_LABELS[status], h("span", {}, [String(columnRecords.length)])]),
          ...cards,
        ])
      );
    });
  }

  // ---------------- Create modal ----------------

  function buildExtraFieldInputs(container, categorySlug) {
    const { h, clear } = global.ArriseDom;
    clear(container);
    const category = CATEGORY_BY_SLUG[categorySlug];
    const specs = (category && category.extra_fields && category.extra_fields.length) ? category.extra_fields : [{ name: "detalle_adicional", label: "Detalle adicional", type: "text", required: false }];
    specs.forEach(function (spec) {
      container.append(
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "hr-extra-" + spec.name }, [
            spec.label,
            spec.required ? h("span", { class: "required-mark" }, ["*"]) : null,
          ]),
          h("input", {
            id: "hr-extra-" + spec.name,
            name: "extra:" + spec.name,
            class: "input",
            type: spec.type === "date" ? "date" : "text",
            required: spec.required ? "required" : null,
            maxlength: "200",
          }),
        ])
      );
    });
  }

  function openCreateForm() {
    const { h } = global.ArriseDom;

    const extraContainer = h("div", { "data-hr-extra-fields": "1" }, []);

    const categorySelect = h(
      "select",
      {
        id: "hr-category", name: "category", class: "select", required: "required",
        onChange: function () { buildExtraFieldInputs(extraContainer, categorySelect.value); },
      },
      CATEGORIES.map(function (c) { return h("option", { value: c.slug }, [c.label]); })
    );

    const form = h("form", { id: "hr-create-form" }, [
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "hr-requester" }, ["Solicitante", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "hr-requester", name: "requester_id", class: "select", required: "required" },
            REQUESTERS.map(function (e) { return h("option", { value: e.id }, [e.name]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "hr-category" }, ["Categoría", h("span", { class: "required-mark" }, ["*"])]),
          categorySelect,
        ]),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "hr-subject" }, ["Asunto", h("span", { class: "required-mark" }, ["*"])]),
        h("input", { id: "hr-subject", name: "subject", class: "input", required: "required", maxlength: "160" }),
      ]),
      h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "hr-description" }, ["Descripción", h("span", { class: "required-mark" }, ["*"])]),
        h("textarea", { id: "hr-description", name: "description", class: "textarea", required: "required", maxlength: "2000" }),
      ]),
      h("div", { class: "form-grid" }, [
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "hr-priority" }, ["Prioridad", h("span", { class: "required-mark" }, ["*"])]),
          h("select", { id: "hr-priority", name: "priority", class: "select", required: "required" },
            PRIORITIES.map(function (p) { return h("option", { value: p.slug }, [p.label + " (SLA demo: " + p.sla_hours + "h)"]); })),
        ]),
        h("div", { class: "field" }, [
          h("label", { class: "field-label", for: "hr-attachment" }, ["Adjunto (simulado)"]),
          h("input", { id: "hr-attachment", name: "attachment_filename", class: "input", placeholder: "captura_pantalla.png" }),
        ]),
      ]),
      extraContainer,
      h("div", { "data-form-errors": "1" }, []),
    ]);

    buildExtraFieldInputs(extraContainer, CATEGORIES[0] ? CATEGORIES[0].slug : "");

    const submitBtn = h("button", { type: "submit", form: "hr-create-form", class: "btn btn-primary" }, ["Crear ticket"]);
    const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onClick: function () { global.ArriseModal.close(); } }, ["Cancelar"]);

    global.ArriseModal.open({
      title: "Nuevo ticket",
      body: form,
      footer: h("div", { class: "cluster" }, [cancelBtn, submitBtn]),
    });

    form.addEventListener("submit", async function (evt) {
      evt.preventDefault();
      const formData = new FormData(form);
      const payload = { extra_fields: {} };
      formData.forEach(function (value, key) {
        if (key.indexOf("extra:") === 0) {
          payload.extra_fields[key.slice("extra:".length)] = value;
        } else {
          payload[key] = value;
        }
      });
      payload.existing_ids = data().records.map(function (r) { return r.id; });

      const response = await global.ArrisePortalApi.postJSON("/soluciones/hr/api/crear/", payload);
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
      renderKanban();
      renderAnalytics();
      global.ArriseModal.close();
      global.ArriseToast.success("Ticket " + response.result.record.id + " creado.");
    });
  }

  // ---------------- Detail / transition / assign / comment modal ----------------

  function extraFieldsSummary(record) {
    const { h } = global.ArriseDom;
    const category = CATEGORY_BY_SLUG[record.category];
    const specs = (category && category.extra_fields && category.extra_fields.length) ? category.extra_fields : [{ name: "detalle_adicional", label: "Detalle adicional" }];
    return specs
      .filter(function (spec) { return record.extra_fields && record.extra_fields[spec.name]; })
      .map(function (spec) {
        return h("div", {}, [h("dt", {}, [spec.label]), h("dd", {}, [record.extra_fields[spec.name]])]);
      });
  }

  function openDetail(recordId) {
    const record = data().records.find(function (r) { return r.id === recordId; });
    if (!record) return;
    const { h, formatDateTime } = global.ArriseDom;

    function buildBody() {
      const allowed = TRANSITIONS[record.status] || [];

      const assignSection = h("div", { class: "field" }, [
        h("label", { class: "field-label", for: "hr-assign-select" }, ["Responsable"]),
        h("div", { class: "cluster" }, [
          h("select", { id: "hr-assign-select", class: "select" },
            AGENTS.map(function (a) { return h("option", { value: a.id, selected: a.id === record.assignee_id ? "selected" : null }, [a.name]); })),
          h("button", {
            type: "button", class: "btn btn-secondary btn-sm",
            onClick: function () { assign(record, document.getElementById("hr-assign-select").value); },
          }, [record.assignee_id ? "Reasignar" : "Asignar"]),
        ]),
      ]);

      const transitionButtons = allowed.map(function (target) {
        return h(
          "button",
          { type: "button", class: "btn btn-secondary btn-sm", onClick: function () { handleTransitionClick(record, target); } },
          ["Mover a " + STATUS_LABELS[target]]
        );
      });

      const attachmentsList = (record.attachments || []).length
        ? h("ul", {}, record.attachments.map(function (a) { return h("li", {}, [a.filename + " (simulado, " + a.size_kb + " KB)"]); }))
        : h("p", { class: "text-secondary" }, ["Sin adjuntos."]);

      const surveyBlock = record.survey
        ? h("p", {}, ["Encuesta de satisfacción: " + record.survey.score + "/5" + (record.survey.comment ? " — " + record.survey.comment : "")])
        : null;

      const timeline = h("ul", { class: "timeline" }, record.history.slice().reverse().map(function (entry) {
        return h("li", { class: "timeline-item" }, [
          h("time", {}, [formatDateTime(entry.at)]),
          h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
        ]);
      }));

      const commentForm = h("form", { id: "hr-comment-form", class: "field" }, [
        h("label", { class: "field-label", for: "hr-comment-input" }, ["Agregar comentario"]),
        h("textarea", { id: "hr-comment-input", name: "comment", class: "textarea", maxlength: "1000" }),
        h("div", { "data-comment-errors": "1" }, []),
        h("button", { type: "submit", class: "btn btn-secondary btn-sm", style: "margin-top: var(--space-2);" }, ["Guardar comentario"]),
      ]);

      return h("div", { class: "stack" }, [
        h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
          h("div", {}, [h("dt", {}, ["Solicitante"]), h("dd", {}, [record.requester_name])]),
          h("div", {}, [h("dt", {}, ["Correo"]), h("dd", {}, [record.requester_email])]),
          h("div", {}, [h("dt", {}, ["Categoría"]), h("dd", {}, [CATEGORY_LABELS[record.category] || record.category])]),
          h("div", {}, [h("dt", {}, ["Prioridad"]), h("dd", {}, [h("span", { class: "badge " + priorityBadgeClass(record.priority) }, [PRIORITY_LABELS[record.priority]])])]),
          h("div", {}, [h("dt", {}, ["Estado"]), h("dd", {}, [h("span", { class: "badge " + statusBadgeClass(record.status) }, [STATUS_LABELS[record.status]])])]),
          h("div", {}, [h("dt", {}, ["SLA (guía de demostración)"]), h("dd", {}, [slaBadge(record)])]),
          h("div", {}, [h("dt", {}, ["Creado"]), h("dd", {}, [formatDateTime(record.created_at)])]),
          h("div", {}, [h("dt", {}, ["Resuelto"]), h("dd", {}, [record.resolved_at ? formatDateTime(record.resolved_at) : "—"])]),
          ...extraFieldsSummary(record),
        ]),
        h("h3", {}, ["Adjuntos"]),
        attachmentsList,
        surveyBlock,
        h("hr"),
        assignSection,
        transitionButtons.length ? h("div", { class: "cluster" }, transitionButtons) : h("p", { class: "text-secondary" }, ["Estado final: no admite más cambios."]),
        h("div", { "data-hr-survey-slot": "1" }, []),
        h("hr"),
        h("h3", {}, ["Historial"]),
        timeline,
        h("hr"),
        commentForm,
      ]);
    }

    global.ArriseModal.open({ title: record.id + " — " + record.subject, body: buildBody() });

    const commentForm = document.getElementById("hr-comment-form");
    if (commentForm) {
      commentForm.addEventListener("submit", async function (evt) {
        evt.preventDefault();
        const comment = commentForm.querySelector("#hr-comment-input").value;
        const response = await global.ArrisePortalApi.postJSON("/soluciones/hr/api/comentario/", { id: record.id, comment: comment });
        const errBox = commentForm.querySelector("[data-comment-errors]");
        global.ArriseDom.clear(errBox);
        if (!response.ok) {
          Object.keys(response.errors || {}).forEach(function (f) {
            errBox.append(global.ArriseDom.h("p", { class: "field-error" }, [response.errors[f]]));
          });
          return;
        }
        record.comments.push(response.result.comment);
        record.history.push(response.result.comment);
        global.ArrisePortal.saveState();
        global.ArriseModal.close();
        renderTable();
        global.ArriseToast.success("Comentario guardado.");
      });
    }
  }

  function handleTransitionClick(record, target) {
    if (target !== "resolved") {
      transition(record, target, null);
      return;
    }
    // Optional satisfaction survey shown only for the move-to-resolved
    // transition (see module docstring for why it rides the same request).
    const { h, clear } = global.ArriseDom;
    const slot = document.querySelector("[data-hr-survey-slot]");
    if (!slot) { transition(record, target, null); return; }
    clear(slot);
    const scoreSelect = h("select", { id: "hr-survey-score", class: "select" }, [
      h("option", { value: "" }, ["Sin encuesta"]),
      h("option", { value: "5" }, ["5 — Muy satisfecho"]),
      h("option", { value: "4" }, ["4 — Satisfecho"]),
      h("option", { value: "3" }, ["3 — Neutral"]),
      h("option", { value: "2" }, ["2 — Insatisfecho"]),
      h("option", { value: "1" }, ["1 — Muy insatisfecho"]),
    ]);
    const commentInput = h("input", { id: "hr-survey-comment", class: "input", placeholder: "Comentario opcional" });
    slot.append(
      h("div", { class: "card card-padded" }, [
        h("h3", {}, ["Encuesta de satisfacción (opcional)"]),
        h("div", { class: "field" }, [h("label", { class: "field-label", for: "hr-survey-score" }, ["Calificación"]), scoreSelect]),
        h("div", { class: "field" }, [h("label", { class: "field-label", for: "hr-survey-comment" }, ["Comentario"]), commentInput]),
        h("button", {
          type: "button", class: "btn btn-primary btn-sm",
          onClick: function () {
            const score = scoreSelect.value;
            const survey = score ? { score: Number(score), comment: commentInput.value } : null;
            transition(record, target, survey);
          },
        }, ["Confirmar resolución"]),
      ])
    );
  }

  async function transition(record, target, survey) {
    const payload = { id: record.id, current_status: record.status, target_status: target };
    if (survey) payload.survey = survey;
    const response = await global.ArrisePortalApi.postJSON("/soluciones/hr/api/transicion/", payload);
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo cambiar de estado.");
      return;
    }
    record.status = response.result.status;
    record.history.push(response.result.history_entry);
    if (Object.prototype.hasOwnProperty.call(response.result, "resolved_at")) record.resolved_at = response.result.resolved_at;
    if (Object.prototype.hasOwnProperty.call(response.result, "closed_at")) record.closed_at = response.result.closed_at;
    if (response.result.survey) record.survey = response.result.survey;
    addNotification(response.result.notify, record.id);
    global.ArrisePortal.saveState();
    global.ArriseModal.close();
    renderTable();
    renderKanban();
    renderAnalytics();
    global.ArriseToast.success("Ticket actualizado a " + STATUS_LABELS[target] + ".");
  }

  async function assign(record, assigneeId) {
    if (!assigneeId) return;
    const response = await global.ArrisePortalApi.postJSON("/soluciones/hr/api/asignar/", {
      id: record.id,
      current_status: record.status,
      assignee_id: assigneeId,
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
    global.ArriseModal.close();
    renderTable();
    renderKanban();
    renderAnalytics();
    global.ArriseToast.success("Ticket asignado a " + record.assignee_name + ".");
  }

  function addNotification(body, recordId) {
    const state = global.ArrisePortal.state;
    state.core = state.core || {};
    state.core.notifications = state.core.notifications || [];
    state.core.notifications.unshift({
      id: "notif-" + Date.now(),
      title: "Actualización de ticket HR",
      body: body,
      read: false,
      at: new Date().toISOString(),
      link: "/soluciones/hr/",
    });
  }

  // ---------------- Analytics ----------------

  let categoryChart = null;
  let statusChart = null;

  function averageResolutionHours(records) {
    const finished = records.filter(function (r) { return r.resolved_at || r.closed_at; });
    if (!finished.length) return null;
    const totalHours = finished.reduce(function (sum, r) {
      const end = new Date(r.resolved_at || r.closed_at).getTime();
      const start = new Date(r.created_at).getTime();
      return sum + Math.max(0, (end - start) / 3600000);
    }, 0);
    return totalHours / finished.length;
  }

  function formatHours(hours) {
    if (hours === null) return "Sin datos";
    if (hours < 48) return Math.round(hours) + " h";
    return Math.round(hours / 24) + " d";
  }

  function renderAnalytics() {
    const records = data().records;
    const total = records.length;
    const open = records.filter(function (r) { return OPEN_STATUSES.has(r.status); }).length;
    const overdue = records.filter(isOverdue).length;
    const dueSoon = records.filter(isDueSoon).length;
    const resolved = records.filter(function (r) { return r.status === "resolved"; }).length;
    const closed = records.filter(function (r) { return r.status === "closed"; }).length;
    const avgResolution = averageResolutionHours(records);
    const surveyed = records.filter(function (r) { return r.survey; });
    const avgSatisfaction = surveyed.length
      ? (surveyed.reduce(function (sum, r) { return sum + r.survey.score; }, 0) / surveyed.length).toFixed(1) + "/5"
      : "Sin datos";

    setKpi("total", total);
    setKpi("open", open);
    setKpi("overdue", overdue);
    setKpi("due-soon", dueSoon);
    setKpi("resolved", resolved);
    setKpi("closed", closed);
    setKpi("resolution-time", formatHours(avgResolution));
    setKpi("satisfaction", avgSatisfaction);

    const categoryTotals = {};
    records.forEach(function (r) { categoryTotals[r.category] = (categoryTotals[r.category] || 0) + 1; });
    const categorySlugs = Object.keys(CATEGORY_LABELS).filter(function (c) { return categoryTotals[c]; });

    const statusTotals = STATUS_SLUGS.map(function (s) { return records.filter(function (r) { return r.status === s; }).length; });

    const categoryCanvas = document.querySelector('[data-chart="category"]');
    if (global.Chart && categoryCanvas && categoryCanvas.offsetParent !== null) {
      if (categoryChart) categoryChart.destroy();
      categoryChart = new global.Chart(categoryCanvas, {
        type: "bar",
        data: {
          labels: categorySlugs.map(function (c) { return CATEGORY_LABELS[c]; }),
          datasets: [{ label: "Tickets", data: categorySlugs.map(function (c) { return categoryTotals[c]; }), backgroundColor: "#7f5af0" }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        },
      });

      const statusCanvas = document.querySelector('[data-chart="status"]');
      if (statusChart) statusChart.destroy();
      statusChart = new global.Chart(statusCanvas, {
        type: "doughnut",
        data: {
          labels: STATUS_SLUGS.map(function (s) { return STATUS_LABELS[s]; }),
          datasets: [{ data: statusTotals, backgroundColor: ["#94a3b8", "#2f6fd6", "#7f5af0", "#b7791f", "#0e9f6e", "#35106a"] }],
        },
        options: { responsive: true, maintainAspectRatio: false },
      });
    }
  }

  function setKpi(key, value) {
    const el = document.querySelector('[data-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function init() {
    document.querySelectorAll("[data-hr-new]").forEach(function (btn) {
      btn.addEventListener("click", openCreateForm);
    });
    document.querySelectorAll("[data-hr-filter]").forEach(function (el) {
      el.addEventListener("input", function () { renderTable(); renderKanban(); });
      el.addEventListener("change", function () { renderTable(); renderKanban(); });
    });
    const analyticsPanel = document.getElementById("panel-analitica");
    if (analyticsPanel) {
      analyticsPanel.addEventListener("arrise:tab-shown", renderAnalytics);
    }

    renderTable();
    renderKanban();
    renderAnalytics();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
