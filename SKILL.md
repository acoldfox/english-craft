---
name: english-craft
description: 英文语料工坊（EnglishCraft）。一站式英文原版语料策展、散装文章装订成册、词汇提炼分析、A4打印排版，并支持一键导入词塔（WordTower）生成双语伴读课程。支持《经济学人》等外刊、Standard Ebooks 与古登堡名著、AudioBook Bay 有声书、YouTube 英文字幕、外媒网页去噪长文。
metadata:
  version: "2.1.0"
  homepage: "https://github.com/acoldfox/english-craft"
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
│   • 英文有声读物：AudioBook Bay 有声书检索与免登录 Magnet 提取 │
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
2. **YouTube 提取与字幕依赖（跨平台全自动自愈）**：
   - 模块 `{baseDir}/scripts/fetch_youtube.py` 原生支持 Windows、macOS 与 Linux。
   - 当需要获取 YouTube 视频列表或下载时间戳字幕时，若系统尚未安装 `yt-dlp`，脚本内置**自动自愈机制**（自动触发 `python -m pip install -U yt-dlp` 补齐）。
   - Agent 亦可主动自检并安装（Windows: `python -m pip install -U yt-dlp` 或 `winget install yt-dlp`；macOS: `brew install yt-dlp`）。
3. **网页长文清洗（可选外部技能）**：
   - 网页长文清洗：`npx skills add https://github.com/jimliu/baoyu-skills --skill baoyu-url-to-markdown -y`

---

## 📚 第二步：功能模块与脚本调用

> **路径约定**：下方命令中的 `{baseDir}` 代表本 `SKILL.md` 所在的目录（例如 `.agents/skills/english-craft`）。执行脚本时请替换为实际路径。

### 1. 权威外刊下载 (`{baseDir}/scripts/fetch_magazine.py`)
无需任何外部依赖，自动代理穿透与镜像兜底：
```bash
# 查看外刊最新期数
python3 {baseDir}/scripts/fetch_magazine.py list [-m economist|new_yorker|atlantic|wired] [--limit 5]

# 下载最新一期或指定日期 EPUB
python3 {baseDir}/scripts/fetch_magazine.py download -m economist -i latest -o ./downloads/economist
```

### 2. 英文公版名著图书 (`{baseDir}/scripts/fetch_book.py`)
优先检索 Standard Ebooks 极客精排源，自动 fallback 至古登堡计划：
```bash
# 搜索原版书
python3 {baseDir}/scripts/fetch_book.py search "The Great Gatsby" [--limit 5]

# 下载 EPUB（支持书名、古登堡数字 ID 或图书网页 URL）
python3 {baseDir}/scripts/fetch_book.py download "The Great Gatsby" -o ./downloads/books
python3 {baseDir}/scripts/fetch_book.py download 1661 -o ./downloads/books
```

### 3. 英文有声书搜索与免登录磁力链提取 (`{baseDir}/scripts/fetch_audiobook.py`)
支持在 AudioBook Bay (`audiobookbay.lu` 及多镜像容灾) 检索无删减英文有声书，提取封面图、演播者（Narrator）、音频格式（M4B/MP3）、码率与文件大小，并通过页面 `Info Hash` 与 Tracker 列表免登录合成标准磁力链接。

- **封面展示与多结果处理策略**：
  1. **先执行带封面的搜索列表（`--markdown`）**：将脚本输出的 Markdown 表格（内含 `![封面](...)` 缩略图、编号 `[1]`/`[2]`、格式 `M4B`/`MP3`、码率、文件大小）直接展示在对话回复中，方便用户直观对比封面与不同版本。
  2. **多版本选择**：
     - 若存在多个结果且用户未指定具体版本：展示上述带封面的多版本对比表格，询问用户需要哪一个编号（或默认同时附上 `[1]` 号首选版本的磁力链，并提示用户可输入“要第 2 个”或“要 M4B 版”切换）。
     - 若用户已明确指定编号（如“第 2 个”）或格式（如“M4B 格式”）：直接通过 `--index 2` 或 `-f m4b`（或传入对应详情页 URL）提取该版本的完整演播者信息、封面与磁力链。
