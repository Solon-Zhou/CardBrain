const CACHE_NAME = "cardbrain-v3";
const PRECACHE = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/api.js",
  "/static/js/store.js",
  "/static/js/pages/home.js",
  "/static/js/pages/result.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // All requests: network first, fallback to cache
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        // cache a fresh copy
        if (res.ok && url.origin === self.location.origin) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
