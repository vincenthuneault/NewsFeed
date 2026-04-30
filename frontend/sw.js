/**
 * Service Worker v4 — cache uniquement les assets statiques lourds.
 * JS et HTML : toujours réseau pour que les mises à jour soient immédiates.
 */

const CACHE = "newsfeed-v5";

// Activation immédiate sans pré-cache — skipWaiting fire instantanément
self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API, JS, HTML → toujours réseau, jamais de cache
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/js/") ||
    url.pathname === "/" ||
    url.pathname.endsWith(".html")
  ) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Images et audio (/static/) → Cache First — contenu généré, stable
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(e.request).then((cached) => {
        if (cached) return cached;
        return fetch(e.request).then((resp) => {
          if (resp.ok) caches.open(CACHE).then((c) => c.put(e.request, resp.clone()));
          return resp;
        });
      })
    );
    return;
  }

  // CSS → Network First avec fallback cache
  e.respondWith(
    fetch(e.request)
      .then((resp) => {
        if (resp.ok) caches.open(CACHE).then((c) => c.put(e.request, resp.clone()));
        return resp;
      })
      .catch(() => caches.match(e.request))
  );
});
