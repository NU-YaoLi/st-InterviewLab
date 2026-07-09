(function () {
  const COMPONENT_READY = "streamlit:componentReady";
  const SET_FRAME_HEIGHT = "streamlit:setFrameHeight";
  const SET_COMPONENT_VALUE = "streamlit:setComponentValue";
  const RENDER = "streamlit:render";

  const listeners = {};

  function addEventListener(type, callback) {
    if (!listeners[type]) {
      listeners[type] = [];
    }
    listeners[type].push(callback);
  }

  function dispatchEvent(type, event) {
    (listeners[type] || []).forEach((callback) => callback(event));
  }

  function sendMessage(payload) {
    window.parent.postMessage(
      Object.assign({ isStreamlitMessage: true }, payload),
      "*",
    );
  }

  window.Streamlit = {
    RENDER_EVENT: RENDER,
    events: { addEventListener, dispatchEvent },
    setComponentReady() {
      sendMessage({ type: COMPONENT_READY });
    },
    setFrameHeight(height) {
      sendMessage({ type: SET_FRAME_HEIGHT, height });
    },
    setComponentValue(value) {
      sendMessage({
        type: SET_COMPONENT_VALUE,
        value,
        dataType: "json",
      });
    },
  };

  window.addEventListener("message", (event) => {
    const data = event.data;
    if (!data || !data.isStreamlitMessage || data.type !== RENDER) {
      return;
    }
    dispatchEvent(RENDER, { detail: data });
  });
})();
