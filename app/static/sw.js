// app/static/sw.js - PRODUCTION - Fixes stuck "Installing EvidLens..."
const CACHE = "evidlens-v3";

const CORE = [
  "/",
  "/static/manifest.webmanifest",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/logo.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/icon-512-maskable.png"
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(CORE))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.map((k) => (k !== CACHE ? caches.delete(k) : null))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);

  // NEVER cache API / backend - always live, never stale
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/market/") ||
    url.pathname.startsWith("/reports/")
  ) {
    return;
  }

  // Only same-origin
  if (url.origin !== self.location.origin) return;

  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
