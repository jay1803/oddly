import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import { base } from '../lib/base';

const FEED_LIMIT = 100;

export async function GET(context) {
  const posts = (await getCollection('posts'))
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf())
    .slice(0, FEED_LIMIT);

  return rss({
    title: 'oddly',
    description: '每天筛选的新产品、新技术和 AI 更新',
    site: context.site,
    items: posts.map((post) => ({
      title: post.data.title,
      pubDate: post.data.date,
      description: post.data.description ?? post.data.title,
      categories: [post.data.category],
      link: `${base}/${post.id}/`,
    })),
  });
}
