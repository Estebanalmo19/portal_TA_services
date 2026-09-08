/**
 * Light/dark theme toggle. The initial attribute is already set by an
 * inline snippet in <head> (before CSS/paint) to avoid a flash; this module
 * only wires up the visible toggle button afterwards.
 */
(function (global) {
  "use strict";

  const THEME_KEY = "arrise_theme";

  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") || "system";
  }

  function apply(theme) {
    if (theme === "system") {
      document.documentElement.removeAttribute("data-theme");
    } else {
      document.documentElement.setAttribute("data-theme", theme);
    }
    try {
      global.localStorage.setItem(THEME_KEY, theme);
    } catch (err) { /* ignore */ }
  }

  function effectiveTheme() {
    const explicit = document.documentElement.getAttribute("data-theme");
    if (explicit) return explicit;
    return global.matchMedia && global.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function init() {
    const toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) return;
    function sync() {
      const effective = effectiveTheme();
      toggle.setAttribute("aria-pressed", String(effective === "dark"));
      toggle.setAttribute("aria-label", effective === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro");
    }
    sync();
    toggle.addEventListener("click", function () {
      const next = effectiveTheme() === "dark" ? "light" : "dark";
      apply(next);
      sync();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
