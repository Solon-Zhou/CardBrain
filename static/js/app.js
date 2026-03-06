/**
 * app.js — SPA hash router + init
 */
(() => {
  const container = document.getElementById("page-container");

  const routes = {
    "/": HomePage,
    "/result": ResultPage,
  };

  function getRoute() {
    const hash = location.hash.replace("#", "") || "/";
    // extract path (before ?)
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

    container.innerHTML = '<div class="spinner">載入中...</div>';
    container.className = "page-enter";

    try {
      const html = await render(params);
      container.innerHTML = html;
      container.className = "page-enter";
      // call page init if exists
      if (render.init) render.init(params);
    } catch (e) {
      console.error(e);
      container.innerHTML = '<div class="result-empty">載入失敗，請重試</div>';
    }
  }

  window.addEventListener("hashchange", navigate);
  window.addEventListener("DOMContentLoaded", navigate);
})();
