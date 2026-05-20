// OTTA Moyka — service worker (Django-rendered)
const VERSION = 'otta-v1';
const STATIC_CACHE = 'otta-static-' + VERSION;
const PAGE_CACHE = 'otta-pages-' + VERSION;
const OFFLINE_URL = '{{ offline_url }}';
const PRECACHE = [
{% for url in precache %}  '{{ url }}',
{% endfor %}];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => ![STATIC_CACHE, PAGE_CACHE].includes(k))
          .map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;

  // Only handle same-origin GET; never touch auth/POST/admin traffic.
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/admin/')) return;

  // Navigations: network-first, fall back to cached page, then offline page.
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((resp) => {
          const copy = resp.clone();
          caches.open(PAGE_CACHE).then((c) => c.put(req, copy));
          return resp;
        })
        .catch(() => caches.match(req).then((c) => c || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // Static assets: cache-first, then populate cache.
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then((cached) => cached || fetch(req).then((resp) => {
        const copy = resp.clone();
        caches.open(STATIC_CACHE).then((c) => c.put(req, copy));
        return resp;
      }).catch(() => cached))
    );
  }
});
