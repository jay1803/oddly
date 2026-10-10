#!/usr/bin/env python3
"""Delegate entry authoring for one novel candidate (tweet or Feedbin
article) to gpt-6-luna chat.

Keeps the expensive main model out of the writing loop — only orchestrates
(calls this script, validates JSON, writes the file, runs git). See the
hermes-model-delegation skill for the underlying `hermes chat` pattern.

Usage:
    python3 write_entry.py item.json > entry.json

item.json is EITHER shape:
- Tweet: {"id":..., "author":..., "handle":..., "text":..., "url":...}
  -> detailed "explain in full" prompt.
- Feedbin article: {"id":..., "title":..., "domain":..., "summary":...,
  "url":...} -> SIMPLE prompt per Max's 2026-10-10 instruction ("介绍
  清楚是什么，有什么用就行了" — no deep backstory, 1-2 sentence body).

Output: {"title":..., "category":"product|model|tool|idea|other",
         "description":..., "body":...}
On failure (non-JSON response, missing fields), exits non-zero and prints
the raw model output to stderr — caller must not silently fabricate a
fallback entry.
"""
import json
import os
import subprocess
import sys

HERMES_BIN = os.environ.get(
    "HERMES_BIN", os.path.expanduser("~/.hermes/hermes-agent/venv/bin/hermes")
)
LUNA_MODEL = os.environ.get("LUNA_MODEL", "gpt-6-luna")
LUNA_PROVIDER = os.environ.get("LUNA_PROVIDER", "openai-codex")

TWEET_PROMPT_TMPL = """你是 oddly 站点（每天筛选新奇发现：新产品、新技术、AI 技术更新）的内容撰写助手。下面这条推文已经被判定为"新奇"，现在需要你把它写成一条站点条目。

## 推文
作者: {author} ({handle})
正文: {text}
链接: {url}

## 要求
- title: 简短中文标题（不是原文复述，提炼核心信息，10-25字左右）
- category: 从 product/model/tool/idea/other 中选一个最贴切的
- description: 一句话中文摘要（30-60字），讲清楚这是什么、为什么值得关注
- body: 1-3句中文正文，补充背景或细节，不是把 description 换个说法重复一遍；
  如果推文信息量本身有限，body 可以如实简短，不要编造没有依据的细节

只输出严格 JSON，不要任何其他文字、不要 markdown 代码块标记：
{{"title": "...", "category": "...", "description": "...", "body": "..."}}"""

# Deliberately simple per Max's 2026-10-10 instruction: Feedbin-sourced
# candidates don't need the deep-dive treatment tweets get. Just say what
# it is and what it's for.
ARTICLE_PROMPT_TMPL = """你是 oddly 站点（筛选新奇发现：新产品、新技术、AI 技术更新）的内容撰写助手。下面这篇文章已经被判定为"新奇"（一个新产品/工具/技术），现在需要你写一条简单的站点条目——不用复杂分析，介绍清楚是什么、有什么用就行了。

## 文章
标题: {title}
来源域名: {domain}
摘要: {summary}
链接: {url}

## 要求
- title: 简短中文标题（10-25字左右）
- category: 从 product/model/tool/idea/other 中选一个最贴切的
- description: 一句话中文摘要（30-60字），说清楚这是什么
- body: 只要 1-2 句话，说清楚这个东西是什么、有什么用，不展开背景分析、
  不猜测影响或后续发展

只输出严格 JSON，不要任何其他文字、不要 markdown 代码块标记：
{{"title": "...", "category": "...", "description": "...", "body": "..."}}"""


def build_prompt(item):
    """Detect shape (tweet vs Feedbin article) and return the right prompt."""
    if "text" in item:
        return TWEET_PROMPT_TMPL.format(
            author=item.get("author", ""),
            handle=item.get("handle", ""),
            text=item.get("text", ""),
            url=item.get("url", ""),
        )
    return ARTICLE_PROMPT_TMPL.format(
        title=item.get("title", ""),
        domain=item.get("domain", ""),
        summary=item.get("summary", ""),
        url=item.get("url", ""),
    )


def main():
    if len(sys.argv) != 2:
        print("Usage: write_entry.py item.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        item = json.load(f)

    prompt = build_prompt(item)

    result = subprocess.run(
        [HERMES_BIN, "chat", "-q", prompt, "-m", LUNA_MODEL, "--provider", LUNA_PROVIDER, "-t", "", "-Q"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = result.stdout.strip()
    lines = [l for l in out.split("\n") if not l.startswith("session_id:")]
    answer_text = "\n".join(lines).strip()
    # Strip accidental markdown code fences.
    if answer_text.startswith("```"):
        answer_text = answer_text.strip("`")
        if answer_text.startswith("json"):
            answer_text = answer_text[4:]
        answer_text = answer_text.strip()

    try:
        parsed = json.loads(answer_text)
    except json.JSONDecodeError:
        print(f"Luna 返回非 JSON，需人工复核: {answer_text[:500]}", file=sys.stderr)
        sys.exit(1)

    required = {"title", "category", "description", "body"}
    if not required.issubset(parsed.keys()):
        print(f"Luna 输出缺字段: {parsed}", file=sys.stderr)
        sys.exit(1)

    if parsed["category"] not in ("product", "model", "tool", "idea", "other"):
        parsed["category"] = "other"

    print(json.dumps(parsed, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
