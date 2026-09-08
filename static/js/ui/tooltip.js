/**
 * Accessible tooltip: any element with `data-tooltip="..."` gets a
 * describedby'd bubble shown on hover/focus and hidden on blur/mouseleave
 * or Escape. Used for the dashboard's KPI formula explanations.
 */
(function (global) {
  "use strict";

  let counter = 0;

  function attach(trigger) {
    if (trigger.dataset.tooltipReady) return;
    trigger.dataset.tooltipReady = "1";
    const text = trigger.getAttribute("data-tooltip");
    const id = "tooltip-" + (counter += 1);
    const bubble = document.createElement("span");
    bubble.className = "tooltip-bubble";
    bubble.id = id;
    bubble.setAttribute("role", "tooltip");
    bubble.hidden = true;
    bubble.textContent = text;

    trigger.classList.add("tooltip-trigger");
    trigger.setAttribute("aria-describedby", id);
    if (!trigger.hasAttribute("tabindex") && trigger.tagName !== "BUTTON" && trigger.tagName !== "A") {
      trigger.setAttribute("tabindex", "0");
    }
    trigger.appendChild(bubble);

    function show() { bubble.hidden = false; }
    function hide() { bubble.hidden = true; }

    trigger.addEventListener("mouseenter", show);
    trigger.addEventListener("mouseleave", hide);
    trigger.addEventListener("focus", show);
    trigger.addEventListener("blur", hide);
    trigger.addEventListener("keydown", function (evt) {
      if (evt.key === "Escape") hide();
    });
  }

  function init(scope) {
    (scope || document).querySelectorAll("[data-tooltip]").forEach(attach);
  }

  global.ArriseTooltip = { init: init };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(document); });
  } else {
    init(document);
  }
})(window);
