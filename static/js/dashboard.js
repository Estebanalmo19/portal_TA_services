/**
 * Executive dashboard: filters submit as a normal GET (full page reload —
 * everything here is a read-only aggregate recomputed server-side from
 * mock_data, so there is no sessionStorage state to reconcile, unlike the
 * seven solution modules). This file only wires up auto-submit and renders
 * the Chart.js views from the JSON the server already filtered.
 */
(function (global) {
  "use strict";

  function readJSON(id) {
    const node = document.getElementById(id);
    if (!node) return [];
    try {
      return JSON.parse(node.textContent);
    } catch (e) {
      return [];
    }
  }

  function initAutoSubmit() {
    const form = document.getElementById("dashboard-filters");
    if (!form) return;
    form.querySelectorAll("select").forEach(function (el) {
      el.addEventListener("change", function () {
        form.submit();
      });
    });
  }

  const charts = {};

  function destroyIfExists(key) {
    if (charts[key]) {
      charts[key].destroy();
      charts[key] = null;
    }
  }

  function isVisible(el) {
    return !!el && el.offsetParent !== null;
  }

  function renderTrend() {
    const canvas = document.querySelector('[data-chart="trend"]');
    if (!global.Chart || !isVisible(canvas)) return;
    const months = readJSON("dashboard-trend");
    destroyIfExists("trend");
    charts.trend = new global.Chart(canvas, {
      type: "bar",
      data: {
        labels: months.map(function (m) { return m.month; }),
        datasets: [
          { label: "Éxito", data: months.map(function (m) { return m.success; }), backgroundColor: "#0e9f6e", stack: "s" },
          { label: "Fallo", data: months.map(function (m) { return m.fail; }), backgroundColor: "#c0392b", stack: "s" },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  function renderUsage() {
    const canvas = document.querySelector('[data-chart="usage"]');
    if (!global.Chart || !isVisible(canvas)) return;
    const rows = readJSON("dashboard-usage");
    destroyIfExists("usage");
    charts.usage = new global.Chart(canvas, {
      type: "bar",
      data: {
        labels: rows.map(function (r) { return r.name; }),
        datasets: [{ label: "Ejecuciones", data: rows.map(function (r) { return r.executions; }), backgroundColor: "#7f5af0" }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  function renderDoughnut(key, elementId, dataKey) {
    const canvas = document.querySelector('[data-chart="' + elementId + '"]');
    if (!global.Chart || !isVisible(canvas)) return;
    const rows = readJSON(dataKey);
    destroyIfExists(key);
    charts[key] = new global.Chart(canvas, {
      type: "doughnut",
      data: {
        labels: rows.map(function (r) { return r.name; }),
        datasets: [{ data: rows.map(function (r) { return r.count; }), backgroundColor: ["#35106a", "#7f5af0", "#0e9f6e", "#2f6fd6", "#b7791f"] }],
      },
      options: { responsive: true, maintainAspectRatio: false },
    });
  }

  function renderAll() {
    renderTrend();
    renderUsage();
    renderDoughnut("area", "area", "dashboard-users-area");
    renderDoughnut("country", "country", "dashboard-users-country");
  }

  function init() {
    initAutoSubmit();
    renderAll();
    document.querySelectorAll(".tab-panel").forEach(function (panel) {
      panel.addEventListener("arrise:tab-shown", renderAll);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
