/* 오프라인 캐시 — 내용(특히 data.js)을 바꾸면 CACHE 이름의 숫자를 올린다 */
const CACHE = 'my-timetable-v5';
const ASSETS = [
  './',
  'index.html',
  'style.css',
  'data.js',
  'app.js',
  'manifest.webmanifest',
  'icons/icon.svg',
  'icons/icon-180.png',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith('my-timetable-') && key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

// 네트워크 우선, 실패하면 캐시. 강의실이 바뀌어도 온라인이면 바로 반영되고, 오프라인에서도 열린다.
// 네트워크가 3초 넘게 느리면(약한 와이파이) 캐시를 먼저 보여 주고, 네트워크 응답은 뒤에서 캐시만 갱신한다.
const SLOW_MS = 3000;
self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET' || new URL(request.url).origin !== self.location.origin) return;
  const network = fetch(request).then((response) => {
    if (!response.ok) return response;
    const copy = response.clone();
    return caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {}).then(() => response);
  });
  event.waitUntil(network.catch(() => {}));
  const slow = new Promise((resolve) => setTimeout(resolve, SLOW_MS))
    .then(() => caches.match(request))
    .then((hit) => hit || network);
  event.respondWith(
    Promise.race([network, slow])
      .catch(() => caches.match(request).then((hit) => hit || caches.match('index.html')))
  );
});
