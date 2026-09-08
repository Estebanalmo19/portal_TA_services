/**
 * Runs on every page, before any page-specific script. Decides which
 * dataset this tab uses (the persisted sessionStorage blob, or a fresh
 * server-rendered snapshot embedded in the current page) and exposes it as
 * `window.ArrisePortal`. See `state/storage.js` for the storage contract.
 */
(function (global) {
  "use strict";

  function readServerSnapshot() {
    const node = document.getElementById("arrise-initial-state");
    if (!node) return null;
    try {
      return JSON.parse(node.textContent);
    } catch (err) {
      console.error("[ArrisePortal] snapshot inicial del servidor inválido.", err);
      return null;
    }
  }

  function init() {
    const version = global.ARRISE_STATE_VERSION;
    const server = readServerSnapshot();
    const { state: sessionState, wasCorrupt, storageUnavailable } = global.ArrisePortalStorage.readRaw(version);

    let state = sessionState;
    let recovered = false;
    let usingSessionMemoryOnly = false;

    if (!state) {
      state = server || { version: version, generated_at: null, core: {}, solutions: {} };
      const wrote = global.ArrisePortalStorage.write(state);
      usingSessionMemoryOnly = !wrote;
      recovered = wasCorrupt;
    }

    const profile = global.ArrisePortalStorage.readProfile();

    global.ArrisePortal = {
      state: state,
      profile: profile,
      storageUnavailable: storageUnavailable || usingSessionMemoryOnly,
      saveState: function () {
        global.ArrisePortal.state.updated_at = new Date().toISOString();
        global.ArrisePortalStorage.write(global.ArrisePortal.state);
      },
      setProfile: function (slug) {
        global.ArrisePortalStorage.writeProfile(slug);
        global.ArrisePortal.profile = { slug: slug };
      },
      resetDemo: function () {
        global.ArrisePortalStorage.clearBusinessState(version);
        global.location.href = "/catalogo/";
      },
    };

    const path = global.location.pathname;
    const isWelcome = path === "/" || path === "";
    if (!profile && !isWelcome) {
      global.location.href = "/?next=" + encodeURIComponent(path);
      return;
    }

    document.dispatchEvent(new CustomEvent("arrise:state-ready", { detail: { recovered: recovered } }));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
