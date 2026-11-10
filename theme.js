(() => {
  const key = "dqm-theme";
  const root = document.documentElement;
  let select;

  function apply(value) {
    if (value === "light" || value === "dark") {
      root.dataset.theme = value;
    } else {
      delete root.dataset.theme;
    }
    if (select) select.value = root.dataset.theme || "system";
  }

  try { apply(localStorage.getItem(key)); } catch { /* CSS follows the system. */ }
  window.addEventListener("storage", event => {
    if (event.key === key || event.key === null) apply(event.newValue);
  });

  document.addEventListener("DOMContentLoaded", () => {
    select = document.getElementById("theme-select");
    if (!select) return;
    select.value = root.dataset.theme || "system";
    select.addEventListener("change", () => {
      apply(select.value);
      try {
        if (select.value === "system") localStorage.removeItem(key);
        else localStorage.setItem(key, select.value);
      } catch { /* The choice still applies to this page. */ }
    });
    select.closest("label").hidden = false;
  });
})();
