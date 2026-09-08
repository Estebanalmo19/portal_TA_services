/**
 * Toast notifications, announced to assistive tech via an aria-live region.
 */
(function (global) {
  "use strict";

  function region() {
    let el = document.querySelector(".toast-region");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast-region";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    return el;
  }

  function show(message, kind, timeoutMs) {
    kind = kind || "info";
    timeoutMs = timeoutMs === undefined ? 4500 : timeoutMs;
    const el = document.createElement("div");
    el.className = "toast toast-" + kind;
    el.textContent = message;
    region().appendChild(el);
    if (timeoutMs > 0) {
      setTimeout(function () {
        el.remove();
      }, timeoutMs);
    }
    return el;
  }

  global.ArriseToast = {
    success: function (msg) { return show(msg, "success"); },
    danger: function (msg) { return show(msg, "danger"); },
    info: function (msg) { return show(msg, "info"); },
  };
})(window);
