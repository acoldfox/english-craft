---
name: wordtower-importer
description: 词塔（WordTower）专属语料导入助手。一站式获取英文原版杂志（经济学人等）、公有领域名著书籍（Standard Ebooks 与古登堡计划）、YouTube 视频与带时间戳字幕（对齐词塔 v0.7.0）、外媒文章，全自动导入词塔生成双语精读课程。内置依赖自动安装与 WORDTOWER_API_KEY 引导配置向导。
metadata:
  version: "1.2.0"
  homepage: "https://github.com/acoldfox/wordtower-importer"
---

# 词塔语料导入助手 (WordTower Importer)

本 Skill 是专为 [词塔（WordTower）](https://www.wordtower.cn) 打造的**多渠道外语语料导入总控中枢**。对齐词塔官方 Skill v0.7.0 规范，集成了外刊 EPUB 获取（经济学人等）、经典名著图书检索（Standard Ebooks & 古登堡）、YouTube 视频与带时间戳字幕提取、网页去噪转录，并全自动完成词塔视频/文本建课、生词生成与精读伴读流水线。

---

## 🎯 核心工作流与分工

用户只需用自然语言提出需求（如“在 Standard Ebooks 搜一下 The Great Gatsby 并导入词塔”、“把最新一期经济学人导入词塔”、“帮我把这个 YouTube 英语演讲导入词塔做成精读课程”），本 Skill 按以下流程全自动完成：

```text
[用户自然语言需求] ──► 1. 前置自检 (WORDTOWER_API_KEY 与依赖检测)
                          │
                          ▼
                       2. 多源采集 (外刊EPUB / 经典图书EPUB / YouTube SRT字幕 / 网页正文)
                          │
                          ▼
                       3. 格式规范与时间轴对齐 (保留视频同步播放与跳转)
                          │
                          ▼
                       4. 落地词塔 (自动上传建课、生成双语伴读与生词表)
```

---

## 🛠️ 第一步：前置环境与词塔 API Key 引导向导

在执行任何导入前，Agent 必须先行自检：

### 1. 词塔凭证（`WORDTOWER_API_KEY`）检测与引导
- 检查环境变量 `WORDTOWER_API_KEY`（或兼容旧版的 `WORDS_API_KEY`）是否已配置。
- **若未配置**：暂停后续步骤，以清晰、保姆级的步骤向用户引导：
  1. 提示用户前往词塔网页端或客户端的 **「账户 → Skill 与 Token」** 创建 Token（格式以 `wtk-` 开头）。
  2. 强调需勾选 `imports:text` 与 `imports:epub`（或套餐默认导入权限）。
  3. 提示用户：**“你可以直接在当前对话框把 Token 发给我，我来帮你保存；或者在终端中运行 `export WORDTOWER_API_KEY=wtk_xxx`。”**
  4. 收到 Token 后，协助将其写入本地环境变量或配置文件，并通过词塔官方接口测试连通性，然后**自动恢复之前中断的导入任务**。

### 2. 外部依赖检测与静默安装
- 若语料来源涉及 YouTube 视频，且本地未安装 `baoyu-youtube-transcript`：
  自动执行安装：
  ```bash
  npx skills add https://github.com/jimliu/baoyu-skills --skill baoyu-youtube-transcript -y
  ```
- 若语料来源涉及任意网页 URL 且未安装 `baoyu-url-to-markdown`：
  自动执行安装：
  ```bash
  npx skills add https://github.com/jimliu/baoyu-skills --skill baoyu-url-to-markdown -y
  ```

---

## 📚 第二步：多渠道语料采集与词塔对接

根据用户的输入类型，自动选择最佳采集引擎并直接调用词塔导入接口：

### 模式 A：《经济学人》及外刊（内置引擎，提取 EPUB）
无需外部依赖，直接运行本 Skill 内置的杂志获取脚本：
- **查看期数**：
  ```bash
  python3 scripts/fetch_magazine.py list [-m economist|new_yorker|atlantic|wired] [--limit 5]
  ```
- **下载指定期数或最新一期（EPUB 格式）**：
  ```bash
  python3 scripts/fetch_magazine.py download -i latest -f epub -o ./downloads/economist
  ```
- **导入词塔**：
  ```bash
  python3 .agents/skills/wordtower/scripts/request.py --epub <下载的EPUB路径> --title "The Economist 2026-11-07"
  ```
  *(注：若用户要求只导入指定章节或非政治类题材，遵循 wordtower 的本地选章脚本裁剪后再行提交)*

---

### 模式 B：经典名著图书检索与下载（Standard Ebooks & 古登堡计划）
内置对全球两大公有领域图书馆的搜索与下载支持，优先检索高质量精排版源（Standard Ebooks）：
- **检索图书**：
  ```bash
  python3 scripts/fetch_book.py search "<书名或作者>" [--source auto|standard_ebooks|gutenberg] [--limit 5]
  ```
- **下载并导入词塔**：
  ```bash
  # 下载图书 EPUB 到本地
  python3 scripts/fetch_book.py download "<书名或作者>" [--source auto|standard_ebooks|gutenberg] -o ./downloads/books

  # 提交至词塔生成书籍精读课程
  python3 .agents/skills/wordtower/scripts/request.py --epub <下载的图书EPUB路径> --title "<书籍标题>"
  ```

---

### 模式 C：YouTube 视频与带时间戳字幕导入（词塔 v0.7.0 原生支持）
词塔官方 Skill v0.7.0 原生支持 YouTube 视频课程导入，并能完整保留原视频时间轴与逐句跳转！

1. **获取带时间戳的 SRT 字幕**：
   调用 `baoyu-youtube-transcript` 导出 `.srt` 文件（例如保存到 `./downloads/subtitles/video.srt`）：
   ```bash
   npx -y bun .agents/skills/baoyu-youtube-transcript/scripts/main.ts "<YouTube-URL>" --format srt --languages en
   ```
2. **生成词塔视频课程预览（Preview）**：
   调用官方脚本，同时传入视频 URL 与字幕路径：
   ```bash
   python3 .agents/skills/wordtower/scripts/request.py --youtube "<YouTube-URL>" --subtitles "<字幕.srt路径>" --title "<视频标题>"
   ```
   *官方脚本会自动解析 SRT 时间戳（转换为 start / duration），并调用服务端的 `/imports/youtube/preview` 取得 `preview_id` 和额度报价。*
3. **提交建课任务**：
   生成随机 UUID 作为 `idempotency_key`，写入临时请求文件 `submit.json`：
   ```json
   {"api_name": "/imports/text", "preview_id": "<实际preview_id>", "idempotency_key": "<生成的UUID>"}
   ```
   执行提交：
   ```bash
   python3 .agents/skills/wordtower/scripts/request.py submit.json
   ```
4. **轮询状态并向用户反馈**：
   取得返回的 `job_id`，轮询查询状态：
   ```json
   {"api_name": "/imports/status", "job_id": "<实际job_id>"}
   ```
   当 `status` 为 `succeeded` 时，向用户汇报课程创建成功，告知该课程已保留 YouTube 播放器与同步字幕时间轴，支持句子点读与生词精读！

---

### 模式 D：外媒文章 / 博客网页 URL
1. 调用 `baoyu-url-to-markdown` 提取正文并过滤广告：
   ```bash
   npx -y bun .agents/skills/baoyu-url-to-markdown/scripts/main.ts <Web-URL>
   ```
2. 调用官方脚本导入：
   ```bash
   python3 .agents/skills/wordtower/scripts/request.py --text <清洗后的Markdown路径> --title "文章标题"
   ```

---

## 💡 常用自然语言调用示例

### 1. 经典图书检索与导入
- *“在 Standard Ebooks 搜一下《了不起的盖茨比》(The Great Gatsby) 并导入词塔”*
- *“在古登堡计划搜一下《傲慢与偏见》(Pride and Prejudice) 并导入词塔”*
- *“帮我搜《福尔摩斯探案集》电子书并导入词塔学习”*

### 2. 外刊杂志精读
- *“查看《经济学人》最近期数”*
- *“帮我把最新一期《经济学人》导入词塔学习”*
- *“下载最新一期《纽约客》EPUB 并导入词塔”*
- *“把这期《经济学人》的 Leaders 章节导入词塔”*

### 3. YouTube 视频原声伴读
- *“把这个 YouTube 英语演讲导入词塔，保留视频时间轴做成精读课程：https://www.youtube.com/watch?v=xxx”*

### 4. 外媒网页文章精读
- *“帮我把这篇文章导入词塔：https://example.com/article”*
