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

  let _currentPage = null;

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

    // 清理前一頁的資源（Geo、Leaflet、事件監聽器等）
    if (_currentPage && _currentPage.destroy) {
      _currentPage.destroy();
    }

    container.innerHTML = '<div class="spinner">載入中...</div>';
    container.className = "page-enter";
    container.scrollTop = 0;

    try {
      const html = await render(params);
      container.innerHTML = html;
      container.className = "page-enter";
      _currentPage = render;
      if (render.init) render.init(params);
    } catch (e) {
      console.error(e);
      container.innerHTML = '<div class="result-empty">載入失敗，請重試</div>';
    }
  }

  window.addEventListener("hashchange", navigate);
  window.addEventListener("DOMContentLoaded", navigate);
})();
