/**
 * Topbar-wide interactions that don't belong to a single solution: global
 * search, the notifications panel, the profile menu, and "Restablecer
 * demo". Runs on every page (loaded from base.html).
 */
(function (global) {
  "use strict";

  function closeAllPanels(except) {
    document.querySelectorAll("[data-notifications-panel], [data-profile-panel], [data-global-search-results]").forEach(function (el) {
      if (el !== except) el.hidden = true;
    });
  }

  function initSearch() {
    const input = document.querySelector("[data-global-search]");
    const results = document.querySelector("[data-global-search-results]");
    if (!input || !results) return;
    let timer = null;

    input.addEventListener("input", function () {
      clearTimeout(timer);
      const query = input.value.trim();
      if (query.length < 2) {
        results.hidden = true;
        return;
      }
      timer = setTimeout(async function () {
        const response = await global.ArrisePortalApi.getJSON("/api/busqueda/?q=" + encodeURIComponent(query));
        const { h, clear } = global.ArriseDom;
        clear(results);
        const items = (response.ok && response.result.results) || [];
        if (!items.length) {
          results.append(h("div", { style: "padding: var(--space-3); color: var(--color-text-secondary);" }, ["Sin resultados."]));
        } else {
          items.forEach(function (item) {
            results.append(
              h("a", { href: item.url, style: "display:block; padding: var(--space-3); border-bottom:1px solid var(--color-border);" }, [
                h("div", { style: "font-weight:600;" }, [item.label]),
                h("div", { style: "font-size: var(--font-size-xs); color: var(--color-text-secondary);" }, [item.hint]),
              ])
            );
          });
        }
        results.hidden = false;
      }, 220);
    });

    document.addEventListener("click", function (evt) {
      if (!results.contains(evt.target) && evt.target !== input) results.hidden = true;
    });
  }

  function renderNotifications() {
    const panel = document.querySelector("[data-notifications-panel]");
    const dot = document.querySelector("[data-notifications-dot]");
    if (!panel) return;
    const { h, clear, formatDateTime } = global.ArriseDom;
    const state = global.ArrisePortal.state;
    const notifications = (state.core && state.core.notifications) || [];
    clear(panel);

    if (!notifications.length) {
      panel.append(h("div", { style: "padding: var(--space-4); color: var(--color-text-secondary);" }, ["Sin notificaciones."]));
    } else {
      notifications.forEach(function (n) {
        panel.append(
          h(
            "a",
            {
              href: n.link || "#",
              style:
                "display:block; padding: var(--space-3); border-bottom:1px solid var(--color-border);" +
                (n.read ? "" : " background: var(--color-primary-soft);"),
              onClick: function () {
                n.read = true;
                global.ArrisePortal.saveState();
              },
            },
            [
              h("div", { style: "font-weight:600; font-size: var(--font-size-sm);" }, [n.title]),
              h("div", { style: "font-size: var(--font-size-xs); color: var(--color-text-secondary);" }, [n.body]),
              h("time", { style: "font-size: var(--font-size-xs); color: var(--color-text-tertiary-a11y);" }, [formatDateTime(n.at)]),
            ]
          )
        );
      });
    }
    const unread = notifications.filter(function (n) { return !n.read; }).length;
    dot.hidden = unread === 0;
  }

  function initNotifications() {
    const toggle = document.querySelector("[data-notifications-toggle]");
    const panel = document.querySelector("[data-notifications-panel]");
    if (!toggle || !panel) return;
    toggle.addEventListener("click", function () {
      const willOpen = panel.hidden;
      closeAllPanels();
      panel.hidden = !willOpen;
      toggle.setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden) renderNotifications();
    });
  }

  function initProfileMenu() {
    const toggle = document.querySelector("[data-profile-toggle]");
    const panel = document.querySelector("[data-profile-panel]");
    const label = document.querySelector("[data-profile-label]");
    const resetBtn = document.querySelector("[data-reset-demo]");
    if (!toggle || !panel) return;

    toggle.addEventListener("click", function () {
      const willOpen = panel.hidden;
      closeAllPanels();
      panel.hidden = !willOpen;
      toggle.setAttribute("aria-expanded", String(!panel.hidden));
      if (!panel.hidden && label) {
        const profile = global.ArrisePortal.profile;
        const names = { manager: "Manager", solution_owner: "Solution Owner", analyst: "Analyst" };
        label.textContent = "Perfil: " + (profile ? names[profile.slug] || profile.slug : "sin elegir");
      }
    });

    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        const confirmed = global.confirm(
          "¿Restablecer la demo? Se borrarán los registros, comentarios, notificaciones y conversaciones de esta pestaña. Se conservará tu perfil y tema."
        );
        if (confirmed) global.ArrisePortal.resetDemo();
      });
    }
  }

  document.addEventListener("click", function (evt) {
    const insideAnyPanel = evt.target.closest(
      "[data-notifications-panel], [data-notifications-toggle], [data-profile-panel], [data-profile-toggle]"
    );
    if (!insideAnyPanel) closeAllPanels();
  });

  document.addEventListener("keydown", function (evt) {
    if (evt.key === "Escape") closeAllPanels();
  });

  function init() {
    initSearch();
    initNotifications();
    initProfileMenu();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
