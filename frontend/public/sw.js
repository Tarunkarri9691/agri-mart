// Offline support: app shell cache-first; API GET requests network-first with cached fallback,
// so a farmer on a weak connection still sees the last recommendations.
const SHELL = "agri-shell-v2";
const API = "agri-api-v2";
self.addEventListener("install", (e) => { e.waitUntil(caches.open(SHELL).then((c) => c.addAll(["/", "/manifest.webmanifest", "/icon.svg"]))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => ![SHELL, API].includes(k)).map((k) => caches.delete(k))))); self.clients.claim(); });
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) {
    if (/\/(recommendations|offers|notifications|farmer|buyer|markets|msp)/.test(url.pathname)) {
      e.respondWith(fetch(req).then((res) => { const copy = res.clone(); caches.open(API).then((c) => c.put(req, copy)); return res; })
        .catch(() => caches.match(req).then((hit) => hit || new Response(JSON.stringify({ detail: "You are offline" }), { status: 503, headers: { "Content-Type": "application/json" } }))));
    }
    return;
  }
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req).then((res) => { const copy = res.clone(); caches.open(SHELL).then((c) => c.put(req, copy)); return res; }).catch(() => caches.match("/"))));
});
