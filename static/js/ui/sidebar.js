/**
 * Desktop sidebar collapse (persisted) + mobile off-canvas nav.
 */
(function (global) {
  "use strict";

  const COLLAPSE_KEY = "arrise_sidebar_collapsed";

  function init() {
    const shell = document.querySelector(".app-shell");
    if (!shell) return;

    let collapsed = "0";
    try {
      collapsed = global.localStorage.getItem(COLLAPSE_KEY) || "0";
    } catch (err) { /* ignore */ }
    if (collapsed === "1") shell.classList.add("is-sidebar-collapsed");

    const collapseBtn = document.querySelector("[data-sidebar-toggle]");
    if (collapseBtn) {
      collapseBtn.addEventListener("click", function () {
        const isCollapsed = shell.classList.toggle("is-sidebar-collapsed");
        try {
          global.localStorage.setItem(COLLAPSE_KEY, isCollapsed ? "1" : "0");
        } catch (err) { /* ignore */ }
        collapseBtn.setAttribute("aria-pressed", String(isCollapsed));
      });
    }

    const mobileToggle = document.querySelector("[data-mobile-nav-toggle]");
    const overlay = document.querySelector("[data-nav-overlay]");
    function closeMobileNav() {
      shell.classList.remove("is-mobile-nav-open");
      if (mobileToggle) mobileToggle.setAttribute("aria-expanded", "false");
    }
    if (mobileToggle) {
      mobileToggle.addEventListener("click", function () {
        const isOpen = shell.classList.toggle("is-mobile-nav-open");
        mobileToggle.setAttribute("aria-expanded", String(isOpen));
      });
    }
    if (overlay) overlay.addEventListener("click", closeMobileNav);
    document.addEventListener("keydown", function (evt) {
      if (evt.key === "Escape") closeMobileNav();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
