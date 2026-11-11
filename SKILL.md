---
name: wordtower-importer
description: 词塔（WordTower）专属语料导入助手。一站式获取《经济学人》（The Economist）等英文原版杂志（内置）、YouTube 视频字幕、外媒文章，进行格式清洗、双语对照与难度评估，并全自动导入词塔（WordTower）生成双语精读课程。内置依赖自动安装与 WORDS_API_KEY 引导配置向导。
metadata:
  version: "1.0.0"
  homepage: "https://github.com/acoldfox/wordtower-importer"
---

# 词塔语料导入助手 (WordTower Importer)

本 Skill 是专为 [词塔（WordTower）](https://wordtower.app) 打造的**多渠道外语语料导入总控中枢**。它集成了外刊下载（经济学人等）、视频字幕提取、网页去噪转录，并打通了词塔的自动建课、生词生成与精读伴读流水线。

---

## 🎯 核心工作流与分工

用户只需用自然语言提出需求（如“把最新一期经济学人导入词塔”、“帮我把这个 YouTube 英语演讲导入词塔做成精读课程”），本 Skill 按以下四步全自动完成：

```text
[用户输入] ──► 1. 前置自检 (WORDS_API_KEY 与依赖检测)
                 │
                 ▼
              2. 多源采集 (内置外刊下载 / YouTube字幕 / 网页正文)
                 │
                 ▼
              3. 排版清洗与预处理 (去除杂质、段落规范化)
                 │
                 ▼
              4. 落地词塔 (自动上传建课、生成双语伴读与生词表)
```

---

## 🛠️ 第一步：前置环境与词塔 API Key 引导向导

在执行任何导入前，Agent 必须先行自检：

### 1. 词塔凭证（`WORDS_API_KEY`）检测与引导
- 检查环境变量 `WORDS_API_KEY` 是否已配置。
- **若未配置**：暂停后续步骤，以清晰、保姆级的步骤向用户引导：
  1. 提示用户前往词塔网页端或客户端的 **「账户 → Skill 与 Token」** 创建 Token。
  2. 强调需勾选 `imports:text` 与 `imports:epub`（或套餐默认导入权限）。
  3. 提示用户：**“你可以直接在当前对话框把 Token 发给我，我来帮你保存；或者在终端中运行 `export WORDS_API_KEY=wt_xxx`。”**
  4. 收到 Token 后，协助将其写入本地环境变量或配置文件，并通过词塔的接口测试连通性，然后**自动恢复之前中断的导入任务**。

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

## 📚 第二步：多渠道语料采集

根据用户的输入类型，自动选择最佳采集引擎：

### 模式 A：《经济学人》及外刊（内置引擎）
无需外部依赖，直接运行本 Skill 内置的杂志获取脚本：
- **查看期数**：
  ```bash
  python3 scripts/fetch_magazine.py list [-m economist|new_yorker|atlantic|wired] [--limit 5]
  ```
- **下载指定期数或最新一期（默认 EPUB）**：
  ```bash
  python3 scripts/fetch_magazine.py download -i latest -f epub -o ./downloads/economist
  ```
- 脚本已内置本地代理探测（1082 / 7890 等）和国内加速镜像自动回退，确保稳定高速下载。

### 模式 B：YouTube 视频字幕
调用 `baoyu-youtube-transcript` 获取结构化文本：
```bash
npx -y bun .agents/skills/baoyu-youtube-transcript/scripts/main.ts <YouTube-URL> --languages en --format text
```

### 模式 C：外媒文章 / 博客网页 URL
调用 `baoyu-url-to-markdown` 提取正文并过滤广告：
```bash
npx -y bun .agents/skills/baoyu-url-to-markdown/scripts/main.ts <Web-URL>
```

---

## 🧹 第三步：排版清洗与生词预处理

1. **排版规范化**：
   对于抓取到的长篇字幕或网页文章，可借助 `baoyu-format-markdown` 修正断句、去除多余换行、规范标点与段落层级。
2. **双语辅助（可选）**：
   若用户希望在导入前生成高质量参考译文，可借助 `baoyu-translate` 生成段落级对照。

---

## 🚀 第四步：落地导入词塔（WordTower）

利用官方 `wordtower` 组件，直接执行导入并生成课程：

### 1. EPUB 杂志导入
```bash
python3 .agents/skills/wordtower/scripts/request.py --epub <下载的EPUB路径> --title "The Economist 2026-11-07"
```
*(注：若用户要求只导入指定章节或非政治类题材，遵循 wordtower 的本地选章脚本裁剪后再行提交)*

### 2. 文本 / Markdown / YouTube 字幕导入
```bash
python3 .agents/skills/wordtower/scripts/request.py --text <清洗后的Markdown路径> --title "视频/文章标题"
```

### 3. 查询任务状态并反馈
- 脚本返回 `job_id` 后，通过 `/imports/status` 轮询直到状态为 `succeeded`。
- 向用户反馈课程创建成功的通知，并附上阅读与伴读建议。

---

## 💡 常用自然语言调用示例

- *“帮我把最新一期的《经济学人》导入词塔。”*
- *“把这期经济学人的 Leaders 章节导入词塔学习。”*
- *“把这个 YouTube 演讲视频做成词塔精读课程：https://www.youtube.com/watch?v=xxx”*
- *“帮我把这篇文章导入词塔：https://example.com/article”*
