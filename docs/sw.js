/*  RealSketch — Service Worker (GitHub Pages / static)  */

const CACHE_NAME = "realsketch-v16";

const SHELL_ASSETS = [
    "./",
    "./index.html",
    "./css/style.css",
    "./js/app.js",
    "./js/processing.js",
    "./manifest.json",
    "./icons/icon-192.png",
    "./icons/icon-512.png",
];

// Install — cache shell
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches
            .open(CACHE_NAME)
            .then((cache) => cache.addAll(SHELL_ASSETS))
            .then(() => self.skipWaiting()),
    );
});

// Activate — clean old caches
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

// Fetch — stale-while-revalidate for shell, cache-first for CDN
self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);
    const isShell = url.origin === self.location.origin;

    if (isShell) {
        // Network-first for our own assets so updates apply immediately
        event.respondWith(
            fetch(event.request)
                .then((response) => {
                    if (
                        response &&
                        response.status === 200 &&
                        event.request.method === "GET"
                    ) {
                        const clone = response.clone();
                        caches
                            .open(CACHE_NAME)
                            .then((c) => c.put(event.request, clone));
                    }
                    return response;
                })
                .catch(() => caches.match(event.request)),
        );
    } else {
        // Cache-first for CDN resources (e.g. OpenCV.js — versioned URL)
        event.respondWith(
            caches.match(event.request).then((cached) => {
                if (cached) return cached;
                return fetch(event.request).then((response) => {
                    if (
                        response &&
                        response.status === 200 &&
                        event.request.method === "GET"
                    ) {
                        const clone = response.clone();
                        caches
                            .open(CACHE_NAME)
                            .then((c) => c.put(event.request, clone));
                    }
                    return response;
                });
            }),
        );
    }
});
