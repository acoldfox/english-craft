---
name: english-craft
description: 英文语料工坊（EnglishCraft）。一站式英文原版语料策展、散装文章装订成册、词汇提炼分析、A4打印排版，并支持一键导入词塔（WordTower）生成双语伴读课程。支持《经济学人》等外刊、Standard Ebooks 与古登堡名著、YouTube 英文字幕、外媒网页去噪长文。
metadata:
  version: "2.0.0"
  homepage: "https://github.com/acoldfox/wordtower-importer"
---

# 英文语料工坊 (EnglishCraft)

**EnglishCraft** 是专为英文原版学习者打造的**个人原版语料策展、装订排印与词汇工坊**。

它解决了传统英文阅读的三大痛点：**找书难（好源分散）、读懂难（生词零碎未提前梳理）、精读难（散篇无处装订，缺少打印做笔记的排版）**。无论是用于纸质精读、Kindle 墨水屏阅读，还是一键导入**词塔（WordTower）**生成双语伴读课程，EnglishCraft 提供完整的流水线支持。

---

## 🎯 核心工作流能力

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. 纯正英文原版语料检索与获取 (Find)                         │
│   • 国际权威外刊：《经济学人》《纽约客》《大西洋月刊》《连线》     │
│   • 公版原著图书：Standard Ebooks 极客精排源、Project Gutenberg │
│   • 现代多模态：YouTube 英文原声与时间戳字幕、外媒去噪长文   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 2. 深度工坊加工与词汇工程 (Craft & Analyze)                 │
│   • 散篇装订成册 (Binder)：将散装 Markdown/文章组装成标准 EPUB│
│   • 词频与生词提炼 (Vocab)：自动过滤停用词，提取考研/雅思核心词 │
│   • A4 印刷精排 (Print Layout)：生成带右侧边栏生词注记的排版  │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│ 3. 多端输出与分发 (Export & Study)                          │
│   • 📄 纸质精读：A4 双栏打印版（带打卡复习勾选框与手写留白）    │
│   • 📱 电子墨水屏：标准 EPUB 电子书（适用 Kindle / Apple Books）│
│   • 📇 复习卡包：CSV / Markdown 词表（可导入 Anki）          │
│   • 🗼 词塔对接 (WordTower)：一键构建 AI 点读课与句子点读课程 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 第一步：前置环境与依赖检测

在执行相关任务时，Agent 根据用户意图自检依赖：

1. **词塔连通性（可选，仅当用户要求导入词塔时才触发）**：
   - 检查 `WORDTOWER_API_KEY`（或 `WORDS_API_KEY`）是否已配置。
   - 若用户要求导词塔但未配置：引导用户在 [词塔网页端](https://www.wordtower.cn) 创建 Token（格式以 `wtk-` 开头），并协助配置连通。
2. **外部转录依赖（仅当涉及 YouTube 或网页爬取时自动安装）**：
   - YouTube 字幕：`npx skills add https://github.com/jimliu/baoyu-skills --skill baoyu-youtube-transcript -y`
   - 网页长文清洗：`npx skills add https://github.com/jimliu/baoyu-skills --skill baoyu-url-to-markdown -y`

---

## 📚 第二步：功能模块与脚本调用

### 1. 权威外刊下载 (`scripts/fetch_magazine.py`)
无需任何外部依赖，自动代理穿透与镜像兜底：
```bash
# 查看外刊最新期数
python3 scripts/fetch_magazine.py list [-m economist|new_yorker|atlantic|wired] [--limit 5]

# 下载最新一期或指定日期 EPUB
python3 scripts/fetch_magazine.py download -m economist -i latest -o ./downloads/economist
```

### 2. 英文公版名著图书 (`scripts/fetch_book.py`)
优先检索 Standard Ebooks 极客精排源，自动 fallback 至古登堡计划：
```bash
# 搜索原版书
python3 scripts/fetch_book.py search "The Great Gatsby" [--limit 5]

# 下载 EPUB（支持书名、古登堡数字 ID 或图书网页 URL）
python3 scripts/fetch_book.py download "The Great Gatsby" -o ./downloads/books
python3 scripts/fetch_book.py download 1661 -o ./downloads/books
```

### 3. 散装文章装订成册 (`scripts/binder.py`)
将多篇散落的英文 Markdown 或纯文本文件，装订合成一本标准的 EPUB 3 电子书：
```bash
python3 scripts/binder.py ./articles/ --title "Weekly Tech & Life Digest" -o ./downloads/digest.epub
```

### 4. 英文词频与核心词汇提取 (`scripts/vocab.py`)
自动对文章或整本 EPUB 提取重点词汇，支持词形还原并过滤初中常见虚词：
```bash
# 提取前 30 个高频重点词汇及上下文例句
python3 scripts/vocab.py <path-to-epub-or-md> --top 30

# 导出为 CSV / Anki 词卡或 Markdown 词表
python3 scripts/vocab.py <path> --top 50 --format csv -o ./downloads/vocab.csv
python3 scripts/vocab.py <path> --top 50 --format markdown -o ./downloads/vocab.md
```

### 5. A4 打印与页边注记排版 (`scripts/print_layout.py`)
生成带右侧生词边栏、手写留白横线与文末词汇复习清单的 A4 打印排版 HTML（支持在浏览器中 `Cmd+P` 另存为 PDF 或直接打印）：
```bash
python3 scripts/print_layout.py <path-to-md-or-epub> --title "Article Title" -o ./downloads/reading_sheet.html
```

### 6. 导出到词塔 (`scripts/exporters/wordtower.py`)
将采集或装订好的语料一键推送到词塔平台：
```bash
# 导出 EPUB
python3 scripts/exporters/wordtower.py epub <path-to-epub> --title "<课程名>"

# 导出 Markdown/文本
python3 scripts/exporters/wordtower.py text <path-to-md> --title "<课程名>"

# 导出带时间戳字幕的 YouTube 视频课程
python3 scripts/exporters/wordtower.py youtube "<YouTube-URL>" --subtitles <字幕.srt路径> --title "<课程名>"
```

---

## 💡 常用自然语言调用指令

- **查书找刊**：
  - *“帮我查一下最新一期的《经济学人》，并下载 EPUB”*
  - *“在 Standard Ebooks 上找一本《福尔摩斯探案集》”*
  - *“古登堡计划搜索 1661 电子书下载”*
- **装订成册**：
  - *“把我这周收集的 3 篇英文文章装订成一本 EPUB 电子书”*
- **词汇分析**：
  - *“分析一下这篇《经济学人》的词汇难度，提取 30 个重点词汇做成词表”*
  - *“帮我把这本小说的生词导出成 CSV 格式”*
- **打印排版**：
  - *“把这篇文章做成适合 A4 打印的精读排版，边栏附带生词和笔记栏”*
- **词塔对接**：
  - *“把下载好的这本书导入词塔生成精读课程”*
  - *“把这个 YouTube 英语演讲和字幕一起导入词塔做成点读课程”*
