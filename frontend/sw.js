/**
 * Service Worker — cache les assets statiques pour chargement rapide.
 * Stratégie : Cache First pour les assets, Network First pour l'API.
 */

const CACHE = "newsfeed-v2";
const STATIC_ASSETS = ["/", "/css/app.css", "/js/app.js", "/js/api.js", "/js/feed.js", "/js/player.js", "/js/ui.js"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API → Network First (jamais le cache)
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Static → Cache First
  e.respondWith(
    caches.match(e.request).then((cached) => {
      if (cached) return cached;
      return fetch(e.request).then((resp) => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE).then((cache) => cache.put(e.request, clone));
        }
        return resp;
      });
    })
  );
});
