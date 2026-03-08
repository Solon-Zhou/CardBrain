/**
 * app.js — SPA hash router + bottom tab bar
 */
(() => {
  const container = document.getElementById("page-container");

  const routes = {
    "/": HomePage,
    "/compare": ComparePage,
    "/cards": CardsPage,
    "/nearby": NearbyPage,
    "/result": ResultPage,
  };

  // ── Tab Bar Active State ──
  function updateActiveTab(path) {
    document.querySelectorAll("#tabBar .tab-item").forEach((tab) => {
      const tabPath = tab.dataset.tab;
      tab.classList.toggle("active", tabPath === path);
    });
  }

  // ── Router ──
  function getRoute() {
    const hash = location.hash.replace("#", "") || "/";
    const qIdx = hash.indexOf("?");
    const path = qIdx >= 0 ? hash.substring(0, qIdx) : hash;
    const search = qIdx >= 0 ? hash.substring(qIdx + 1) : "";
    return { path, search };
  }

  function parseParams(search) {
    const p = {};
    if (!search) return p;
    search.split("&").forEach((pair) => {
      const [k, v] = pair.split("=");
      if (k) p[decodeURIComponent(k)] = decodeURIComponent(v || "");
    });
    return p;
  }

  async function navigate() {
    const { path, search } = getRoute();
    const params = parseParams(search);
    const render = routes[path] || routes["/"];

    updateActiveTab(path);

    container.innerHTML = '<div class="spinner">載入中...</div>';
    container.className = "page-enter";

    try {
      const html = await render(params);
      container.innerHTML = html;
      container.className = "page-enter";
      if (render.init) render.init(params);
    } catch (e) {
      console.error(e);
      container.innerHTML = '<div class="result-empty">載入失敗，請重試</div>';
    }
  }

  window.addEventListener("hashchange", navigate);
  window.addEventListener("DOMContentLoaded", navigate);
})();
