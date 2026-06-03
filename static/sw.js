// ✨ त्रिकाल दर्शन - Service Worker v1.0
// यह file PWA को offline काम करने देती है

const CACHE_NAME = 'trikal-darshan-v1';

// यह files offline के लिए cache होंगी
const STATIC_ASSETS = [
  '/',
  '/panchang/',
  '/milan/',
  '/static/css/style.css',
  '/static/logo.png',
  '/offline.html',
];

// ─── Install: Static files cache karo ───
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      // Individual failures se pura install fail na ho
      return Promise.allSettled(
        STATIC_ASSETS.map(url => cache.add(url).catch(e => console.warn('[SW] Skip:', url, e)))
      );
    })
  );
  self.skipWaiting();
});

// ─── Activate: Purana cache hatao ───
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating...');
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          })
      )
    )
  );
  self.clients.claim();
});

// ─── Fetch: Network first, Cache fallback strategy ───
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Sirf same-origin requests handle karo
  if (url.origin !== location.origin) return;

  // API calls ko cache mat karo (hamesha live data chahiye)
  if (url.pathname.startsWith('/api/') || 
      url.pathname.startsWith('/admin') ||
      url.pathname.startsWith('/telegram') ||
      url.pathname.startsWith('/django-admin')) {
    return; // Browser default behavior
  }

  // POST requests cache nahi hoti
  if (request.method !== 'GET') return;

  event.respondWith(
    fetch(request)
      .then((networkResponse) => {
        // Network se mila toh cache update karo
        if (networkResponse && networkResponse.status === 200) {
          const responseClone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseClone);
          });
        }
        return networkResponse;
      })
      .catch(() => {
        // Network nahi mila → cache dekho
        return caches.match(request).then((cachedResponse) => {
          if (cachedResponse) {
            console.log('[SW] Serving from cache:', request.url);
            return cachedResponse;
          }
          // Na network, na cache → offline page dikhao
          if (request.headers.get('accept').includes('text/html')) {
            return caches.match('/offline.html');
          }
        });
      })
  );
});

// ─── Push Notifications (future use) ───
self.addEventListener('push', (event) => {
  if (!event.data) return;
  const data = event.data.json();
  self.registration.showNotification(data.title || 'त्रिकाल दर्शन', {
    body: data.body || 'आपका दैनिक राशिफल तैयार है 🔮',
    icon: '/static/logo.png',
    badge: '/static/logo.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' },
  });
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data.url || '/')
  );
});
