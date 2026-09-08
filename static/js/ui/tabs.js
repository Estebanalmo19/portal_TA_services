/**
 * Simple ARIA tabs: a `[data-tabs]` container with `[role=tab]` triggers
 * (each with `data-tab-target="panel-id"`) and matching `[role=tabpanel]`
 * elements. Supports arrow-key navigation per WAI-ARIA tabs pattern.
 */
(function (global) {
  "use strict";

  function initGroup(group) {
    const tabs = Array.prototype.slice.call(group.querySelectorAll('[role="tab"]'));
    if (!tabs.length) return;

    function activate(tab, focus) {
      tabs.forEach(function (t) {
        const selected = t === tab;
        t.setAttribute("aria-selected", String(selected));
        t.tabIndex = selected ? 0 : -1;
        t.classList.toggle("is-active", selected);
        const panel = document.getElementById(t.getAttribute("data-tab-target"));
        if (panel) {
          panel.hidden = !selected;
          // Charts (Chart.js) initialized while their canvas is inside a
          // `hidden` (display:none) panel get stuck at a 0-size layout —
          // this lets a page's script lazily (re)create them only once the
          // panel is actually visible, instead of at DOMContentLoaded.
          if (selected) panel.dispatchEvent(new CustomEvent("arrise:tab-shown", { bubbles: true }));
        }
      });
      if (focus) tab.focus();
    }

    tabs.forEach(function (tab, index) {
      tab.addEventListener("click", function () { activate(tab, false); });
      tab.addEventListener("keydown", function (evt) {
        let targetIndex = null;
        if (evt.key === "ArrowRight") targetIndex = (index + 1) % tabs.length;
        if (evt.key === "ArrowLeft") targetIndex = (index - 1 + tabs.length) % tabs.length;
        if (evt.key === "Home") targetIndex = 0;
        if (evt.key === "End") targetIndex = tabs.length - 1;
        if (targetIndex !== null) {
          evt.preventDefault();
          activate(tabs[targetIndex], true);
        }
      });
    });

    const preselected = group.querySelector('[role="tab"][aria-selected="true"]') || tabs[0];
    activate(preselected, false);
  }

  function init(scope) {
    (scope || document).querySelectorAll("[data-tabs]").forEach(initGroup);
  }

  global.ArriseTabs = { init: init };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(document); });
  } else {
    init(document);
  }
})(window);
