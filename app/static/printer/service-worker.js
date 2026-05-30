// Service Worker - iyb waffle Yazıcı PWA
// Arka plan çalışma ve offline destek için

const CACHE_NAME = 'iyb-waffle-printer-v1';
const URLS_TO_CACHE = [
    '/printer',
    '/manifest.json'
];

// Install
self.addEventListener('install', (event) => {
    console.log('[SW] Yükleniyor...');
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Cache açıldı');
            return cache.addAll(URLS_TO_CACHE);
        }).catch(err => console.log('[SW] Cache hatası:', err))
    );
    self.skipWaiting();
});

// Activate
self.addEventListener('activate', (event) => {
    console.log('[SW] Aktif');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[SW] Eski cache siliniyor:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch (network-first stratejisi - API çağrıları için)
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // API çağrıları her zaman sunucudan gitsin
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(JSON.stringify({ ok: false, offline: true }), {
                    headers: { 'Content-Type': 'application/json' }
                });
            })
        );
        return;
    }
    
    // Diğer kaynaklar cache-first
    event.respondWith(
        caches.match(event.request).then((response) => {
            if (response) return response;
            return fetch(event.request);
        })
    );
});

// Push notifications (opsiyonel - ileride kullanılabilir)
self.addEventListener('push', (event) => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body || 'Yeni sipariş',
            icon: '/static/printer/icon-192.png',
            badge: '/static/printer/icon-192.png',
            vibrate: [200, 100, 200],
            tag: 'new-order',
            requireInteraction: true
        };
        event.waitUntil(
            self.registration.showNotification(data.title || 'iyb waffle', options)
        );
    }
});

// Notification click - sayfayı aç
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then((clientList) => {
            for (const client of clientList) {
                if (client.url.includes('/printer') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('/printer');
            }
        })
    );
});