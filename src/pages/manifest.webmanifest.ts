import type { APIRoute } from 'astro';
import { base } from '../lib/base';

export const GET: APIRoute = () =>
  new Response(
    JSON.stringify({
      id: `${base}/`,
      name: 'oddly',
      short_name: 'oddly',
      description: '每天筛选的新产品、新技术和 AI 更新，支持离线阅读。',
      start_url: `${base}/`,
      scope: `${base}/`,
      display: 'standalone',
      background_color: '#f7f4ed',
      theme_color: '#f7f4ed',
      icons: [
        { src: `${base}/icons/icon-192.png`, sizes: '192x192', type: 'image/png', purpose: 'any' },
        {
          src: `${base}/icons/icon-512.png`,
          sizes: '512x512',
          type: 'image/png',
          purpose: 'any maskable',
        },
      ],
    }),
    { headers: { 'Content-Type': 'application/manifest+json; charset=utf-8' } }
  );
