/**
 * Agent TA floating chat panel. Conversation history lives in
 * `ArrisePortal.state.core.agent_ta.messages` so it survives navigation and
 * full page reloads within the tab (see state/bootstrap.js).
 */
(function (global) {
  "use strict";

  function panelState() {
    const state = global.ArrisePortal.state;
    state.core = state.core || {};
    state.core.agent_ta = state.core.agent_ta || { messages: [], suggested: [] };
    return state.core.agent_ta;
  }

  function renderMessages() {
    const { h, clear, formatDateTime } = global.ArriseDom;
    const container = document.querySelector("[data-agent-ta-messages]");
    if (!container) return;
    clear(container);
    const data = panelState();
    data.messages.forEach(function (msg, index) {
      const bubble = h(
        "div",
        {
          style:
            "max-width:88%; padding:10px 12px; border-radius:12px; font-size:var(--font-size-sm);" +
            (msg.role === "user"
              ? "align-self:flex-end; background:var(--color-primary); color:var(--color-text-on-primary);"
              : "align-self:flex-start; background:var(--color-surface-secondary); color:var(--color-text-primary);"),
        },
        [msg.text]
      );
      container.append(bubble);

      if (msg.role === "assistant" && msg.support_url) {
        container.append(
          h("a", { class: "btn btn-secondary btn-sm", style: "align-self:flex-start;", href: msg.support_url }, [
            "Abrir ticket en Solutions Support",
          ])
        );
      }

      if (msg.role === "assistant" && index > 0) {
        const row = h("div", { class: "cluster", style: "align-self:flex-start;" }, [
          h(
            "button",
            {
              type: "button",
              class: "btn btn-ghost btn-sm",
              "aria-pressed": String(msg.rating === "up"),
              "aria-label": "Respuesta útil",
              onClick: function () {
                msg.rating = msg.rating === "up" ? null : "up";
                global.ArrisePortal.saveState();
                renderMessages();
              },
            },
            [msg.rating === "up" ? "👍 Útil" : "👍"]
          ),
          h(
            "button",
            {
              type: "button",
              class: "btn btn-ghost btn-sm",
              "aria-pressed": String(msg.rating === "down"),
              "aria-label": "Respuesta no útil",
              onClick: function () {
                msg.rating = msg.rating === "down" ? null : "down";
                global.ArrisePortal.saveState();
                renderMessages();
              },
            },
            [msg.rating === "down" ? "👎 No útil" : "👎"]
          ),
        ]);
        container.append(row);
      }
    });
    container.scrollTop = container.scrollHeight;
  }

  function renderSuggested() {
    const { h, clear } = global.ArriseDom;
    const container = document.querySelector("[data-agent-ta-suggested]");
    if (!container) return;
    clear(container);
    const data = panelState();
    (data.suggested || []).forEach(function (question) {
      container.append(
        h(
          "button",
          {
            type: "button",
            class: "btn btn-secondary btn-sm",
            onClick: function () { sendMessage(question); },
          },
          [question]
        )
      );
    });
  }

  async function sendMessage(text) {
    const data = panelState();
    data.messages.push({ role: "user", text: text });
    global.ArrisePortal.saveState();
    renderMessages();

    const indicator = document.createElement("div");
    indicator.textContent = "Agent TA está escribiendo…";
    indicator.setAttribute("data-agent-ta-typing", "1");
    indicator.style.cssText = "align-self:flex-start; font-size:var(--font-size-xs); color:var(--color-text-tertiary-a11y);";
    document.querySelector("[data-agent-ta-messages]").appendChild(indicator);

    const response = await global.ArrisePortalApi.postJSON("/api/agent-ta/preguntar/", { message: text });

    indicator.remove();

    if (!response.ok) {
      data.messages.push({ role: "assistant", text: "No pude procesar tu pregunta. Intenta de nuevo." });
    } else {
      data.messages.push({
        role: "assistant",
        text: response.result.reply,
        support_url: response.result.support_url || null,
      });
      data.suggested = response.result.suggested || data.suggested;
    }
    global.ArrisePortal.saveState();
    renderMessages();
    renderSuggested();
  }

  function openPanel() {
    const panel = document.querySelector("[data-agent-ta-panel]");
    const fab = document.querySelector("[data-agent-ta-fab]");
    if (!panel) return;
    panel.hidden = false;
    fab.setAttribute("aria-expanded", "true");
    renderMessages();
    renderSuggested();
    const input = document.getElementById("agent-ta-input");
    if (input) input.focus();
  }

  function closePanel() {
    const panel = document.querySelector("[data-agent-ta-panel]");
    const fab = document.querySelector("[data-agent-ta-fab]");
    if (!panel) return;
    panel.hidden = true;
    fab.setAttribute("aria-expanded", "false");
    fab.focus();
  }

  function init() {
    const fab = document.querySelector("[data-agent-ta-fab]");
    const closeBtn = document.querySelector("[data-agent-ta-close]");
    const openTriggers = document.querySelectorAll("[data-agent-ta-open]");
    const form = document.querySelector("[data-agent-ta-form]");
    const newConvoBtn = document.querySelector("[data-agent-ta-new-conversation]");

    if (fab) fab.addEventListener("click", openPanel);
    openTriggers.forEach(function (btn) { btn.addEventListener("click", openPanel); });
    if (closeBtn) closeBtn.addEventListener("click", closePanel);

    document.addEventListener("keydown", function (evt) {
      const panel = document.querySelector("[data-agent-ta-panel]");
      if (evt.key === "Escape" && panel && !panel.hidden) closePanel();
    });

    if (form) {
      form.addEventListener("submit", function (evt) {
        evt.preventDefault();
        const input = document.getElementById("agent-ta-input");
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        sendMessage(text);
      });
    }

    if (newConvoBtn) {
      newConvoBtn.addEventListener("click", function () {
        const data = panelState();
        data.messages = data.messages.slice(0, 1);
        global.ArrisePortal.saveState();
        renderMessages();
      });
    }

    // `bootstrap.js`'s DOMContentLoaded listener runs before this one (it is
    // registered first, via an earlier <script> tag), so `ArrisePortal.state`
    // is already populated by the time this executes — render immediately
    // instead of waiting for an `arrise:state-ready` that already fired.
    renderMessages();
    renderSuggested();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
