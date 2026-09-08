/**
 * Client-side filtering for the catalog grid (area/status/text). Card data
 * is server-rendered from the same mock snapshot embedded on the page;
 * this only shows/hides — no re-fetch needed for a demo-sized 7-item list.
 */
(function () {
  "use strict";

  function relativeLabel(iso) {
    if (!iso) return "Sin datos";
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return iso;
    const diffMs = Date.now() - then;
    const days = Math.floor(diffMs / 86400000);
    if (days <= 0) return "Hoy";
    if (days === 1) return "Hace 1 día";
    if (days < 30) return "Hace " + days + " días";
    const months = Math.floor(days / 30);
    return "Hace " + months + (months === 1 ? " mes" : " meses");
  }

  function applyFilters() {
    const area = document.getElementById("catalog-filter-area").value;
    const status = document.getElementById("catalog-filter-status").value;
    const q = document.getElementById("catalog-filter-q").value.trim().toLowerCase();
    const cards = document.querySelectorAll("[data-catalog-card]");
    let visible = 0;
    cards.forEach(function (card) {
      const matchesArea = !area || card.dataset.area === area;
      const matchesStatus = !status || card.dataset.status === status;
      const matchesQuery = !q || card.dataset.name.indexOf(q) !== -1;
      const show = matchesArea && matchesStatus && matchesQuery;
      card.hidden = !show;
      if (show) visible += 1;
    });
    document.querySelector("[data-catalog-empty]").hidden = visible !== 0;
  }

  document.querySelectorAll("[data-catalog-filter]").forEach(function (el) {
    el.addEventListener("input", applyFilters);
    el.addEventListener("change", applyFilters);
  });

  document.querySelectorAll("[data-relative-time]").forEach(function (el) {
    el.textContent = relativeLabel(el.getAttribute("data-relative-time"));
  });
})();
