const CACHE = 'nerimity-docs-v1';
const CUSTOM_404 = new URL('404-custom.html', self.location).href;

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.add(CUSTOM_404)));
  self.skipWaiting();
});

self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request).then(res => {
      if (res.status === 404) {
        return caches.match(CUSTOM_404).then(cached => cached || res);
      }
      return res;
    }).catch(() => caches.match(CUSTOM_404))
  );
});
