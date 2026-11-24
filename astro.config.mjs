import { defineConfig } from 'astro/config';
import remarkGfm from 'remark-gfm';
import readingTheme from 'astro-reading-theme';
import rehypePangu from 'astro-reading-theme/rehype-pangu';

export default defineConfig({
  site: 'https://oddly.maxoxo.me',
  integrations: [
    readingTheme({
      name: 'oddly',
      lang: 'zh-CN',
      description: '每天从 X 时间线和 Feedbin 筛选的新产品、新技术和 AI 更新。',
      dek: ['时间线上的新奇玩意。', '新产品、新技术、AI 更新。没有算法，只有好奇心。'],
      tagline: '新产品、新技术、AI 更新',
      manifestDescription: '每天筛选的新产品、新技术和 AI 更新，支持离线阅读。',
      rssDescription: '每天筛选的新产品、新技术和 AI 更新',
      nav: [{ label: '关于', href: '/about/' }],
      footerLink: { label: 'RSS', href: '/rss.xml' },
      features: { category: true, author: false, domain: false, listen: false },
      // Files below replace the theme's versions (keys relative to the theme's src/).
      overrides: {
        'components/PostEntry.astro': 'src/overrides/components/PostEntry.astro',
        'pages/[...slug].astro': 'src/overrides/pages/[...slug].astro',
        'pages/[...page].astro': 'src/overrides/pages/[...page].astro',
        'pages/category/[category]/[...page].astro': 'src/overrides/pages/category/[category]/[...page].astro',
        'lib/feed.ts': 'src/lib/feed.ts',
      },
    }),
  ],
  markdown: {
    gfm: false,
    remarkPlugins: [[remarkGfm, { singleTilde: false }]],
    rehypePlugins: [rehypePangu],
  },
  build: {
    inlineStylesheets: 'always',
  },
});
