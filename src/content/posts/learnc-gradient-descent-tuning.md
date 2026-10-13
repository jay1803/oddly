---
title: "让梯度下降自动调优 C 代码常数"
date: 2026-10-13T04:05:00Z
category: tool
description: "learnc 将 C 代码中手工设定的阈值、权重等常数交给梯度下降优化，并生成修改后的同一份 C 文件，无需在生产环境引入新依赖。"
tweet_url: "https://x.com/yibie/status/2109857006605763002"
author: "yibie"
---

这项工具针对的是代码库中常见的"魔法数字"，尝试用自动搜索替代人工反复调参。项目作者 Anmol Sharma 也开发过 decidr。
