/**
 * app.js — SPA hash router + hamburger nav
 */
(() => {
  const container = document.getElementById("page-container");
  const sidenav = document.getElementById("sideNav");
  const overlay = document.getElementById("sideNavOverlay");
  const hamburger = document.getElementById("hamburgerBtn");

  const routes = {
    "/": HomePage,
    "/cards": CardsPage,
    "/nearby": NearbyPage,
    "/result": ResultPage,
  };

  // ── Hamburger Side Nav ──
  function openNav() {
    sidenav.classList.add("open");
    overlay.classList.add("open");
  }
  function closeNav() {
    sidenav.classList.remove("open");
    overlay.classList.remove("open");
  }

  hamburger.addEventListener("click", openNav);
  overlay.addEventListener("click", closeNav);

  // close nav when clicking a nav link
  sidenav.querySelectorAll(".sidenav-link").forEach((link) => {
    link.addEventListener("click", closeNav);
  });

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

  function updateActiveNav(path) {
    sidenav.querySelectorAll(".sidenav-link").forEach((link) => {
      const href = link.getAttribute("href").replace("#", "");
      link.classList.toggle("active", href === path);
    });
  }

  async function navigate() {
    const { path, search } = getRoute();
    const params = parseParams(search);
    const render = routes[path] || routes["/"];

    updateActiveNav(path);

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
