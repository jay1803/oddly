// Pages are read from local storage first. Refresh is an explicit network update.
const PAGE_CACHE = 'oddly-pages-v1';
const SHELL_CACHE = 'oddly-shell-v1';
const scope = new URL(self.registration.scope);
const home = scope.pathname;
const offline = `${home}offline/`;
const manifest = `${home}offline-manifest.json`;
const appAssets = [
  `${home}favicon.svg`,
  `${home}apple-touch-icon.png`,
  `${home}icons/icon-192.png`,
  `${home}icons/icon-512.png`,
  `${home}manifest.webmanifest`,
];

function inScope(url) {
  return url.origin === scope.origin && url.pathname.startsWith(home);
}

function pageKey(url) {
  const key = new URL(url);
  key.search = '';
  key.hash = '';
  return key.href;
}

function isHtml(response) {
  return response.ok && response.headers.get('content-type')?.includes('text/html');
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const shell = await caches.open(SHELL_CACHE);
      await shell.addAll([offline, ...appAssets]);
      await saveRecentPages();
    })()
  );
  self.skipWaiting();
});

async function saveRecentPages(onProgress) {
  const response = await fetch(manifest, { cache: 'no-store' });
  if (!response.ok) throw new Error('Could not load offline manifest');
  const { pages } = await response.json();
  if (!Array.isArray(pages) || pages.some((url) => !inScope(new URL(url, scope.origin)))) {
    throw new Error('Invalid offline manifest');
  }

  const cache = await caches.open(PAGE_CACHE);
  for (let index = 0; index < pages.length; index += 5) {
    const batch = pages.slice(index, index + 5);
    const responses = await Promise.all(
      batch.map((path) => fetch(new URL(path, scope.origin), { cache: 'no-store' }))
    );
    if (responses.some((page) => !isHtml(page))) throw new Error('Could not save recent pages');
    await Promise.all(
      batch.map((path, offset) => cache.put(pageKey(new URL(path, scope.origin)), responses[offset]))
    );
    onProgress?.(Math.min(index + batch.length, pages.length), pages.length);
  }
}

self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      caches.keys().then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith('oddly-shell-') && key !== SHELL_CACHE)
            .map((key) => caches.delete(key))
        )
      ),
      self.clients.claim(),
    ])
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || !inScope(url) || url.pathname.endsWith('/sw.js')) return;

  if (appAssets.includes(url.pathname)) {
    event.respondWith(caches.match(pageKey(url)).then((saved) => saved || fetch(request)));
    return;
  }

  const navigation = request.mode === 'navigate';
  const page = navigation || url.pathname.endsWith('/');
  if (!page) return;

  event.respondWith(
    (async () => {
      const key = pageKey(url);
      const saved = (await caches.open(PAGE_CACHE)).match(key);
      const shell = (await caches.open(SHELL_CACHE)).match(key);
      const cached = (await saved) || (await shell);
      if (cached) return cached;

      try {
        const response = await fetch(request);
        if (isHtml(response)) {
          try {
            await (await caches.open(PAGE_CACHE)).put(key, response.clone());
          } catch {
            // A full device cache should not prevent online reading.
          }
        }
        return response;
      } catch {
        if (navigation) {
          return (await caches.match(offline)) || Response.error();
        }
        return Response.error();
      }
    })()
  );
});

self.addEventListener('message', (event) => {
  if (event.data?.type === 'CACHE_POSTS') {
    const paths = Array.isArray(event.data.urls) ? event.data.urls.slice(0, 24) : [];
    event.waitUntil(
      (async () => {
        const urls = [...new Set(paths.map((path) => {
          try {
            const url = new URL(path, scope.origin);
            return inScope(url) && url.pathname.endsWith('/') ? pageKey(url) : null;
          } catch {
            return null;
          }
        }).filter(Boolean))];
        const cache = await caches.open(PAGE_CACHE);
        for (let index = 0; index < urls.length; index += 4) {
          await Promise.all(
            urls.slice(index, index + 4).map(async (url) => {
              if (await cache.match(url)) return;
              try {
                const response = await fetch(url);
                if (isHtml(response)) await cache.put(url, response);
              } catch {
                // The archive page still contains the post if this download fails.
              }
            })
          );
        }
      })()
    );
    return;
  }

  if (event.data?.type !== 'REFRESH') return;
  let target;
  try {
    target = new URL(event.data.url);
  } catch {
    event.ports[0]?.postMessage({ ok: false });
    return;
  }
  if (!inScope(target)) {
    event.ports[0]?.postMessage({ ok: false });
    return;
  }

  event.waitUntil(
    (async () => {
      try {
        await saveRecentPages((done, total) =>
          event.ports[0]?.postMessage({ progress: `${done}/${total} pages saved` })
        );
        if (pageKey(target) !== pageKey(new URL(home, scope.origin))) {
          const response = await fetch(pageKey(target), { cache: 'no-store' });
          if (!isHtml(response)) throw new Error('Could not refresh current page');
          await (await caches.open(PAGE_CACHE)).put(pageKey(target), response);
        }
        event.ports[0]?.postMessage({ ok: true });
      } catch {
        event.ports[0]?.postMessage({ ok: false });
      }
    })()
  );
});
