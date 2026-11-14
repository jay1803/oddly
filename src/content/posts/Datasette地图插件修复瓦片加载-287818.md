---
title: "Datasette地图插件修复瓦片加载"
date: 2026-11-14
category: "tool"
description: "datasette-leaflet 0.3 修复了 Datasette 表格页面加载 OpenStreetMap 地图瓦片时的来源标头问题。"
source: "https://simonwillison.net/2026/Nov/13/datasette-leaflet/"
author: "Simon Willison"
---

datasette-leaflet 是为 Datasette 提供地图展示功能的插件。0.3 版本调整了页面的 Referrer-Policy，使 OpenStreetMap 瓦片服务器能够收到所需的来源标头。
