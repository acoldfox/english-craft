# EnglishCraft (英文语料工坊)

<p align="center">
  <strong>一站式英文原版语料策展、散装文章装订成册、词汇提炼分析与 A4 打印排版工坊</strong><br>
  <em>Personal English Corpus Workshop: Find, Bind, Analyze, Print & Export</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License MIT">
  <img src="https://img.shields.io/badge/Skill-OpenAgent-orange.svg" alt="Open Agent Skill">
  <img src="https://img.shields.io/badge/Zero-External%20Deps-brightgreen.svg" alt="Zero External Dependencies">
</p>

---

## 📖 为什么需要 EnglishCraft？

在日常学习英文、精读原版时，英语学习者常面临以下困扰：

1. **原版资源分散且割裂**：想找优质外刊（《经济学人》《纽约客》）往往被各种复杂的爬虫或登录墙阻挡；经典名著要么排版粗糙（古登堡旧扫描版），要么缺少精排源。
2. **生词零碎未提前梳理**：拿到一篇好文章直接硬啃，遇到大量生词反复查字典打断思路，缺少阅读前后的核心词频清单。
3. **散篇好文无处安放**：在网上收藏了多篇优秀外媒专栏或博文，散落在不同文件夹，无法装订成合集推送到墨水屏或阅读器。
4. **纸质阅读排版差**：直接网页打印字号拥挤，没有留白，没有边栏生词批注区。

**EnglishCraft** 专为解决上述痛点而设计。它既是一个**功能完整的命令行工具集**，也是一个**开箱即用的 AI Agent 专属技能 (Skill)**。

---

## ✨ 核心特性

- 🔍 **全源英文语料采集 (Find)**
  - **权威外刊**：直连《经济学人》（The Economist）、《纽约客》（The New Yorker）、《大西洋月刊》（The Atlantic）、《连线》（WIRED）高品质 EPUB，内置自动代理与镜像容灾。
  - **公版经典名著**：优先检索 **Standard Ebooks** 极客精排源，自动 fallback 至 **Project Gutenberg**（古登堡计划），支持书名、作者、数字 ID 与 URL 直下。
  - **英文有声读物**：支持 **AudioBook Bay (ABB)** 无删减有声书检索（含演播者、M4B/MP3 格式与码率解析），基于 Info Hash 与 Tracker 列表**免登录直接生成磁力链接 (Magnet Link)**。
  - **现代多模态**：支持 YouTube 英文演讲与带时间戳字幕（SRT）采集，支持任意网页外媒长文去噪正文提取。
- 📚 **散装文章装订成册 (Bind)**
  - 内置 EPUB 3 零依赖打包引擎，将多篇散落的 Markdown / TXT 文章或章节，一键编译成标准的 EPUB 电子书，生成合规目录（TOC），直接推送到 Kindle 或 Apple Books。
- 📊 **词频与核心生词提炼 (Vocab)**
  - 自动分析全文词汇丰富度（Lexical Diversity）与总词数。
  - 词形还原（Lemmatization），过滤英文基础功能虚词（Stopwords），按词频提取考研/雅思/托福核心高频词，并附带原文上下文例句。
  - 支持输出为表格、Markdown 词表或 Anki / CSV 词卡。
- 🖨️ **A4 纸质精读排版 (Print Layout)**
  - 生成专为打印设计的 A4 HTML 页面：**左侧正文 + 右侧边栏生词与手写批注线 + 文末生词复习打卡清单**。
  - 浏览器按 `Cmd + P` / `Ctrl + P` 即可一键输出高颜值 A4 打印纸或保存为 PDF。
