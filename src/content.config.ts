import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const finds = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/posts' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    category: z.enum(['product', 'model', 'tool', 'idea', 'other']).default('other'),
    description: z.string().optional(),
    source: z.string().url().optional(),
    tweet_url: z.string().url().optional(),
    author: z.string().optional(),
  }),
});

export const collections = { posts: finds };
