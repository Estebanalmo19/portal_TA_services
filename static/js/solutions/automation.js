/**
 * Automation Health Center: automation cards + global executions table +
 * detail modal (full execution history, retry) + trend tab. All rendering
 * reads `ArrisePortal.state.solutions.automation` so it reflects whatever
 * this tab has done so far (see state/bootstrap.js for how that state is
 * seeded/persisted).
 *
 * Retry rule and health formula mirror
 * `solutions.services.automation.retry_execution` / `recompute_health` —
 * see that module's docstrings for the exact, deterministic rule ("every
 * retry of a failed run is simulated as resolved, so it always succeeds").
 * Django is still the authority: the numbers below are only for optimistic
 * UI (labels/badges), never for deciding the retry outcome itself.
 */
(function (global) {
  "use strict";

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try { return JSON.parse(node.textContent); } catch (e) { return []; }
  }

  const HEALTH_STATUSES = readJSON("automation-health-statuses");
  const EXECUTION_STATUSES = readJSON("automation-execution-statuses");

  function toLabelMap(list) {
    return list.reduce(function (acc, item) { acc[item.slug] = item.label; return acc; }, {});
  }

  const HEALTH_LABELS = toLabelMap(HEALTH_STATUSES);
  const EXECUTION_STATUS_LABELS = toLabelMap(EXECUTION_STATUSES);

  function data() {
    const state = global.ArrisePortal.state;
    state.solutions = state.solutions || {};
    // Merge field-by-field (not `existing || defaults` on the whole
    // object): a tab whose sessionStorage was seeded before this module
    // existed (or before a field was added to initial_state()) would
    // otherwise keep a stale shape missing e.g. `executions` and crash
    // every renderer that reads it. See static/js/solutions/security.js's
    // data() for the same pattern with two top-level collections.
    const existing = state.solutions.automation || {};
    state.solutions.automation = {
      automations: existing.automations || [],
      executions: existing.executions || [],
      health_statuses: existing.health_statuses || HEALTH_STATUSES,
      execution_statuses: existing.execution_statuses || EXECUTION_STATUSES,
      monthly_series: existing.monthly_series || [],
      last_sync: existing.last_sync || null,
    };
    return state.solutions.automation;
  }

  function healthBadgeClass(health) {
    if (health === "good") return "badge-success";
    if (health === "warning") return "badge-warning";
    if (health === "critical") return "badge-danger";
    return "badge-neutral";
  }

  function statusBadgeClass(status) {
    return status === "success" ? "badge-success" : "badge-danger";
  }

  function findAutomation(id) {
    return data().automations.find(function (a) { return a.id === id; });
  }

  function executionsFor(automationId) {
    return data().executions
      .filter(function (e) { return e.automation_id === automationId; })
      .slice()
      .sort(function (a, b) { return new Date(b.started_at) - new Date(a.started_at); });
  }

  function formatDuration(seconds) {
    if (seconds === null || seconds === undefined) return "—";
    if (seconds < 60) return seconds + " s";
    const minutes = Math.floor(seconds / 60);
    const rest = seconds % 60;
    return minutes + " min" + (rest ? " " + rest + " s" : "");
  }

  function formatPercent(ratio) {
    if (ratio === null || ratio === undefined) return "Sin datos";
    return Math.round(ratio * 100) + "%";
  }

  // ---------------- KPIs / alerts ----------------

  function renderKpis() {
    const automations = data().automations;
    const total = automations.length;
    const active = automations.filter(function (a) { return !a.paused; }).length;
    const attention = automations.filter(function (a) { return a.health !== "good" || a.paused; }).length;
    const hours = automations.reduce(function (sum, a) { return sum + (a.hours_saved_per_week || 0); }, 0);

    setKpi("total", total);
    setKpi("active", active);
    setKpi("attention", attention);
    setKpi("hours", Math.round(hours * 10) / 10 + " h");

    const lastSyncEl = document.querySelector("[data-automation-last-sync]");
    if (lastSyncEl) lastSyncEl.textContent = global.ArriseDom.formatDateTime(data().last_sync);
  }

  function setKpi(key, value) {
    const el = document.querySelector('[data-automation-kpi="' + key + '"]');
    if (el) el.textContent = String(value);
  }

  function renderAlerts() {
    const { h, clear } = global.ArriseDom;
    const box = document.querySelector("[data-automation-alerts]");
    const list = document.querySelector("[data-automation-alerts-list]");
    if (!box || !list) return;
    clear(list);
    const flagged = data().automations.filter(function (a) { return a.health !== "good" || a.paused; });
    box.hidden = flagged.length === 0;
    flagged.forEach(function (a) {
      const reason = [];
      if (a.health !== "good") reason.push("salud " + (HEALTH_LABELS[a.health] || a.health).toLowerCase());
      if (a.paused) reason.push("pausada");
      list.append(h("li", {}, [
        h("a", { href: "#", onClick: function (evt) { evt.preventDefault(); openDetail(a.id); } }, [a.id + " — " + a.name]),
        " (" + reason.join(", ") + ")",
      ]));
    });
  }

  // ---------------- Automation cards ----------------

  function matchesFilters(automation) {
    const q = (document.querySelector('[data-automation-filter="q"]').value || "").trim().toLowerCase();
    const health = document.querySelector('[data-automation-filter="health"]').value;
    const paused = document.querySelector('[data-automation-filter="paused"]').value;
    if (health && automation.health !== health) return false;
    if (paused === "true" && !automation.paused) return false;
    if (paused === "false" && automation.paused) return false;
    if (q && automation.name.toLowerCase().indexOf(q) === -1 && automation.id.toLowerCase().indexOf(q) === -1) return false;
    return true;
  }

  function renderCards() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const container = document.querySelector("[data-automation-cards]");
    const empty = document.querySelector("[data-automation-empty]");
    if (!container) return;
    clear(container);
    const automations = data().automations.filter(matchesFilters);
    empty.hidden = automations.length !== 0;

    automations.forEach(function (a) {
      const card = h("div", { class: "card card-padded solution-card" }, [
        h("div", { class: "solution-card-top" }, [
          h("div", {}, [
            h("h3", {}, [a.name]),
            h("span", { class: "solution-card-area" }, [a.id]),
          ]),
          h("div", { class: "cluster", style: "gap: var(--space-1);" }, [
            h("span", { class: "badge " + healthBadgeClass(a.health) }, [HEALTH_LABELS[a.health] || a.health]),
            a.paused ? h("span", { class: "badge badge-neutral" }, ["Pausada"]) : null,
          ]),
        ]),
        h("p", { class: "solution-card-desc" }, [a.description]),
        h("dl", { class: "solution-card-meta" }, [
          h("div", {}, [h("dt", {}, ["Última ejecución"]), h("dd", {}, [formatDateTime(a.last_run_at)])]),
          h("div", {}, [h("dt", {}, ["Próxima ejecución"]), h("dd", {}, [a.paused ? "En pausa" : formatDateTime(a.next_run_at)])]),
          h("div", {}, [h("dt", {}, ["Tasa de éxito"]), h("dd", {}, [formatPercent(a.success_rate)])]),
          h("div", {}, [h("dt", {}, ["Registros (últ. corrida)"]), h("dd", {}, [String(a.records_processed_last_run)])]),
          h("div", {}, [h("dt", {}, ["Duración típica"]), h("dd", {}, [formatDuration(a.typical_duration_seconds)])]),
          h("div", {}, [h("dt", {}, ["Ahorro estimado"]), h("dd", {}, [a.hours_saved_per_week + " h/semana"])]),
        ]),
        h("div", { class: "solution-card-actions" }, [
          h("button", { type: "button", class: "btn btn-secondary btn-sm", onClick: function () { openDetail(a.id); } }, ["Ver historial"]),
          h("button", {
            type: "button",
            class: "btn " + (a.paused ? "btn-primary" : "btn-ghost") + " btn-sm",
            onClick: function () { togglePaused(a); },
          }, [a.paused ? "Reactivar" : "Pausar"]),
        ]),
      ]);
      container.append(card);
    });
  }

  // ---------------- Detail modal ----------------

  function openDetail(automationId) {
    const automation = findAutomation(automationId);
    if (!automation) return;
    const { h } = global.ArriseDom;

    function buildBody() {
      const runs = executionsFor(automationId);
      const timeline = h("ul", { class: "timeline" }, runs.map(function (run) {
        const detailParts = [
          h("span", { class: "badge " + statusBadgeClass(run.status) }, [EXECUTION_STATUS_LABELS[run.status] || run.status]),
          " " + run.id + " — " + String(run.records_processed) + " registros — " + formatDuration(run.duration_seconds),
        ];
        const extra = [];
        if (run.error) extra.push(h("p", { class: "text-secondary", style: "margin: 2px 0 0;" }, [run.error]));
        if (run.retry_of) extra.push(h("p", { class: "text-secondary", style: "margin: 2px 0 0;" }, ["Reintento de " + run.retry_of]));
        if (run.status === "failed") {
          extra.push(h("button", {
            type: "button",
            class: "btn btn-secondary btn-sm",
            style: "margin-top: var(--space-2);",
            onClick: function () { retryExecution(automation, run); },
          }, ["Reintentar"]));
        }
        return h("li", { class: "timeline-item" }, [
          h("time", {}, [global.ArriseDom.formatDateTime(run.started_at)]),
          h("p", { style: "margin: 2px 0 0;" }, detailParts),
        ].concat(extra));
      }));

      const dependencyList = h("ul", { style: "margin: 4px 0 0; padding-left: 1.1em;" },
        automation.dependencies.map(function (dep) { return h("li", {}, [dep]); }));

      const historyList = h("ul", { class: "timeline" }, automation.history.slice().reverse().map(function (entry) {
        return h("li", { class: "timeline-item" }, [
          h("time", {}, [global.ArriseDom.formatDateTime(entry.at)]),
          h("p", { style: "margin: 2px 0 0;" }, [entry.detail + " — " + entry.actor]),
        ]);
      }));

      return h("div", { class: "stack" }, [
        h("dl", { class: "solution-card-meta", style: "grid-template-columns: 1fr 1fr;" }, [
          h("div", {}, [h("dt", {}, ["Salud"]), h("dd", {}, [h("span", { class: "badge " + healthBadgeClass(automation.health) }, [HEALTH_LABELS[automation.health] || automation.health])])]),
          h("div", {}, [h("dt", {}, ["Estado"]), h("dd", {}, [automation.paused ? "Pausada" : "Activa"])]),
          h("div", {}, [h("dt", {}, ["Frecuencia"]), h("dd", {}, [automation.frequency_label])]),
          h("div", {}, [h("dt", {}, ["Tasa de éxito"]), h("dd", {}, [formatPercent(automation.success_rate)])]),
          h("div", {}, [h("dt", {}, ["Registros procesados (total)"]), h("dd", {}, [String(automation.records_processed_total)])]),
          h("div", {}, [h("dt", {}, ["Ahorro estimado"]), h("dd", {}, [automation.hours_saved_per_week + " h/semana"])]),
        ]),
        h("p", {}, [automation.description]),
        h("h3", { style: "margin-bottom: 2px;" }, ["Dependencias (simuladas)"]),
        dependencyList,
        h("hr"),
        h("div", { class: "cluster" }, [
          h("button", {
            type: "button",
            class: "btn " + (automation.paused ? "btn-primary" : "btn-ghost") + " btn-sm",
            onClick: function () { togglePaused(automation, true); },
          }, [automation.paused ? "Reactivar" : "Pausar"]),
        ]),
        h("hr"),
        h("h3", {}, ["Historial de ejecuciones"]),
        runs.length ? timeline : h("p", { class: "text-secondary" }, ["Sin ejecuciones registradas."]),
        h("hr"),
        h("h3", {}, ["Notas de la automatización"]),
        historyList,
      ]);
    }

    global.ArriseModal.open({ title: automation.id + " — " + automation.name, body: buildBody() });
  }

  // ---------------- Mutations ----------------

  async function retryExecution(automation, run) {
    const existingIds = data().executions.map(function (e) { return e.id; });
    const history = executionsFor(automation.id).slice().reverse(); // oldest first
    const recentStatuses = history.map(function (e) { return e.status; }).slice(-4);

    const response = await global.ArrisePortalApi.postJSON("/soluciones/automation/api/reintentar/", {
      automation_id: automation.id,
      execution_id: run.id,
      records_processed: run.records_processed,
      typical_duration_seconds: automation.typical_duration_seconds,
      existing_ids: existingIds,
      recent_statuses: recentStatuses,
    });
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo reintentar la ejecución.");
      return;
    }
    data().executions.push(response.result.execution);
    automation.health = response.result.health;
    automation.history.push(response.result.history_entry);
    global.ArrisePortal.saveState();
    renderCards();
    renderKpis();
    renderAlerts();
    renderRuns();
    global.ArriseModal.close();
    openDetail(automation.id);
    global.ArriseToast.success("Reintento " + response.result.execution.id + " completado con éxito.");
  }

  async function togglePaused(automation, reopenDetail) {
    const target = !automation.paused;
    const response = await global.ArrisePortalApi.postJSON("/soluciones/automation/api/pausar/", {
      automation_id: automation.id,
      paused: target,
      current_paused: automation.paused,
    });
    if (!response.ok) {
      global.ArriseToast.danger(Object.values(response.errors || {})[0] || "No se pudo actualizar la automatización.");
      return;
    }
    automation.paused = response.result.paused;
    automation.history.push(response.result.history_entry);
    global.ArrisePortal.saveState();
    renderCards();
    renderKpis();
    renderAlerts();
    if (reopenDetail) {
      global.ArriseModal.close();
      openDetail(automation.id);
    }
    global.ArriseToast.success(automation.paused ? "Automatización pausada." : "Automatización reactivada.");
  }

  // ---------------- Global executions table ----------------

  function populateRunAutomationFilter() {
    const select = document.querySelector('[data-run-filter="automation_id"]');
    if (!select || select.dataset.populated) return;
    const { h } = global.ArriseDom;
    data().automations.forEach(function (a) {
      select.append(h("option", { value: a.id }, [a.name]));
    });
    select.dataset.populated = "1";
  }

  function matchesRunFilters(run) {
    const automationId = document.querySelector('[data-run-filter="automation_id"]').value;
    const status = document.querySelector('[data-run-filter="status"]').value;
    if (automationId && run.automation_id !== automationId) return false;
    if (status && run.status !== status) return false;
    return true;
  }

  function renderRuns() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const tbody = document.querySelector("[data-run-table-body]");
    const empty = document.querySelector("[data-run-empty]");
    if (!tbody) return;
    clear(tbody);
    const runs = data().executions.filter(matchesRunFilters).slice().sort(function (a, b) {
      return new Date(b.started_at) - new Date(a.started_at);
    });
    empty.hidden = runs.length !== 0;

    runs.forEach(function (run) {
      const automation = findAutomation(run.automation_id);
      tbody.append(h("tr", {}, [
        h("td", { class: "mono" }, [run.id]),
        h("td", {}, [automation ? automation.name : run.automation_id]),
        h("td", {}, [formatDateTime(run.started_at)]),
        h("td", {}, [formatDuration(run.duration_seconds)]),
        h("td", {}, [h("span", { class: "badge " + statusBadgeClass(run.status) }, [EXECUTION_STATUS_LABELS[run.status] || run.status])]),
        h("td", {}, [String(run.records_processed)]),
        h("td", {}, [run.error || "—"]),
        h("td", {}, [
          run.status === "failed" && automation
            ? h("button", { type: "button", class: "btn btn-secondary btn-sm", onClick: function () { retryExecution(automation, run); } }, ["Reintentar"])
            : null,
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
            { label: "Éxito", data: series.map(function (m) { return m.success; }), backgroundColor: "#0e9f6e", stack: "s" },
            { label: "Fallidas", data: series.map(function (m) { return m.fail; }), backgroundColor: "#e02424", stack: "s" },
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
    const tbody = document.querySelector("[data-automation-monthly-body]");
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
    renderCards();
    renderKpis();
    renderAlerts();
    renderRuns();
    renderAnalytics();
  }

  function init() {
    populateRunAutomationFilter();

    document.querySelectorAll("[data-automation-filter]").forEach(function (el) {
      el.addEventListener("input", renderCards);
      el.addEventListener("change", renderCards);
    });
    document.querySelectorAll("[data-run-filter]").forEach(function (el) {
      el.addEventListener("change", renderRuns);
    });

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
