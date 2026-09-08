/**
 * Minimal focus trap for modals/panels: keeps Tab/Shift+Tab cycling inside
 * `container` and restores focus to whatever was focused before opening.
 */
(function (global) {
  "use strict";

  const FOCUSABLE = 'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

  function trap(container) {
    const previouslyFocused = document.activeElement;

    function focusables() {
      return Array.prototype.slice
        .call(container.querySelectorAll(FOCUSABLE))
        .filter(function (el) { return el.offsetParent !== null; });
    }

    function onKeydown(evt) {
      if (evt.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (evt.shiftKey && document.activeElement === first) {
        evt.preventDefault();
        last.focus();
      } else if (!evt.shiftKey && document.activeElement === last) {
        evt.preventDefault();
        first.focus();
      }
    }

    container.addEventListener("keydown", onKeydown);

    const initial = container.querySelector("[data-autofocus]") || focusables()[0];
    if (initial) initial.focus();

    return function release() {
      container.removeEventListener("keydown", onKeydown);
      if (previouslyFocused && typeof previouslyFocused.focus === "function") {
        previouslyFocused.focus();
      }
    };
  }

  global.ArriseFocusTrap = { trap: trap };
})(window);
