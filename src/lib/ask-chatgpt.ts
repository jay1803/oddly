// Builds a ChatGPT deep link that pre-fills a prompt asking GPT to explain
// an oddly entry in detail, carrying along its source links as context.
// https://chatgpt.com/?q=... opens a new conversation with the query
// pre-filled (and auto-submitted) — no API key or auth needed, just a URL.

export interface AskablePost {
  title: string;
  description?: string;
  category?: string;
  author?: string;
  tweet_url?: string;
  source?: string;
}

const CATEGORY_LABEL_ZH: Record<string, string> = {
  product: '产品',
  model: '模型',
  tool: '工具',
  idea: '点子',
  other: '其他',
};

export function buildAskChatGptUrl(post: AskablePost): string {
  const lines: string[] = [];
  lines.push(`请详细解释下面这条新奇发现，补充背景信息、最新进展和为什么值得关注：`);
  lines.push('');
  lines.push(`标题：${post.title}`);
  if (post.category) {
    lines.push(`类型：${CATEGORY_LABEL_ZH[post.category] ?? post.category}`);
  }
  if (post.description) {
    lines.push(`摘要：${post.description}`);
  }
  if (post.author) {
    lines.push(`来源作者：${post.author}`);
  }
  if (post.tweet_url) {
    lines.push(`原推文：${post.tweet_url}`);
  }
  if (post.source) {
    lines.push(`相关链接：${post.source}`);
  }
  lines.push('');
  lines.push('请用中文回答，包含：这是什么、技术/产品背景、为什么重要或有意思、可能的影响或后续值得关注的点。');

  const prompt = lines.join('\n');
  return `https://chatgpt.com/?q=${encodeURIComponent(prompt)}`;
}
