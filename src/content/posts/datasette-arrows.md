---
title: "Datasette 插件支持 Arrow 流式导出"
date: 2026-11-19
category: tool
description: "datasette-arrows 是 Datasette 插件，利用流式导出能力将表格数据导出为 Apache Arrow 格式。"
source: "https://simonwillison.net/2026/Nov/18/datasette-arrows/"
author: "Simon Willison"
---

它让 Datasette 能以流式方式导出 Arrow 数据，适合导出大型数据表，无需一次性将全部内容载入内存。
