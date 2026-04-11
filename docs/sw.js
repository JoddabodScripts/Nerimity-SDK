const CACHE = 'nerimity-docs-v1';
const OFFLINE_404 = '/404-custom.html';

// Cache the custom 404 page on install
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.add(OFFLINE_404))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (!e.request.url.startsWith(self.location.origin)) return;

  e.respondWith(
    fetch(e.request).then(res => {
      // If the server returns a 404, serve our custom page instead
      if (res.status === 404) {
        return caches.match(OFFLINE_404).then(cached => cached || res);
      }
      return res;
    }).catch(() => caches.match(OFFLINE_404))
  );
});
