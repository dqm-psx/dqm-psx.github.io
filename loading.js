"use strict";

// Shared page loading indicator. Call finish = DqmLoading.begin(), then finish()
// when that task settles. Concurrent tasks cannot clear one another's cursor.
(() => {
  const active = new Set();
  const root = document.documentElement;
  const scriptBase = document.currentScript.src;
  const cursor = document.createElement("div");
  cursor.className = "dqm-loading-cursor";
  cursor.hidden = true;
  cursor.setAttribute("aria-hidden", "true");
  const sprite = document.createElement("img");
  sprite.src = new URL("assets/slime.gif", scriptBase).href;
  sprite.width = sprite.height = 32;
  sprite.alt = "";
  sprite.className = "pixel";
  cursor.append(sprite);
  document.body.append(cursor);

  const finePointer = window.matchMedia("(any-hover: hover) and (any-pointer: fine)");
  let pointer = null;
  function render() {
    const busy = active.size > 0;
    root.toggleAttribute("data-loading", busy);
    cursor.hidden = !busy || !pointer || !finePointer.matches || !sprite.complete || sprite.naturalWidth === 0;
    root.toggleAttribute("data-loading-pointer", !cursor.hidden);
    if (!cursor.hidden) {
      const x = Math.max(0, Math.min(pointer.x + 14, document.documentElement.clientWidth - 34));
      const y = Math.max(0, Math.min(pointer.y + 16, window.innerHeight - 34));
      cursor.style.transform = `translate(${x}px, ${y}px)`;
    }
  }
  function forgetPointer() { pointer = null; render(); }
  sprite.addEventListener("load", render);
  sprite.addEventListener("error", render);
  document.addEventListener("pointermove", event => {
    pointer = event.pointerType === "mouse" ? { x: event.clientX, y: event.clientY } : null;
    render();
  }, { passive: true });
  document.documentElement.addEventListener("pointerleave", forgetPointer);
  window.addEventListener("blur", forgetPointer);
  window.addEventListener("pagehide", forgetPointer);
  document.addEventListener("visibilitychange", () => { if (document.hidden) forgetPointer(); });
  finePointer.addEventListener("change", render);

  function begin() {
    const task = {};
    active.add(task);
    render();
    return () => { active.delete(task); render(); };
  }
  window.DqmLoading = Object.freeze({ begin });
  if (document.readyState !== "complete") {
    const finish = begin();
    window.addEventListener("load", finish, { once: true });
  }
})();
