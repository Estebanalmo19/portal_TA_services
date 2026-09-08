/**
 * Small fetch() wrapper for the local, stateless JSON operation endpoints.
 * Every mutating call is a POST carrying the CSRF header Django expects
 * (see config.settings.CSRF_HEADER_NAME / CSRF_COOKIE_NAME).
 */
(function (global) {
  "use strict";

  function readCookie(name) {
    const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[2]) : null;
  }

  async function postJSON(url, payload) {
    const csrfToken = readCookie("arrise_csrftoken") || "";
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify(payload || {}),
      });
    } catch (networkError) {
      return { ok: false, errors: { __all__: "No se pudo contactar al servidor local." }, networkError: true };
    }
    let data;
    try {
      data = await response.json();
    } catch (parseError) {
      return { ok: false, errors: { __all__: "Respuesta inválida del servidor." } };
    }
    return data;
  }

  async function getJSON(url) {
    let response;
    try {
      response = await fetch(url, { credentials: "same-origin" });
    } catch (networkError) {
      return { ok: false, errors: { __all__: "No se pudo contactar al servidor local." }, networkError: true };
    }
    try {
      return await response.json();
    } catch (parseError) {
      return { ok: false, errors: { __all__: "Respuesta inválida del servidor." } };
    }
  }

  global.ArrisePortalApi = { postJSON: postJSON, getJSON: getJSON, readCookie: readCookie };
})(window);
