/**
 * launch-splash.js — in-app launch video splash
 * Note: Native OS launch screens (iOS/Android) are static; this runs after WebView loads.
 */
(() => {
  const MAX_MS = 7000;
  const MIN_MS = 600;

  function hideSplash(splash) {
    if (!splash || splash.classList.contains("is-hidden")) return;
    splash.classList.add("is-hidden");
    window.setTimeout(() => splash.remove(), 350);
  }

  function init() {
    const splash = document.getElementById("launchSplash");
    if (!splash) return;

    const video = document.getElementById("launchSplashVideo");
    const startedAt = Date.now();

    const safeHide = () => {
      const elapsed = Date.now() - startedAt;
      const wait = Math.max(0, MIN_MS - elapsed);
      window.setTimeout(() => hideSplash(splash), wait);
    };

    splash.addEventListener("click", safeHide, { passive: true, once: true });
    splash.addEventListener("touchstart", safeHide, { passive: true, once: true });

    window.setTimeout(safeHide, MAX_MS);

    if (!video) {
      safeHide();
      return;
    }

    video.addEventListener("ended", safeHide, { once: true });
    video.addEventListener("error", safeHide, { once: true });

    const p = video.play?.();
    if (p && typeof p.catch === "function") {
      p.catch(() => safeHide());
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();

