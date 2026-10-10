#!/usr/bin/env python3
"""Two-tier oddly triage classifier: Jev (fast, cheap) -> Luna Decisions (semantic fallback).

Mirrors feedbin-cli's jev_triage.py pattern (see that skill + the
hermes-model-delegation skill) but for a binary novel/skip decision instead
of star/skip/unsure.

Tier 1 (Jev): every candidate tweet gets a single `choice` question
(novel/skip) in well under a second each. Low-confidence answers are
escalated.

Tier 2 (GPT-6 Luna Decisions, via OpenRouter's `/alpha/decisions` endpoint —
see the `luna-decisions` skill in jay1803/skills): only items Jev was unsure
about (or answered with low confidence). This is a bounded typed-probability
classification call, NOT a `hermes chat` generative call — Luna Decisions is
purpose-built for exactly this novel/skip classification task and is cheaper
than routing through ordinary chat. Content WRITING (title/description/body)
still goes through ordinary `gpt-6-luna` chat in write_entry.py — only the
judgment step uses Decisions.

Usage:
    python3 oddly_triage.py tweets.json > results.json

tweets.json is a JSON array of objects, each with at minimum:
    {"id": "...", "author": "...", "handle": "...", "text": "...",
     "url": "...", "isRetweet": false}

Output is a JSON array of:
    {"id": ..., "label": "novel"|"skip", "tier": "jev"|"luna_decisions"|"error", "reason": "..."}

Requires:
- ~/.config/jev/.env.local with API_KEY=... (TypeSafe/Jev API key)
- OPENROUTER_API_KEY in environment or ~/.hermes/.env (for Luna Decisions)
"""
import json
import os
import sys
import urllib.request
import urllib.error

JEV_ENV_FILE = os.environ.get("JEV_ENV_FILE", os.path.expanduser("~/.config/jev/.env.local"))
HERMES_ENV_FILE = os.environ.get("HERMES_ENV_FILE", os.path.expanduser("~/.hermes/.env"))
LUNA_DECISIONS_MODEL = os.environ.get("LUNA_DECISIONS_MODEL", "openai/gpt-6-luna-decisions")
LUNA_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"

JEV_API_URL = "https://api.typesafe.ai/v1/systemone"

# Same reasoning as feedbin-cli's jev_triage.py: Jev's choice sampling can
# emit a confident-looking novel/skip on borderline items when it should
# really say unsure. Treat low confidence as unsure and escalate.
JEV_CONFIDENCE_FLOOR = float(os.environ.get("JEV_CONFIDENCE_FLOOR", "0.6"))

# Kept in sync with references/triage-rules.md — if you edit the rules
# there, update this instructions string too (and vice versa).
TRIAGE_INSTRUCTIONS = (
    "判断这条推文是否值得发布（novel）：只有三类算 novel——①新产品发布"
    "（实际可用/即将发布的软硬件产品、新功能上线）；②新技术（工程/技术"
    "突破、新方法、新协议、新基础设施，非设计/视觉类）；③AI 技术相关更新"
    "（新 AI 模型发布、benchmark 突破、训练方法、推理优化、AI 工具/框架的"
    "技术性更新）。不属于这三类的，包括单纯有意思的点子、生活方式分享、"
    "概念性讨论，都判 skip。"
    "设计作品类内容一律 skip：壁纸、桌面主题、图标重绘、UI/UX 设计分享、"
    "作品集展示、字体设计、海报、插画、品牌视觉、Logo 重设计，以及设计工具"
    "的用法展示/灵感类帖子。即使标题带'新品发布'等字样，只要内容本质是视觉/"
    "设计作品展示而非产品/技术本体，都判 skip。"
    "其他 skip 情形：日常闲聊、情绪表达、梗图、单纯转推他人观点、个人生活"
    "分享、纯广告、政治社会评论（除非直接是产品/模型新闻）。"
    "转推（isRetweet=true）默认优先级降低，但如果转推内容本身是官方账号发布"
    "的产品/模型消息，仍可判 novel。"
    "官方科技公司账号（OpenAI、Anthropic、Google DeepMind 等）的产品/模型"
    "发布默认倾向 novel，除非纯营销话术没有实质信息。"
    "无实质文本、仅图片无说明的默认 skip。"
    "互动数据（回复/转发/点赞数）辅助判断广告嫌疑：互动量极低（个位数）"
    "且文案带明显推广/CTA语气（'免费试用''立即体验''私信咨询''现已开放'"
    "等营销号召用语）的，倾向判 skip，这是广告信号。但互动量低不能单独"
    "作为 skip 的充分条件——刚发布的新内容互动量低是正常的，要结合文案"
    "语气和账号性质综合判断，不要仅凭低互动一刀切。"
)

LUNA_PROMPT_INSTRUCTIONS_TMPL = """你是 oddly 新奇发现筛选器的第二级裁判。这条内容被第一级快速分类器（Jev）标记为 unsure，现在需要你结合语义理解做最终判断：novel 或 skip（只能二选一）。

## 判断标准
{instructions}

## Jev 第一级判断（供参考）
novel 概率: {novel_prob}, unsure 概率: {unsure_prob}, skip 概率: {skip_prob}"""