```bash
# 搜索有声书并输出带封面缩略图的 Markdown 对比表（可按格式 -f m4b|mp3 过滤）
python3 {baseDir}/scripts/fetch_audiobook.py search "The Great Gatsby" --limit 5 --markdown [-f m4b]

# 按编号 (--index N)、格式 (-f) 或详情 URL 提取指定版本的封面、演播者与免登录 Magnet 链接
python3 {baseDir}/scripts/fetch_audiobook.py magnet "The Great Gatsby" --index 2 --markdown [-o ./downloads/audiobooks] [--open]
```

### 4. YouTube 频道视频列表与字幕提取 (`{baseDir}/scripts/fetch_youtube.py`)
依托 `yt-dlp` 高速提取 YouTube 用户、频道 Handle（如 `@TEDEd`、`@hubermanlab`）或播放列表的完整视频清单（含封面缩略图、时长、视频链接），并支持直接抓取英文字幕或一步导入词塔：
```bash
# 获取频道视频列表（默认 10 条，支持 -n/--limit，支持富文本 Markdown 表格带封面）
python3 {baseDir}/scripts/fetch_youtube.py list @TEDEd -n 5 [--markdown] [--json]

# 便捷简写（直接跟 Handle 或用户名）
python3 {baseDir}/scripts/fetch_youtube.py @hubermanlab -n 3

# 下载指定视频的英文时间戳字幕（.srt）
python3 {baseDir}/scripts/fetch_youtube.py subtitles "https://www.youtube.com/watch?v=aDblEBU41nA" -o ./downloads/subtitles

# 一键将指定 YouTube 视频提取字幕并导入词塔生成双语阅读伴读课程
python3 {baseDir}/scripts/fetch_youtube.py wordtower "https://www.youtube.com/watch?v=aDblEBU41nA" [--title "Pepper History"]
```

### 5. 散装文章装订成册 (`{baseDir}/scripts/binder.py`)
将多篇散落的英文 Markdown 或纯文本文件，装订合成一本标准的 EPUB 3 电子书：
```bash
python3 {baseDir}/scripts/binder.py ./articles/ --title "Weekly Tech & Life Digest" -o ./downloads/digest.epub
```

### 6. 英文词频与核心词汇提取 (`{baseDir}/scripts/vocab.py`)
自动对文章、字幕或整本 EPUB 提取重点学习词汇，内置词典词形还原并自动过滤专有名词与 A1/A2 基础虚词：
```bash
# 提取前 30 个高频重点词汇及上下文例句
python3 {baseDir}/scripts/vocab.py <path-to-epub-or-md-or-srt> --top 30

# 导出为 CSV / Anki 词卡或 Markdown 词表
python3 {baseDir}/scripts/vocab.py <path> --top 50 --format csv -o ./downloads/vocab.csv
python3 {baseDir}/scripts/vocab.py <path> --top 50 --format markdown -o ./downloads/vocab.md
```

### 7. A4 打印与页边注记排版 (`{baseDir}/scripts/print_layout.py`)
生成带右侧生词边栏、文中词汇下划线标注、手写留白横线与文末词汇复习清单的 A4 打印排版 HTML（支持在浏览器中 `Cmd+P` 另存为 PDF 或直接打印）：
```bash
python3 {baseDir}/scripts/print_layout.py <path-to-md-or-epub> --title "Article Title" [--max-paragraphs 60] -o ./downloads/reading_sheet.html
```

### 8. 导出到词塔 (`{baseDir}/scripts/exporters/wordtower.py`)
完整实现词塔官方 v0.7.0 的 `Preview ➔ Submit (UUID 幂等键) ➔ Poll Status` 三步闭环（若用户仅要求预览，可附加 `--preview-only`）：
```bash
# 导出 EPUB（若用户仅需特定章节，先调用 wordtower/scripts/epub_select.py inspect & build 裁剪后再导出）
python3 {baseDir}/scripts/exporters/wordtower.py epub <path-to-epub> --title "<课程名>"

# 导出 Markdown/文本
python3 {baseDir}/scripts/exporters/wordtower.py text <path-to-md> --title "<课程名>"

# 导出带时间戳字幕的 YouTube 视频课程（支持原生一行命令建课，无需 Node/Bun）
python3 {baseDir}/scripts/fetch_youtube.py wordtower "<YouTube-URL>" [--title "<课程名>"]

# 或分步执行字幕下载与导出：
python3 {baseDir}/scripts/fetch_youtube.py subtitles "<YouTube-URL>" -o ./downloads/subtitles
python3 {baseDir}/scripts/exporters/wordtower.py youtube "<YouTube-URL>" --subtitles ./downloads/subtitles/<video-id>.en.srt --title "<课程名>"
```

