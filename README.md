# Oddly

每天从 X 时间线筛选的新奇发现：新产品、新 AI 模型、有意思的点子或工具。
Astro 静态站，部署到 GitHub Pages，自定义域名 `oddly.maxoxo.me`。

## 结构

- `src/content/posts/*.md` — 条目，frontmatter: `title, date, category(product|model|tool|idea|other), description, source, tweet_url, author`
- `data/seen_ids.json` — 已处理过的推文 ID 列表，用于每日采集时去重，避免同一条推文被重复筛选/发布
- `scripts/scrape_timeline.mjs` — 通过 ego-browser 抓取 X 时间线（For You + Following），输出 JSON 到 stdout

## 每日采集流程（由 cron job 执行）

1. 运行 `cat scripts/scrape_timeline.mjs | ego-browser nodejs` 抓取时间线原始推文
2. 用 `data/seen_ids.json` 过滤掉已经处理过的推文 ID
3. 对剩余推文做筛选：挑出"新奇的东西"——新产品发布、新 AI 模型、有意思的工具/点子；过滤闲聊、转推、广告、无关内容
4. 对选中的每条推文，写一个 Markdown 文件到 `src/content/posts/`（frontmatter 见上）
5. 把所有本次抓到的推文 ID（不管是否被选中）追加进 `data/seen_ids.json`，避免下次重复判断同一条
6. `npm run build` 验证构建无误
7. `git add -A && git commit --no-gpg-sign -m "..." && git push`（GitHub Actions 自动部署）

## 部署

- Repo: `jay1803/oddly`，deploy key 配置在 `~/.ssh/oddly_deploy`，remote 为 `github-oddly-deploy`
- GitHub Pages 通过 `.github/workflows/deploy.yml` 的 GitHub Actions 自动部署
- 自定义域名 `oddly.maxoxo.me`，需要在 Cloudflare 加一条 CNAME 记录指向 `jay1803.github.io`（代理开启，橙色云朵），参照 read.maxoxo.me 配置
