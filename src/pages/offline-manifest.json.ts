import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';
import { base } from '../lib/base';
import { FEED_PAGE_SIZE } from '../lib/feed';

const OFFLINE_POST_COUNT = 50;

export const GET: APIRoute = async () => {
  const posts = (await getCollection('posts'))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf())
    .slice(0, OFFLINE_POST_COUNT);
  const feedPages = Array.from(
    { length: Math.ceil(posts.length / FEED_PAGE_SIZE) - 1 },
    (_, index) => `${base}/${index + 2}/`
  );

  return new Response(
    JSON.stringify({
      count: posts.length,
      pages: [
        `${base}/`,
        `${base}/about/`,
        ...feedPages,
        ...posts.map((post) => `${base}/${post.id}/`),
      ],
    }),
    { headers: { 'Content-Type': 'application/json; charset=utf-8' } }
  );
};
