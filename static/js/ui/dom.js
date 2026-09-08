/**
 * Tiny DOM-building helper used by every solution's renderer.
 *
 * `h()` always sets user-provided text via `textContent`/`el.append(text)`,
 * never `innerHTML` — this is the main reason free-text fields coming back
 * from the server (referral notes, ticket descriptions, comments...) can't
 * turn into script injection: they are inserted as text nodes, never
 * parsed as markup.
 */
(function (global) {
  "use strict";

  function h(tag, attrs, children) {
    const el = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (key) {
      const value = attrs[key];
      if (value === null || value === undefined || value === false) return;
      if (key === "class") {
        el.className = value;
      } else if (key === "dataset") {
        Object.keys(value).forEach(function (dk) {
          el.dataset[dk] = value[dk];
        });
      } else if (key.indexOf("on") === 0 && typeof value === "function") {
        el.addEventListener(key.slice(2).toLowerCase(), value);
      } else if (key === "html") {
        // Explicit opt-in only, used for our own static SVG icon strings —
        // never for anything derived from user/server data.
        el.innerHTML = value;
      } else {
        el.setAttribute(key, value);
      }
    });
    (children || []).forEach(function (child) {
      if (child === null || child === undefined || child === false) return;
      if (typeof child === "string" || typeof child === "number") {
        el.append(String(child));
      } else {
        el.append(child);
      }
    });
    return el;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function formatDate(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "2-digit" });
    } catch (e) {
      return iso;
    }
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      return d.toLocaleString("es-CO", { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
    } catch (e) {
      return iso;
    }
  }

  global.ArriseDom = { h: h, clear: clear, formatDate: formatDate, formatDateTime: formatDateTime };
})(window);
