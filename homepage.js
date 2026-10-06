"use strict";

const scenes = [
  { src: "assets/great-tree.png", alt: "A colorful scene from the world of Dragon Quest Monsters on PlayStation", caption: "A world beyond the Travelers’ Gates" },
  { src: "assets/adventure.png", alt: "The party exploring a room of treasure chests in the English translation", caption: "A new discovery around every corner" },
  { src: "assets/battle.png", alt: "An English-language monster battle in the PlayStation game", caption: "A little courage. A few good monsters." }
];
const featuredScreen = document.getElementById("featured-screen");
const screenshotStage = document.getElementById("screenshot-stage");
const screenshotLoading = document.getElementById("screenshot-loading");
const screenshotStatus = document.getElementById("screenshot-status");
const sceneButtons = [...document.querySelectorAll("[data-scene]")];
let latestSceneRequest = 0;
let activeScene = 0;
let finishSceneLoading = null;
function clearSceneLoading() {
  finishSceneLoading?.();
  finishSceneLoading = null;
  screenshotStage.setAttribute("aria-busy", "false");
  screenshotLoading.hidden = true;
  screenshotStatus.classList.remove("loading-announcement");
  sceneButtons.forEach(button => button.removeAttribute("data-loading"));
}
sceneButtons.forEach(button => {
  button.addEventListener("click", async () => {
    const index = Number(button.dataset.scene);
    const scene = scenes[index];
    const request = ++latestSceneRequest;
    clearSceneLoading();
    screenshotStatus.textContent = "";
    if (index === activeScene && featuredScreen.complete && featuredScreen.naturalWidth > 0) return;

    finishSceneLoading = window.DqmLoading.begin();
    screenshotStage.setAttribute("aria-busy", "true");
    screenshotLoading.hidden = false;
    button.setAttribute("data-loading", "");
    screenshotStatus.textContent = "Loading screenshot…";
    screenshotStatus.classList.add("loading-announcement");
    const nextImage = new Image();
    nextImage.src = scene.src;
    try {
      await nextImage.decode();
      if (request !== latestSceneRequest) return;
      featuredScreen.src = scene.src;
      featuredScreen.alt = scene.alt;
      activeScene = index;
      document.getElementById("screen-caption").textContent = scene.caption;
      document.getElementById("screen-number").textContent = `0${index + 1} / 03`;
      sceneButtons.forEach(item => item.setAttribute("aria-pressed", String(item === button)));
      screenshotStatus.textContent = "";
    } catch {
      if (request === latestSceneRequest) screenshotStatus.textContent = "That screenshot couldn’t load. Please try again.";
    } finally {
      if (request === latestSceneRequest) clearSceneLoading();
    }
  });
});

const copyButton = document.getElementById("copy-report");
copyButton.hidden = false;
copyButton.addEventListener("click", async () => {
  const template = document.getElementById("report-text").textContent.trim();
  const status = document.getElementById("copy-status");
  try {
    if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(template);
    status.textContent = "Copied. Fill it in and share it on Discord.";
  } catch {
    document.getElementById("report-template").open = true;
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(document.getElementById("report-text"));
    selection.removeAllRanges();
    selection.addRange(range);
    status.textContent = "Select and copy the template below.";
  }
});

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

// The committed list remains complete and scrollable without JavaScript.
// Enhance it into four-name groups without changing the panel's height.
(() => {
  const panel = document.getElementById("contributor-panel");
  const viewport = document.getElementById("contributors-viewport");
  const list = document.getElementById("contributor-list");
  const names = [...list.children];
  const controls = document.getElementById("contributor-controls");
  const previous = document.getElementById("contributors-prev");
  const next = document.getElementById("contributors-next");
  const pauseButton = document.getElementById("contributors-pause");
  const allButton = document.getElementById("contributors-all");
  const position = document.getElementById("contributor-position");
  const announcement = document.getElementById("contributor-announcement");
  const groupSize = 4;
  const groupCount = Math.ceil(names.length / groupSize);
  if (groupCount < 2) return;

  let group = 0;
  let showAll = false;
  let userPaused = motionPreference.matches;
  let hovered = panel.matches(":hover");
  let focusHeld = panel.contains(document.activeElement);
  let inView = !("IntersectionObserver" in window);
  let timer = null;

  function schedule() {
    clearTimeout(timer);
    timer = null;
    if (userPaused || showAll || hovered || focusHeld || !inView || document.hidden) return;
    timer = setTimeout(() => {
      group = (group + 1) % groupCount;
      render();
      schedule();
    }, 7000);
  }

  function updateControls() {
    previous.disabled = next.disabled = showAll;
    pauseButton.disabled = showAll;
    pauseButton.textContent = userPaused ? "Resume rotation" : "Pause rotation";
    allButton.textContent = showAll ? "Show groups" : "Show all names";
    allButton.setAttribute("aria-expanded", String(showAll));
  }

  function render(manual = false) {
    const start = group * groupSize;
    names.forEach((name, index) => {
      name.hidden = !showAll && (index < start || index >= start + groupSize);
    });
    viewport.scrollTop = 0;
    position.textContent = showAll ? `All ${names.length} names` : `${start + 1}–${Math.min(start + groupSize, names.length)} of ${names.length}`;
    updateControls();
    // Automatic swaps stay quiet for screen readers; announce manual navigation.
    if (manual) announcement.textContent = showAll ? `All ${names.length} contributors are shown. Scroll the list to read every name.` : `Contributors ${position.textContent}.`;
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
    // An explicit Resume works even while the rotation button has focus.
    focusHeld = false;
    updateControls();
    schedule();
  });
  allButton.addEventListener("click", () => {
    showAll = !showAll;
    userPaused = true;
    render(true);
    schedule();
  });
  panel.addEventListener("mouseenter", () => { hovered = true; schedule(); });
  panel.addEventListener("mouseleave", () => { hovered = false; schedule(); });
  panel.addEventListener("focusin", event => {
    focusHeld = true;
    // The rotation button keeps its current action until activated.
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
    const observer = new IntersectionObserver(entries => {
      inView = entries[0].isIntersecting;
      schedule();
    });
    observer.observe(panel);
  }

  render();
  controls.hidden = false;
  schedule();
})();
