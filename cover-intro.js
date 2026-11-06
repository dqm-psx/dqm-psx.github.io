"use strict";

// Scroll changes only the transparent title layers. Artwork and paper stay fixed.
(() => {
  const intro = document.getElementById("cover-intro");
  const sticky = intro.querySelector(".cover-sticky");
  const titles = intro.querySelectorAll(".cover-title-layers img");
  const header = document.querySelector(".site-header");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let ready = false;
  let frame = null;

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
  Promise.all([...titles].map(image => image.decode())).then(() => {
    ready = true;
    schedule();
  }).catch(() => {
    // The Japanese title and direct link remain available if the English title fails.
    intro.classList.remove("is-enhanced");
  });
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule);
  window.addEventListener("pageshow", schedule);
  reducedMotion.addEventListener("change", updateMotion);
  if ("ResizeObserver" in window) new ResizeObserver(schedule).observe(header);
})();
