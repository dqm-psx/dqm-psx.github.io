"use strict";

// Keep anchor headings below the sticky navigation, including when it wraps.
(() => {
  const header = document.querySelector(".site-header");
  const updateHeaderHeight = () => document.documentElement.style.setProperty(
    "--site-header-height", `${header.getBoundingClientRect().height}px`
  );
  updateHeaderHeight();
  if ("ResizeObserver" in window) new ResizeObserver(updateHeaderHeight).observe(header);
  else window.addEventListener("resize", updateHeaderHeight);
})();

const scenes = window.DqmScreenshots;
(() => {
  if (!Array.isArray(scenes) || !scenes.length) return;
  const gallery = document.getElementById("screenshot-gallery");
  const featuredScreen = document.getElementById("featured-screen");
  const stage = document.getElementById("screenshot-stage");
  const loading = document.getElementById("screenshot-loading");
  const status = document.getElementById("screenshot-status");
  const selection = document.getElementById("scene-select");
  const pauseButton = document.getElementById("scene-pause");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let latestRequest = 0;
  let activeScene = 0;
  let requestedScene = 0;
  let userPaused = true;
  let hovered = gallery.matches(":hover");
  let focusHeld = gallery.contains(document.activeElement);
  let inView = !("IntersectionObserver" in window);
  let autoPending = false;
  let timer = null;

  scenes.forEach((scene, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${String(index + 1).padStart(2, "0")} / ${scenes.length} · ${scene.caption}`;
    selection.append(option);
  });

  function clearLoading() {
    stage.setAttribute("aria-busy", "false");
    loading.hidden = true;
  }

  function updatePauseButton() {
    const label = userPaused ? "Play slideshow" : "Pause slideshow";
    pauseButton.setAttribute("aria-label", label);
    pauseButton.title = label;
    pauseButton.classList.toggle("is-paused", userPaused);
  }

  function schedule() {
    clearTimeout(timer);
    if (userPaused || hovered || focusHeld || !inView || document.hidden) {
      // Pausing also cancels any automatic image still being decoded.
      if (autoPending) {
        ++latestRequest;
        autoPending = false;
        requestedScene = activeScene;
        clearLoading();
      }
      return;
    }
    timer = setTimeout(() => showScene((activeScene + 1) % scenes.length), 7000);
  }

  async function showScene(index, manual = false, initial = false) {
    clearTimeout(timer);
    const request = ++latestRequest;
    requestedScene = index;
    autoPending = !manual && !initial;
    clearLoading();
    status.textContent = "";
    status.classList.add("visually-hidden");
    const scene = scenes[index];
    if (manual) {
      userPaused = true;
      updatePauseButton();
    }
    stage.setAttribute("aria-busy", "true");
    loading.hidden = false;
    const alreadyDisplayed = featuredScreen.getAttribute("src") === scene.src;
    const nextImage = alreadyDisplayed ? featuredScreen : new Image();
    if (!alreadyDisplayed) nextImage.src = scene.src;
    try {
      await nextImage.decode();
      if (request !== latestRequest) return;
      if (!alreadyDisplayed) featuredScreen.src = scene.src;
      featuredScreen.alt = scene.alt;
      activeScene = index;
      document.getElementById("screen-credit").textContent = scene.credit ? `Screenshot by ${scene.credit}${scene.patchVersion ? ` (v${scene.patchVersion})` : ""}` : "From the English translation";
      selection.value = String(index);
      // Automatic rotation stays quiet for screen readers.
      if (manual) status.textContent = `Screenshot ${index + 1} of ${scenes.length}: ${scene.caption}`;
    } catch {
      if (request === latestRequest) {
        status.textContent = "That screenshot couldn’t load. Please try again or choose another image.";
        status.classList.remove("visually-hidden");
        selection.value = String(activeScene);
        requestedScene = activeScene;
        userPaused = true;
        updatePauseButton();
      }
    } finally {
      if (request === latestRequest) {
        autoPending = false;
        clearLoading();
        schedule();
      }
    }
  }

  document.getElementById("scene-previous").addEventListener("click", () => showScene((requestedScene - 1 + scenes.length) % scenes.length, true));
  document.getElementById("scene-next").addEventListener("click", () => showScene((requestedScene + 1) % scenes.length, true));
  let swipeStart = null;
  stage.addEventListener("pointerdown", event => {
    if (event.isPrimary && event.pointerType === "touch") {
      swipeStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
      stage.setPointerCapture(event.pointerId);
    }
  });
  stage.addEventListener("pointercancel", () => { swipeStart = null; });
  stage.addEventListener("pointerup", event => {
    if (swipeStart?.id !== event.pointerId) return;
    const dx = event.clientX - swipeStart.x;
    const dy = event.clientY - swipeStart.y;
    swipeStart = null;
    if (Math.abs(dx) >= 48 && Math.abs(dx) > 1.5 * Math.abs(dy)) {
      showScene((requestedScene + (dx < 0 ? 1 : -1) + scenes.length) % scenes.length, true);
    }
  });
  selection.addEventListener("change", () => showScene(Number(selection.value), true));
  pauseButton.addEventListener("click", () => {
    userPaused = !userPaused;
    // Let an explicit Play start while the pointer and focus are on this button.
    focusHeld = false;
    hovered = false;
    updatePauseButton();
    schedule();
  });
  gallery.addEventListener("mouseenter", () => { hovered = matchMedia("(hover: hover)").matches; schedule(); });
  gallery.addEventListener("mouseleave", () => { hovered = false; schedule(); });
  gallery.addEventListener("focusin", () => { focusHeld = true; schedule(); });
  gallery.addEventListener("focusout", event => {
    if (!gallery.contains(event.relatedTarget)) { focusHeld = false; schedule(); }
  });
  document.addEventListener("visibilitychange", schedule);
  reducedMotion.addEventListener("change", event => {
    if (event.matches) { userPaused = true; updatePauseButton(); schedule(); }
  });
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting;
      schedule();
    });
    observer.observe(gallery);
  }
  updatePauseButton();
  // The selected option is the visible caption; keep the static caption for no-JS.
  document.getElementById("screen-caption").hidden = true;
  document.getElementById("scene-controls").hidden = false;
  // Read the first scene's credit/version too, even when automatic rotation is paused.
  showScene(0, false, true);
})();

// Choose an initial layout once. Resizing preserves the player's choice.
const installation = document.getElementById("install");
if (window.matchMedia("(max-width: 850px)").matches) installation.open = false;

function openLinkedDetails(hash) {
  const target = document.getElementById(hash.slice(1));
  for (let details = target?.closest("details"); details; details = details.parentElement.closest("details")) {
    details.open = true;
  }
}
document.addEventListener("click", event => {
  const link = event.target.closest("a[href^='#']");
  if (link) openLinkedDetails(link.hash);
});
window.addEventListener("hashchange", () => openLinkedDetails(location.hash));
openLinkedDetails(location.hash);

// The full navigation remains visible when JavaScript is unavailable.
(() => {
  const nav = document.querySelector(".main-nav");
  const button = nav.querySelector(".nav-toggle");
  const links = document.getElementById("nav-links");
  const compact = window.matchMedia("(max-width: 768px)");

  function setOpen(open) {
    button.setAttribute("aria-expanded", String(open));
    links.hidden = compact.matches && !open;
    if (!open) nav.querySelector("details").open = false;
  }

  function setLayout() {
    button.hidden = !compact.matches;
    nav.closest(".site-header").classList.toggle("compact-nav", compact.matches);
    setOpen(false);
  }

  button.addEventListener("click", () => setOpen(links.hidden));
  nav.addEventListener("keydown", event => {
    if (event.key === "Escape" && compact.matches && !links.hidden) {
      setOpen(false);
      button.focus();
    }
  });
  links.addEventListener("click", event => {
    if (compact.matches && event.target.closest("a")) setOpen(false);
  });
  nav.addEventListener("focusout", event => {
    if (compact.matches && !nav.contains(event.relatedTarget)) setOpen(false);
  });
  document.addEventListener("click", event => {
    if (compact.matches && !nav.contains(event.target)) setOpen(false);
  });
  compact.addEventListener("change", setLayout);
  setLayout();
})();

// GIFs do not honor CSS animation controls; use their static first frames.
const motionButton = document.getElementById("motion-toggle");
const motionPreference = window.matchMedia("(prefers-reduced-motion: reduce)");
let storedMotion = null;
try { storedMotion = localStorage.getItem("dqm-motion"); } catch { /* Private browsing can restrict storage. */ }
let paused = storedMotion ? storedMotion === "paused" : motionPreference.matches;
function applyMotionPreference() {
  document.documentElement.dataset.motion = paused ? "paused" : "playing";
  document.querySelectorAll('img[src$=".gif"], img[data-animated-src]').forEach(img => {
    if (!img.dataset.animatedSrc) img.dataset.animatedSrc = img.getAttribute("src");
    img.src = paused ? img.dataset.animatedSrc.replace(/\.gif$/, "-still.png") : img.dataset.animatedSrc;
  });
  motionButton.textContent = paused ? "Play sprite animation" : "Pause sprite animation";
}
motionButton.hidden = false;
applyMotionPreference();
motionButton.addEventListener("click", () => {
  paused = !paused;
  storedMotion = paused ? "paused" : "playing";
  try { localStorage.setItem("dqm-motion", storedMotion); } catch { /* Keep the current session preference. */ }
  applyMotionPreference();
});
motionPreference.addEventListener("change", event => {
  if (!storedMotion) { paused = event.matches; applyMotionPreference(); }
});

// Hover opens the FAQ topics; native details also supports keyboard and touch.
(() => {
  const menu = document.getElementById("faq-dropdown");
  const trigger = menu.querySelector("summary");
  const hover = window.matchMedia("(hover: hover)");
  let openedByHover = false;
  menu.addEventListener("mouseenter", () => {
    if (hover.matches && !menu.open) { menu.open = true; openedByHover = true; }
  });
  trigger.addEventListener("click", event => {
    // A pointer click should not immediately undo the hover that preceded it.
    if (event.detail > 0 && menu.open && openedByHover) event.preventDefault();
    openedByHover = false;
  });
  menu.addEventListener("mouseleave", () => {
    if (!menu.contains(document.activeElement)) menu.open = false;
  });
  menu.addEventListener("focusout", event => {
    if (!menu.contains(event.relatedTarget) && !menu.matches(":hover")) menu.open = false;
  });
  menu.addEventListener("keydown", event => {
    if (event.key === "Escape" && menu.open) {
      menu.open = false;
      openedByHover = false;
      trigger.focus();
      event.preventDefault();
      event.stopPropagation();
    }
  });
  menu.querySelectorAll("a").forEach(link => link.addEventListener("click", () => { menu.open = false; }));
  document.addEventListener("click", event => {
    if (!menu.contains(event.target)) menu.open = false;
  });
})();

// The complete list remains scrollable without JavaScript. Rotation is optional.
(() => {
  const panel = document.getElementById("contributor-panel");
  const viewport = document.getElementById("contributors-viewport");
  const list = document.getElementById("contributor-list");
  const names = [...list.children];
  const controls = document.getElementById("contributor-controls");
  const previous = document.getElementById("contributors-prev");
  const next = document.getElementById("contributors-next");
  const pauseButton = document.getElementById("contributors-pause");
  const announcement = document.getElementById("contributor-announcement");
  const groupSize = 4;
  const groupCount = Math.ceil(names.length / groupSize);
  if (groupCount < 2) return;

  let group = 0;
  let userPaused = motionPreference.matches;
  let hovered = panel.matches(":hover");
  let focusHeld = panel.contains(document.activeElement);
  let inView = !("IntersectionObserver" in window);
  let timer = null;

  function schedule() {
    clearTimeout(timer);
    if (userPaused || hovered || focusHeld || !inView || document.hidden) return;
    timer = setTimeout(() => {
      group = (group + 1) % groupCount;
      render();
      schedule();
    }, 7000);
  }

  function updateControls() {
    const label = userPaused ? "Resume contributor rotation" : "Pause contributor rotation";
    pauseButton.setAttribute("aria-label", label);
    pauseButton.title = label;
    pauseButton.classList.toggle("is-paused", userPaused);
  }

  function render(manual = false) {
    const start = group * groupSize;
    names.forEach((name, index) => { name.hidden = index < start || index >= start + groupSize; });
    viewport.scrollTop = 0;
    updateControls();
    if (manual) announcement.textContent = names.slice(start, start + groupSize).map(name => name.textContent).join(", ");
  }

  function browse(delta) {
    userPaused = true;
    group = (group + delta + groupCount) % groupCount;
    render(true);
    schedule();
  }
  previous.addEventListener("click", () => browse(-1));
  next.addEventListener("click", () => browse(1));
  pauseButton.addEventListener("click", () => {
    userPaused = !userPaused;
    focusHeld = false;
    hovered = false;
    updateControls();
    schedule();
  });
  panel.addEventListener("mouseenter", () => { hovered = matchMedia("(hover: hover)").matches; schedule(); });
  panel.addEventListener("mouseleave", () => { hovered = false; schedule(); });
  panel.addEventListener("focusin", event => {
    focusHeld = true;
    if (event.target !== pauseButton) userPaused = true;
    updateControls();
    schedule();
  });
  panel.addEventListener("focusout", event => {
    if (!panel.contains(event.relatedTarget)) { focusHeld = false; schedule(); }
  });
  document.addEventListener("visibilitychange", schedule);
  motionPreference.addEventListener("change", event => {
    if (event.matches) { userPaused = true; updateControls(); schedule(); }
  });
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting;
      schedule();
    }).observe(panel);
  }
  render();
  controls.hidden = false;
  schedule();
})();

// Scroll affects only the English title overlay. The original print stays in place.
(() => {
  const intro = document.getElementById("cover-intro");
  const panel = intro.querySelector(".cover-sticky");
  const overlay = intro.querySelector(".cover-english");
  const header = document.querySelector(".site-header");
  const motion = matchMedia("(prefers-reduced-motion: reduce)");
  let frame = 0;

  function render() {
    frame = 0;
    const offset = header.getBoundingClientRect().bottom - intro.getBoundingClientRect().top;
    const distance = intro.offsetHeight - panel.offsetHeight;
    const progress = motion.matches || distance <= 1
      ? Number(offset >= 10)
      : Math.min(1, Math.max(0, offset / distance));
    intro.style.setProperty("--cover-progress", progress.toFixed(4));
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(render);
  }
  function resize() {
    intro.classList.toggle("is-enhanced", !motion.matches);
    schedule();
  }
  // Reserve the scroll distance before images have decoded, including on fragment visits.
  intro.classList.toggle("is-enhanced", !motion.matches);
  overlay.decode().then(() => {
    resize();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", resize);
    window.addEventListener("pageshow", schedule);
    motion.addEventListener("change", resize);
    if ("ResizeObserver" in window) {
      const observer = new ResizeObserver(schedule);
      observer.observe(header);
      observer.observe(panel);
    }
  }).catch(() => { intro.classList.remove("is-enhanced"); });
})();