---

## 💡 常用自然语言调用指令

- **查书找刊与有声书**：
  - *“帮我查一下最新一期的《经济学人》，并下载 EPUB”*
  - *“在 Standard Ebooks 上找一本《福尔摩斯探案集》”*
  - *“古登堡计划搜索 1661 电子书下载”*
  - *“在 AudioBook Bay 搜一下《了不起的盖茨比》的有声书，提取免登录磁力链接”*
  - *“帮我找一下 Stephen Fry 演播的《哈利波特》M4B 有声书磁力链接”*
- **YouTube 频道检索与字幕直通**：
  - *“帮我查一下 @TEDEd 最近更新了哪些视频，列出时长和封面”*
  - *“看下 Huberman Lab 最近的 5 期播客视频列表”*
  - *“把 @TEDEd 的最新这个视频提取字幕，并一键导入词塔建课”*
- **装订成册**：
  - *“把我这周收集的 3 篇英文文章装订成一本 EPUB 电子书”*
- **词汇分析**：
  - *“分析一下这篇《经济学人》的词汇难度，提取 30 个重点词汇做成词表”*
  - *“帮我把这本小说的生词导出成 CSV 格式”*
- **打印排版**：
  - *“把这篇文章做成适合 A4 打印的精读排版，边栏附带生词和笔记栏”*
- **词塔（WordTower）专属伴读与视频建课**：
  - *“把这个 YouTube 英语演讲和字幕一起导入词塔做成点读课程：https://youtube.com/watch?v=xxx”*
  - *“把这个油管视频导入词塔，保留播放器和同步字幕时间轴”*
  - *“帮我把最新一期《经济学人》导入词塔，生成双语伴读课程”*
  - *“在 Standard Ebooks 上找一本《了不起的盖茨比》，下载后直接导入词塔”*
  - *“从古登堡下载《福尔摩斯探案集》（#1661），导入词塔生成生词伴读课”*
  - *“把刚刚装订好的这本合订本 EPUB，一键推送到词塔建课”*
  - *“把这篇文章（https://example.com/article）清洗后导入词塔学习”*

---

## 🙏 致谢与参考来源

本项目在开发中参考并使用了以下开源项目与公开数据源，特此感谢：
- 外刊期刊：[hehonghui/awesome-english-ebooks](https://github.com/hehonghui/awesome-english-ebooks)
- 公版名著：[Standard Ebooks](https://standardebooks.org/) 与 [Project Gutenberg](https://www.gutenberg.org/)（含 [Gutendex](https://gutendex.com/) 检索支持）
- 有声读物：[AudioBook Bay](https://audiobookbay.lu/)、[Steellow/abb-get](https://github.com/Steellow/abb-get) 与 [smythp/audiobook_bay_scraper](https://github.com/smythp/audiobook_bay_scraper)
- 视频提取：[yt-dlp](https://github.com/yt-dlp/yt-dlp)
- 伴读平台：[词塔 (WordTower)](https://www.wordtower.cn)
- 转录工具：[baoyu-skills](https://github.com/jimliu/baoyu-skills)



### YouTube 同步字幕导入约束

- 视频课程必须使用 `wordtower.py youtube URL --subtitles FILE`，字幕只接受带真实起止时间的 SRT/VTT 或官方 timed JSON。不得把字幕转 Markdown 后用 `text` 导入，也不得在字幕获取失败时降级成纯文本建课。
- 正文只含字幕，不插入视频标题、简介、总结或翻译；这些内容会破坏字幕与正文的对应关系。标题通过 `--title` 指定。
- 提交前脚本必须验证服务端预览的 `media_type=youtube`、`source_url` 和正数 `subtitle_count`；不满足即停止，不提交课程。
- 找不到最新版官方技能时，可设置 `WORDTOWER_REQUEST_SCRIPT=/absolute/path/wordtower/scripts/request.py`。该脚本须与同包 `config.json` 配套，并支持 `--youtube`、`--subtitles` 与当前 Token 协议。不要修改 API 地址或降级使用旧技能。
- SRT 提供字幕片段级时间轴，与 App 的句子级高亮能力一致；它不包含真实逐词对齐，不得伪造均分单词时间。
- 已经以纯文本导入的历史课程不会被自动修复；应重新使用原始时间字幕导入，不从正文猜测时间戳。
