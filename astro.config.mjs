import { defineConfig } from 'astro/config';
import remarkGfm from 'remark-gfm';

export default defineConfig({
  site: 'https://oddly.maxoxo.me',
  markdown: {
    gfm: false,
    remarkPlugins: [[remarkGfm, { singleTilde: false }]],
  },
  build: {
    inlineStylesheets: 'always',
  },
});
