"use strict";

const scenes = [
  { src: "assets/screenshots/balk-travelers-gate.png", alt: "Terry and three monsters approaching a blue Travelers’ Gate in a torchlit dungeon", caption: "Through the Travelers’ Gates", credit: "BalK" },
  { src: "assets/screenshots/balk-championship.png", alt: "Terry is encouraged to win the championship in a richly decorated room", caption: "A championship to chase", credit: "BalK" },
  { src: "assets/screenshots/balk-kings-praise.png", alt: "The king praises Terry and his monster party in the throne room", caption: "An audience with the king", credit: "BalK" },
  { src: "assets/screenshots/balk-cave-encounter.png", alt: "Terry faces an angry monster among broken pots in a cave", caption: "An unexpected encounter", credit: "BalK" },
  { src: "assets/screenshots/balk-field-skills.png", alt: "The English field skills menu with Seek selected and its description visible", caption: "The right skill for the journey", credit: "BalK" },
  { src: "assets/screenshots/balk-adventure-record.png", alt: "Terry’s information screen showing play time, farm monsters, gates cleared, and species found", caption: "Every adventure leaves a record", credit: "BalK" },
  { src: "assets/screenshots/balk-party-flee.png", alt: "A monster in Terry’s party warns everyone to run away quickly", caption: "Knowing when to run", credit: "BalK" },
  { src: "assets/screenshots/balk-party-together.png", alt: "A party member says it is important to stick together", caption: "Better together", credit: "BalK" },
  { src: "assets/screenshots/balk-party-attack.png", alt: "A party member declares that healing wastes time and urges an attack", caption: "A party with plenty of personality", credit: "BalK" },
  { src: "assets/screenshots/balk-arena-rival.png", alt: "A rival challenges Terry and his three monsters before an arena match", caption: "Ready for the arena", credit: "BalK" },
  { src: "assets/screenshots/balk-volcanic-trail.png", alt: "Terry leads a monster party along a rocky trail beside glowing lava", caption: "A trail through a fiery world", credit: "BalK" },
  { src: "assets/great-tree.png", alt: "A colorful scene from the world of Dragon Quest Monsters on PlayStation", caption: "A world beyond the Travelers’ Gates" },
  { src: "assets/adventure.png", alt: "The party exploring a room of treasure chests in the English translation", caption: "A new discovery around every corner" },
  { src: "assets/battle.png", alt: "An English-language monster battle in the PlayStation game", caption: "A little courage. A few good monsters." }
];
(() => {
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
  let userPaused = reducedMotion.matches;
  let hovered = gallery.matches(":hover");
  let focusHeld = gallery.contains(document.activeElement);
  let inView = !("IntersectionObserver" in window);
  let autoPending = false;
  let timer = null;
  let finishLoading = null;

  scenes.forEach((scene, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${String(index + 1).padStart(2, "0")} · ${scene.caption}`;
    selection.append(option);
  });

  function clearLoading() {
    finishLoading?.();
    finishLoading = null;
    stage.setAttribute("aria-busy", "false");
    loading.hidden = true;
  }

  function updatePauseButton() {
    pauseButton.textContent = userPaused ? "Play slideshow" : "Pause slideshow";
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

  async function showScene(index, manual = false) {
    clearTimeout(timer);
    const request = ++latestRequest;
    requestedScene = index;
    autoPending = !manual;
    clearLoading();
    status.textContent = "";
    status.classList.add("visually-hidden");
    const scene = scenes[index];
    if (manual) {
      userPaused = true;
      updatePauseButton();
    }
    finishLoading = window.DqmLoading.begin();
    stage.setAttribute("aria-busy", "true");
    loading.hidden = false;
    const nextImage = new Image();
    nextImage.src = scene.src;
    try {
      await nextImage.decode();
      if (request !== latestRequest) return;
      featuredScreen.src = scene.src;
      featuredScreen.alt = scene.alt;
      activeScene = index;
      document.getElementById("screen-caption").textContent = scene.caption;
      document.getElementById("screen-number").textContent = `${String(index + 1).padStart(2, "0")} / ${String(scenes.length).padStart(2, "0")}`;
      document.getElementById("screen-credit").textContent = scene.credit ? `Screenshot by ${scene.credit}` : "From the English translation";
      selection.value = String(index);
      // Automatic rotation stays quiet for screen readers.
      if (manual) status.textContent = `Screenshot ${index + 1} of ${scenes.length}: ${scene.caption}.`;
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
  selection.addEventListener("change", () => showScene(Number(selection.value), true));
  pauseButton.addEventListener("click", () => {
    userPaused = !userPaused;
    // Explicit Play may resume while this button retains keyboard focus.
    focusHeld = false;
    updatePauseButton();
    schedule();
  });
  gallery.addEventListener("mouseenter", () => { hovered = true; schedule(); });
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
  document.getElementById("scene-controls").hidden = false;
  schedule();
})();

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
