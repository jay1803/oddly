import fs from 'node:fs';
import path from 'node:path';

const CONTENT_DIR = path.join(process.cwd(), 'src/content/posts');

function normalize(s: string): string {
  return s
    .replace(/[*_"“”"]/g, '')
    .replace(/\s+/g, '')
    .trim();
}

// A lot of the bulk-imported posts have a "description" that's just their
// body's first paragraph copied verbatim (an artifact of the original
// import script's fallback logic) — showing it again as an italic dek
// right above that same paragraph is pure duplication. Newer posts from
// the ongoing summarization pipeline write a real, distinct description,
// which should still render. Detect the redundant case by comparing the
// leading run of characters: copies (exact or truncated) always share it;
// genuinely different summaries diverge immediately.
export function isDekRedundant(postId: string, description: string): boolean {
  let raw: string;
  try {
    raw = fs.readFileSync(path.join(CONTENT_DIR, `${postId}.md`), 'utf-8');
  } catch {
    return false;
  }
  const parts = raw.split('---\n');
  const body = parts.length > 2 ? parts.slice(2).join('---\n') : raw;

  let firstPara: string | null = null;
  for (const line of body.split('\n')) {
    const s = line.trim();
    if (s && !s.startsWith('#') && !s.startsWith('```') && s !== '>') {
      firstPara = s.replace(/^>\s*/, '').replace(/^[-*]\s*/, '');
      break;
    }
  }
  if (!firstPara) return false;

  const a = normalize(description);
  const b = normalize(firstPara);
  const n = Math.min(20, a.length, b.length);
  return n > 0 && a.slice(0, n) === b.slice(0, n);
}
