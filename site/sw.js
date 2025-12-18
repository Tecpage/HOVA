self.addEventListener('install', (e) => {
  e.waitUntil(caches.open('hova-v1').then((c) => c.addAll([
    './','./index.html','./styles.css','./app.js',
    './manifest.webmanifest','./sw.js',
    './assets/H_button.svg','./assets/fingerprint.svg',
    './nova.yaml','./CHANGELOG.md'
  ])));
});
self.addEventListener('fetch', (e) => {
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
