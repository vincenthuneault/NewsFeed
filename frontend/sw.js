/**
 * Service Worker — cache les assets lourds (images, audio, CSS).
 * JS exclu du cache : doit toujours être à jour.
 */

const CACHE = "newsfeed-v3";
const STATIC_ASSETS = ["/css/app.css"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API + JS → toujours réseau, jamais de cache
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/js/")) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Images et audio → Cache First (contenu généré, ne change pas)
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(e.request).then((cached) => {
        if (cached) return cached;
        return fetch(e.request).then((resp) => {
          if (resp.ok) {
            caches.open(CACHE).then((cache) => cache.put(e.request, resp.clone()));
          }
          return resp;
        });
      })
    );
    return;
  }

  // Reste (CSS, HTML) → Network First avec fallback cache
  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        if (resp.ok) {
          caches.open(CACHE).then((cache) => cache.put(e.request, resp.clone()));
        }
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
