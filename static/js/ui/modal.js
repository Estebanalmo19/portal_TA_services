/**
 * Generic modal controller: focus management, Escape-to-close, focus
 * return to the trigger, and a single shared overlay element reused by
 * every module (`data-modal-root` in base.html).
 */
(function (global) {
  "use strict";

  let releaseFocusTrap = null;

  function root() {
    return document.querySelector("[data-modal-root]");
  }

  function open(options) {
    const overlay = root();
    if (!overlay) return;
    const { h, clear } = global.ArriseDom;

    clear(overlay);
    const modal = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-labelledby": "modal-title" }, [
      h("div", { class: "modal-header" }, [
        h("h2", { id: "modal-title" }, [options.title || ""]),
        h("button", {
          class: "modal-close",
          type: "button",
          "aria-label": "Cerrar",
          onClick: function () { close(); },
          html: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>',
        }, []),
      ]),
    ]);
    const body = h("div", { class: "modal-body" }, []);
    if (options.body) body.append(options.body);
    modal.append(body);
    if (options.footer) {
      const footer = h("div", { class: "modal-footer" }, []);
      footer.append(options.footer);
      modal.append(footer);
    }
    overlay.append(modal);
    overlay.hidden = false;

    function onKeydown(evt) {
      if (evt.key === "Escape") close();
    }
    overlay.addEventListener("keydown", onKeydown);
    overlay._onKeydown = onKeydown;

    function onOverlayClick(evt) {
      if (evt.target === overlay) close();
    }
    overlay.addEventListener("mousedown", onOverlayClick);
    overlay._onOverlayClick = onOverlayClick;

    releaseFocusTrap = global.ArriseFocusTrap.trap(modal);
  }

  function close() {
    const overlay = root();
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    if (overlay._onKeydown) overlay.removeEventListener("keydown", overlay._onKeydown);
    if (overlay._onOverlayClick) overlay.removeEventListener("mousedown", overlay._onOverlayClick);
    global.ArriseDom.clear(overlay);
    if (releaseFocusTrap) {
      releaseFocusTrap();
      releaseFocusTrap = null;
    }
  }

  global.ArriseModal = { open: open, close: close };
})(window);
