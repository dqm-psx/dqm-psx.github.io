"use strict";

// Ordinary page scrolling reveals the English cover; no scroll interception.
(() => {
  const intro = document.getElementById("cover-intro");
  const sticky = intro.querySelector(".cover-sticky");
  const english = document.getElementById("intro-english-cover");
  const caption = document.getElementById("cover-caption");
  const header = document.querySelector(".site-header");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let ready = false;
  let frame = null;
  let lastCaption = "";

  function render() {
    frame = null;
    if (!ready) return;
    const offset = header.getBoundingClientRect().height - intro.getBoundingClientRect().top;
    const distance = Math.max(1, intro.offsetHeight - sticky.offsetHeight);
    // Reduced motion keeps a single short opening panel and swaps without a fade.
    const progress = reducedMotion.matches
      ? Number(offset >= 64)
      : Math.max(0, Math.min(1, offset / distance));
    intro.style.setProperty("--cover-progress", progress.toFixed(4));
    const label = progress < 0.5 ? "Original Japanese release" : "English fan translation";
    if (label !== lastCaption) { caption.textContent = label; lastCaption = label; }
  }

  function schedule() {
    if (frame === null) frame = requestAnimationFrame(render);
  }

  function updateMotion() {
    intro.classList.toggle("is-enhanced", !reducedMotion.matches);
    schedule();
  }

  // Reserve the scroll space during initialization, before images finish loading.
  updateMotion();
  english.decode().then(() => {
    ready = true;
    schedule();
  }).catch(() => {
    // The Japanese cover and direct link still work if the English image fails.
    intro.classList.remove("is-enhanced");
  });
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  window.addEventListener("pageshow", schedule);
  reducedMotion.addEventListener("change", updateMotion);
  if ("ResizeObserver" in window) new ResizeObserver(schedule).observe(header);
})();
