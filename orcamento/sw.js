// Na Bucha — app instalável (service worker).
// Atualização sem trabalho para o pintor: com internet, sempre busca a versão nova do site
// (rede primeiro); a cópia guardada só é usada quando está sem sinal.
// Para desligar: apague este arquivo e o trecho "serviceWorker" do orcamento/index.html.
const CACHE = 'nabucha-app-v1';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil((async () => {
  for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k);
  await self.clients.claim();
})()));

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;                       // registro e áudio passam direto
  const url = new URL(req.url);
  const nosso = url.origin === location.origin;
  const fonte = /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname);
  if (!nosso && !fonte) return;                           // servidor do áudio/registro: sem cache
  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const res = await fetch(req, { cache: 'no-store' });
      if (res.ok) cache.put(req, res.clone());
      return res;
    } catch (err) {
      const salvo = await cache.match(req, { ignoreSearch: req.mode === 'navigate' });
      if (salvo) return salvo;
      throw err;
    }
  })());
});
