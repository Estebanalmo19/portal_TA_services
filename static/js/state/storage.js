/**
 * Tab-local state storage.
 *
 * Contract (see docs/implementation-notes.md "State contract"):
 * - `arrise_state_v<N>` in sessionStorage holds the *entire* mutable demo
 *   dataset for this browser tab (records, comments, chat, etc.). It is
 *   seeded once per tab from the server-rendered snapshot embedded on the
 *   very first page the tab visits, then every subsequent page reads and
 *   writes the same blob so edits made in one module are visible from
 *   another (and survive a full page reload/navigation).
 * - `arrise_profile` in sessionStorage holds only `{slug}` for the chosen
 *   demo profile. It is intentionally a *separate* key so "Restablecer
 *   demo" can wipe the big state blob while keeping the profile (and the
 *   visual prefs in localStorage) — see `resetState()`.
 * - A version mismatch or malformed blob is never fatal: we log it, tell
 *   the user, and reseed from the server snapshot for the current page.
 */
(function (global) {
  "use strict";

  const STATE_KEY_PREFIX = "arrise_state_v";
  const PROFILE_KEY = "arrise_profile";

  function stateKey(version) {
    return STATE_KEY_PREFIX + String(version);
  }

  function safeParse(raw) {
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch (err) {
      console.warn("[ArrisePortal] estado corrupto en sessionStorage, se descarta.", err);
      return null;
    }
  }

  function isValidShape(state, expectedVersion) {
    return (
      !!state &&
      typeof state === "object" &&
      state.version === expectedVersion &&
      typeof state.solutions === "object" &&
      typeof state.core === "object"
    );
  }

  /**
   * Load the current tab state, or null if absent/corrupt/stale.
   * `wasRecovered` on the returned info tells callers whether a bad blob
   * had to be discarded (used to show a one-time toast).
   */
  function readRaw(expectedVersion) {
    let raw = null;
    try {
      raw = global.sessionStorage.getItem(stateKey(expectedVersion));
    } catch (err) {
      return { state: null, wasCorrupt: false, storageUnavailable: true };
    }
    if (raw === null) {
      return { state: null, wasCorrupt: false, storageUnavailable: false };
    }
    const parsed = safeParse(raw);
    if (!isValidShape(parsed, expectedVersion)) {
      return { state: null, wasCorrupt: true, storageUnavailable: false };
    }
    return { state: parsed, wasCorrupt: false, storageUnavailable: false };
  }

  function write(state) {
    try {
      global.sessionStorage.setItem(stateKey(state.version), JSON.stringify(state));
      return true;
    } catch (err) {
      console.error("[ArrisePortal] no se pudo guardar el estado de la demo.", err);
      return false;
    }
  }

  function clearBusinessState(expectedVersion) {
    try {
      global.sessionStorage.removeItem(stateKey(expectedVersion));
    } catch (err) {
      /* storage unavailable: nothing to clear */
    }
  }

  function readProfile() {
    try {
      const raw = global.sessionStorage.getItem(PROFILE_KEY);
      const parsed = safeParse(raw);
      if (parsed && typeof parsed.slug === "string") return parsed;
    } catch (err) {
      /* ignore */
    }
    return null;
  }

  function writeProfile(slug) {
    try {
      global.sessionStorage.setItem(PROFILE_KEY, JSON.stringify({ slug: slug }));
      return true;
    } catch (err) {
      return false;
    }
  }

  global.ArrisePortalStorage = {
    stateKey: stateKey,
    readRaw: readRaw,
    write: write,
    clearBusinessState: clearBusinessState,
    readProfile: readProfile,
    writeProfile: writeProfile,
  };
})(window);
