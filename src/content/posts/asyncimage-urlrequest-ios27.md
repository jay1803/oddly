---
title: "AsyncImage 开放远程加载控制"
date: 2026-11-16
category: tool
description: "iOS 27 为 SwiftUI 的 AsyncImage 增加 URLRequest 与自定义 URLSession 支持，让开发者能配置远程图片请求和加载策略。"
tweet_url: "https://x.com/NilCoalescing/status/2122076464481030261"
author: "Nil Coalescing"
---

URLRequest 可用于设置自定义请求头、缓存策略和超时；自定义 URLSession 则可沿 SwiftUI 视图层级提供。