- 🗼 **生态对接：词塔导出适配 (Export to WordTower)**
  - 采集或装订的任意语料，均可一键推送到 [词塔（WordTower）](https://www.wordtower.cn) 生成双语伴读课程，保留原视频时间轴与逐句点读功能。

---

## 🤖 安装与使用方式

本项目专为 AI Agent（Antigravity、Claude Code、Cursor 等）设计，用户**无需手动敲击复杂的命令行**，安装技能后，直接在聊天框中使用自然语言下达指令，Agent 会自动调用对应工具完成流水线作业。

### 1. 安装 Skill

在你的 AI 客户端或工作区中安装本技能：
```bash
npx skills add https://github.com/acoldfox/english-craft -y
```
*(或将本仓库克隆至你的 Agent 技能目录，如 `.agents/skills/english-craft`)*

---

### 2. 💬 常用自然语言指令示例

安装完成后，你只需像与助教沟通一样对 AI 提出需求：

#### 📖 1. 查找与下载英文语料（外刊 / 名著 / 有声书）
- *“帮我查一下这周最新一期的《经济学人》，并下载 EPUB。”*
- *“在 Standard Ebooks 上找一本排版精美的《了不起的盖茨比》。”*
- *“在古登堡计划搜一下《福尔摩斯探案集》（或直接下载 #1661）。”*
- *“在 AudioBook Bay 搜一下《了不起的盖茨比》的有声书，帮我提取免登录磁力链接。”*
- *“找一下 Stephen Fry 演播的《哈利波特》M4B 格式有声书。”*
- *“帮我下载这个 YouTube 英文演讲和带时间戳的字幕：https://youtube.com/watch?v=xxx”*

#### 📚 2. 散装好文装订成册 (EPUB)
- *“把我这周收集在 `articles/` 文件夹里的 3 篇外媒文章装订成一本 EPUB 电子书，书名叫《本周精选》。”*
- *“把这篇长文网页提取正文，并做成可以在 Kindle 上看的电子书。”*

#### 📊 3. 词频分析与生词提炼
- *“分析一下刚下载的这篇《经济学人》文章，提取前 30 个核心重点词汇并附带原句摘录。”*
- *“帮我把这本小说的生词表导出为 Anki / CSV 格式，方便我复习。”*

#### 🖨️ 4. A4 打印与页边手写批注排版
- *“把这篇文章排版成适合 A4 打印的精读版，右侧边栏帮我留出对应段落的生词和手写笔记横线。”*
- *“生成打印排版，文末要带打卡复习勾选框清单。”*

#### 🗼 5. 词塔（WordTower）专属双语伴读与互动课程
EnglishCraft 深度集成了 [词塔（WordTower）](https://www.wordtower.cn)，采集或装订的语料均可一键转为具备句子点读、生词联想与视频同步播放的精读课：
- **YouTube 视频原声伴读**：
  - *“把这个 TED 英文演讲导入词塔，保留播放器与原声时间轴做成精读课程：https://youtube.com/watch?v=xxx”*
  - *“帮我把这个油管科技博主的视频和字幕提取出来，一键同步到词塔跟读打卡。”*
  - *“把这段 YouTube 英语访谈导入词塔做成点读课。”*
- **外刊与原版图书建课**：
  - *“帮我把最新一期《经济学人》导入词塔，做成双语精读课程。”*
  - *“在 Standard Ebooks 上找《了不起的盖茨比》，下载后直接推送到词塔。”*
  - *“从古登堡下载《福尔摩斯探案集》（#1661），导入词塔生成生词伴读课。”*
- **散篇与网页文章转课程**：
  - *“把刚刚装订好的这本《本周精选》EPUB，一键推送到词塔。”*
  - *“帮我提取这篇外媒长文（https://example.com/article）的正文，直接导入词塔学习。”*
  *(注：若需导入词塔，首次使用时可在对话框中直接将你的 `WORDTOWER_API_KEY` 发给 AI，Agent 会协助自动配置)*

---

## 📂 项目结构

```text
english-craft/
├── SKILL.md                   # Agent Skill 规范定义与自动化编排
├── README.md                  # 项目使用指南与设计文档
├── scripts/
│   ├── fetch_magazine.py      # 外刊采集引擎（经济学人/纽约客/大西洋/连线）
│   ├── fetch_book.py          # 经典名著检索（Standard Ebooks & 古登堡）
│   ├── fetch_audiobook.py     # 有声书检索与免登录磁力链提取（AudioBook Bay）
│   ├── binder.py              # 散篇文章装订成册（标准 EPUB 3 打包器）
│   ├── vocab.py               # 英文词频与重点词汇提炼分析器
│   ├── print_layout.py        # A4 打印版式与边栏生词排印器
│   ├── tree_snapshot.json     # GitHub API 限流兜底快照
│   └── exporters/
│       └── wordtower.py       # 词塔生态桥接导出器
└── downloads/                 # 默认下载与生成产物目录
```

---

## 🙏 致谢与参考来源 (Credits & Sources)

本项目在开发过程中参考并使用了以下开源项目与公开数据源，特此感谢：

- **[awesome-english-ebooks](https://github.com/hehonghui/awesome-english-ebooks)** (by [@hehonghui](https://github.com/hehonghui))：提供外刊期刊数据整理与更新（《经济学人》《纽约客》《大西洋月刊》《连线》）。
- **[Standard Ebooks](https://standardebooks.org/)**：提供排版精美、校对规范的公有领域英文名著电子书源。
- **[Project Gutenberg](https://www.gutenberg.org/)** 与 **[Gutendex](https://gutendex.com/)**：提供公有领域名著藏书与检索接口。
- **[AudioBook Bay](https://audiobookbay.lu/)**、**[Steellow/abb-get](https://github.com/Steellow/abb-get)** 与 **[smythp/audiobook_bay_scraper](https://github.com/smythp/audiobook_bay_scraper)**：提供英文有声书检索与 Info Hash 免登录磁力链构建参考。
- **[词塔 (WordTower)](https://www.wordtower.cn)**：提供语境精读、生词学习与课程构建支持。
- **[baoyu-skills](https://github.com/jimliu/baoyu-skills)** (by [@jimliu](https://github.com/jimliu))：提供 YouTube 字幕提取与网页正文清洗组件。

---

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。
