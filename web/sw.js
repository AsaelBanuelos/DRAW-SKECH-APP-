/*  RealSketch — Service Worker  */

const CACHE_NAME = "realsketch-v2";

// Files cached for offline use (app shell).
const SHELL_ASSETS = [
    "/",
    "/index.html",
    "/css/style.css",
    "/js/app.js",
    "/manifest.json",
    "/icons/icon-192.png",
    "/icons/icon-512.png",
];

// ---------- Install ----------
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then((cache) => cache.addAll(SHELL_ASSETS))
            .then(() => self.skipWaiting()),
    );
});

// ---------- Activate ----------
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches
            .keys()
            .then((keys) =>
                Promise.all(
                    keys
                        .filter((k) => k !== CACHE_NAME)
                        .map((k) => caches.delete(k)),
                ),
            )
            .then(() => self.clients.claim()),
    );
});

// ---------- Fetch ----------
self.addEventListener("fetch", (event) => {
    const { request } = event;

    // API calls always go to the network (never cache processing results).
    if (request.url.includes("/api/")) {
        event.respondWith(fetch(request));
        return;
    }

    // Cache-first for shell assets.
    event.respondWith(
        caches.match(request).then((cached) => cached || fetch(request)),
    );
});
