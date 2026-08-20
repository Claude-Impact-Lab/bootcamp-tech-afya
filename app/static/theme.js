(() => {
  const storageKey = "portal-theme";
  const root = document.documentElement;
  const saved = localStorage.getItem(storageKey);
  root.dataset.theme = saved === "dark" ? "dark" : "light";

  function updateButtons() {
    const dark = root.dataset.theme === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.textContent = dark ? "☀ Tema claro" : "☾ Tema escuro";
      button.setAttribute("aria-pressed", String(dark));
      button.setAttribute("aria-label", dark ? "Ativar tema claro" : "Ativar tema escuro");
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    updateButtons();
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
        localStorage.setItem(storageKey, root.dataset.theme);
        updateButtons();
      });
    });
  });
})();