def build_state(item):
    """Build the Jev/Luna Decisions `state` text for one candidate.

    Supports two item shapes:
    - Tweet (from scrape_timeline.mjs / x_search): has `text`, optionally
      `author`/`handle`/`isRetweet`.
    - Feedbin article (from the feedbin triage cron's skip-candidate
      export — see references/triage-rules.md "第三数据源"): has `title`
      and `summary`, optionally `domain`.
    Detected by presence of `text` (tweet) vs `title`+`summary` (article).
    """
    if "text" in item:
        engagement = (
            f"互动数据: 回复{item.get('replyCount', '未知')} / "
            f"转发{item.get('retweetCount', '未知')} / "
            f"点赞{item.get('likeCount', '未知')}"
            if "replyCount" in item or "likeCount" in item or "retweetCount" in item
            else "互动数据: 未知（此来源不提供互动数据，如 x_search）"
        )
        return (
            f"作者: {item.get('author', '')} ({item.get('handle', '')})\n"
            f"是否转推: {item.get('isRetweet', False)}\n"
            f"{engagement}\n"
            f"正文: {item.get('text', '')}"
        )
    return (
        f"标题: {item.get('title', '')}\n"
        f"来源域名: {item.get('domain', '')}\n"
        f"摘要: {item.get('summary', '')}"
    )


def load_jev_api_key():
    if not os.path.exists(JEV_ENV_FILE):
        raise RuntimeError(f"Jev credentials file not found: {JEV_ENV_FILE}")
    with open(JEV_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError(f"API_KEY not found in {JEV_ENV_FILE}")


def load_openrouter_api_key():
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    if os.path.exists(HERMES_ENV_FILE):
        with open(HERMES_ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError(
        f"OPENROUTER_API_KEY not found in environment or {HERMES_ENV_FILE}"
    )


def jev_classify(item, api_key):
    state = build_state(item)
    payload = {
        "state": state,
        "model": "jev-latest",
        "questions": {
            "label": {
                "type": "choice",
                "instructions": TRIAGE_INSTRUCTIONS,
                "criteria": {
                    "novel": "高置信度值得发布：新产品/新技术/AI 技术更新（非设计作品）",
                    "skip": "高置信度不值得发布：闲聊/情绪/梗图/生活分享/广告/转发辩论/设计作品类内容",
                    "unsure": "边缘情况、信息不足、难以判断",
                },
            }
        },
    }
    req = urllib.request.Request(
        JEV_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    answer = body["answers"]["label"]
    return {
        "choice": answer["choice"],
        "confidence": answer.get("confidence"),
        "probabilities": answer.get("probabilities", {}),
    }


def luna_decisions_classify(item, jev_result, openrouter_key):
    probs = jev_result.get("probabilities", {})
    instructions = LUNA_PROMPT_INSTRUCTIONS_TMPL.format(
        instructions=TRIAGE_INSTRUCTIONS,
        novel_prob=probs.get("novel", "?"),
        unsure_prob=probs.get("unsure", "?"),
        skip_prob=probs.get("skip", "?"),
    )
    state = build_state(item)
    payload = {
        "model": LUNA_DECISIONS_MODEL,
        "state": {"item": state},
        "questions": {
            "label": {
                "type": "choice",
                "instructions": instructions,
                "criteria": {
                    "novel": "值得发布：新产品/新技术/AI 技术更新（非设计作品）",
                    "skip": "不值得发布：闲聊/情绪/梗图/生活分享/广告/转发辩论/设计作品类内容",
                },
            }
        },
    }
    req = urllib.request.Request(
        LUNA_DECISIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        answer = body["answers"]["label"]
    except (urllib.error.URLError, KeyError, TimeoutError, json.JSONDecodeError) as e:
        return "unsure", f"Luna Decisions 调用失败，需人工复核: {e}"

    label = answer.get("choice")
    confidence = answer.get("confidence")
    if label not in ("novel", "skip"):
        return "unsure", "Luna Decisions 未能在 novel/skip 间给出有效选择，按 unsure 保留"
    return label, f"Luna Decisions 判断（置信度 {confidence}）"


def main():
    if len(sys.argv) != 2:
        print("Usage: oddly_triage.py tweets.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        items = json.load(f)

    api_key = load_jev_api_key()
    openrouter_key = load_openrouter_api_key()
    results = []

    for item in items:
        try:
            jev_result = jev_classify(item, api_key)
        except (urllib.error.URLError, KeyError, TimeoutError) as e:
            results.append(
                {"id": item.get("id"), "label": "unsure", "tier": "error",
                 "reason": f"Jev 调用失败，需人工复核: {e}"}
            )
            continue

        choice = jev_result["choice"]
        confidence = jev_result.get("confidence") or 0.0
        if choice in ("novel", "skip") and confidence >= JEV_CONFIDENCE_FLOOR:
            results.append(
                {
                    "id": item.get("id"),
                    "label": choice,
                    "tier": "jev",
                    "confidence": confidence,
                    "reason": f"Jev 判断（置信度 {confidence}）",
                }
            )
        else:
            label, reason = luna_decisions_classify(item, jev_result, openrouter_key)
            results.append(
                {"id": item.get("id"), "label": label, "tier": "luna_decisions", "reason": reason}
            )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
