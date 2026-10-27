---
title: "Claude Code新增彻底跳过权限开关"
date: 2026-10-27
category: tool
description: "Claude Code新增环境变量，可关闭危险跳过权限模式下对部分命令的拦截，进一步放宽执行限制。"
tweet_url: "https://x.com/The_Whole_Daisy/status/2114796466850202103"
author: "Daisy Hollman"
---

此前，即使启用 `--dangerously-skip-permissions`，工具仍会拦截 `rm -rf ~` 等明显危险操作。推文称今日发布将允许用户通过设置 `CLAUDE_CODE_EVEN_MORE_DANGEROUSLY_SKIP_PERMISSIONS=1` 关闭这层限制。
