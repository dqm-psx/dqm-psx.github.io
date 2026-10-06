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
