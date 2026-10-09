#!/usr/bin/env python3
"""Two-tier oddly triage classifier: Jev (fast, cheap) -> gpt-6-luna (semantic fallback).

Mirrors feedbin-cli's jev_triage.py pattern (see that skill + the
hermes-model-delegation skill) but for a binary novel/skip decision instead
of star/skip/unsure.

Tier 1 (Jev): every candidate tweet gets a single `choice` question
(novel/skip) in well under a second each. Low-confidence answers are
escalated.

Tier 2 (gpt-6-luna via `hermes chat`): only items Jev was unsure about
(or answered with low confidence). Luna must commit to novel/skip, no
unsure allowed.

Usage:
    python3 oddly_triage.py tweets.json > results.json

tweets.json is a JSON array of objects, each with at minimum:
    {"id": "...", "author": "...", "handle": "...", "text": "...",
     "url": "...", "isRetweet": false}

Output is a JSON array of:
    {"id": ..., "label": "novel"|"skip", "tier": "jev"|"luna"|"error", "reason": "..."}

Requires:
- ~/.config/jev/.env.local with API_KEY=... (TypeSafe/Jev API key)
- hermes CLI reachable at $HERMES_BIN with openai-codex auth configured
  for gpt-6-luna (see hermes-model-delegation skill)
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

JEV_ENV_FILE = os.environ.get("JEV_ENV_FILE", os.path.expanduser("~/.config/jev/.env.local"))
HERMES_BIN = os.environ.get(
    "HERMES_BIN", os.path.expanduser("~/.hermes/hermes-agent/venv/bin/hermes")
)
LUNA_MODEL = os.environ.get("LUNA_MODEL", "gpt-6-luna")
LUNA_PROVIDER = os.environ.get("LUNA_PROVIDER", "openai-codex")

JEV_API_URL = "https://api.typesafe.ai/v1/systemone"

# Same reasoning as feedbin-cli's jev_triage.py: Jev's choice sampling can
# emit a confident-looking novel/skip on borderline items when it should
# really say unsure. Treat low confidence as unsure and escalate.
JEV_CONFIDENCE_FLOOR = float(os.environ.get("JEV_CONFIDENCE_FLOOR", "0.6"))

# Kept in sync with references/triage-rules.md — if you edit the rules
# there, update this instructions string too (and vice versa).
TRIAGE_INSTRUCTIONS = (
    "判断这条推文是否是「新奇的东西」：新产品发布、新功能上线、新 AI 模型"
    "发布或重要 benchmark 突破、有意思的开源工具/小项目，或让人'诶这个有点"
    "意思'的新点子/新角度。标准是好奇心驱动，不要求严格落在产品/模型范畴，"
    "但必须是新的东西或新的信息，不是单纯观点、情绪、梗图、日常生活分享、"
    "广告、政治社会评论或对他人观点的转发辩论。"
    "转推（isRetweet=true）默认优先级降低，但如果转推内容本身是官方账号发布"
    "的产品/模型消息，仍可判 novel。"
    "官方科技公司账号（OpenAI、Anthropic、Google DeepMind 等）的产品/模型"
    "发布默认倾向 novel，除非纯营销话术没有实质信息。"
    "无实质文本、仅图片无说明的默认 skip。"
)

LUNA_PROMPT_TMPL = """你是 oddly 新奇发现筛选器的第二级裁判。这条推文被第一级快速分类器（Jev）标记为 unsure，现在需要你结合语义理解做最终判断：novel 或 skip（只能二选一，不能再回答 unsure）。

## 判断标准
{instructions}

## 待判断推文
ID: {id}
作者: {author} ({handle})
是否转推: {is_retweet}
正文: {text}

## Jev 第一级判断（供参考）
novel 概率: {novel_prob}, unsure 概率: {unsure_prob}, skip 概率: {skip_prob}

只输出严格 JSON，不要任何其他文字：{{"label": "novel|skip", "reason": "一句话中文理由"}}"""


def load_jev_api_key():
    if not os.path.exists(JEV_ENV_FILE):
        raise RuntimeError(f"Jev credentials file not found: {JEV_ENV_FILE}")
    with open(JEV_ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line.startswith("API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError(f"API_KEY not found in {JEV_ENV_FILE}")


def jev_classify(item, api_key):
    state = (
        f"作者: {item.get('author', '')} ({item.get('handle', '')})\n"
        f"是否转推: {item.get('isRetweet', False)}\n"
        f"正文: {item.get('text', '')}"
    )
    payload = {
        "state": state,
        "model": "jev-latest",
        "questions": {
            "label": {
                "type": "choice",
                "instructions": TRIAGE_INSTRUCTIONS,
                "criteria": {
                    "novel": "高置信度新奇：新产品/新模型/新工具/新点子",
                    "skip": "高置信度不新奇：闲聊/情绪/梗图/生活分享/广告/转发辩论",
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


def luna_classify(item, jev_result):
    probs = jev_result.get("probabilities", {})
    prompt = LUNA_PROMPT_TMPL.format(
        instructions=TRIAGE_INSTRUCTIONS,
        id=item.get("id"),
        author=item.get("author", ""),
        handle=item.get("handle", ""),
        is_retweet=item.get("isRetweet", False),
        text=item.get("text", ""),
        novel_prob=probs.get("novel", "?"),
        unsure_prob=probs.get("unsure", "?"),
        skip_prob=probs.get("skip", "?"),
    )
    result = subprocess.run(
        [HERMES_BIN, "chat", "-q", prompt, "-m", LUNA_MODEL, "--provider", LUNA_PROVIDER, "-t", "", "-Q"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = result.stdout.strip()
    lines = [l for l in out.split("\n") if not l.startswith("session_id:")]
    answer_text = "\n".join(lines).strip()
    try:
        parsed = json.loads(answer_text)
        label = parsed.get("label", "unsure")
        reason = parsed.get("reason", "")
    except json.JSONDecodeError:
        return "unsure", f"luna 返回非 JSON，需人工复核: {answer_text[:200]}"

    if label not in ("novel", "skip"):
        return "unsure", reason or "Luna 仍无法在 novel/skip 间做出判断，按 unsure 保留"
    return label, reason


def main():
    if len(sys.argv) != 2:
        print("Usage: oddly_triage.py tweets.json", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        items = json.load(f)

    api_key = load_jev_api_key()
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
            label, reason = luna_classify(item, jev_result)
            results.append(
                {"id": item.get("id"), "label": label, "tier": "luna", "reason": reason}
            )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
