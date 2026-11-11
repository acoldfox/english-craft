# 🗼 WordTower Importer (`wordtower-importer`)

> 词塔（WordTower）专属语料导入助手。一键将《经济学人》等优质外刊、YouTube 视频字幕、外媒文章等多种渠道素材清洗、对齐并导入词塔生成双语精读课程。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Skills.sh](https://img.shields.io/badge/skills.sh-compatible-success.svg)](https://skills.sh)

---

## ✨ 核心特性

- 🎬 **YouTube 视频与时间戳字幕原生导入（官方 v0.7.0 对齐）**：原生支持词塔 v0.7.0 视频课程规范！一键提取 YouTube 视频字幕（SRT/VTT/JSON），导入词塔后**完美保留原视频播放器与逐句时间轴跳转**，实现点句跟读与原声伴读。
- 📰 **外刊精读一键导入**：内置《经济学人》（The Economist）、《纽约客》（The New Yorker）、《大西洋月刊》（The Atlantic）、《连线》（WIRED）等优质外刊获取引擎，自动下载 EPUB 原版并导入词塔。
- 🌐 **外媒博文网页转录**：任意英文网页/博客一键去噪，剥离广告提取纯净正文导入词塔。
- 🧹 **智能排版与双语对照**：自动化段落规整、去噪清洗，支持生成地道参考译文与术语对齐。
- 🚀 **词塔（WordTower）全自动建课**：一键上传生成词塔精读课程，提取核心生词，无缝开启 AI 伴读。
- 🧭 **保姆级向导机制**：智能检测环境，引导用户配置 `WORDTOWER_API_KEY`，支持全自动补齐外部依赖。

---

## 📦 安装方法

本项目遵循开放 Agent Skills 规范，可一键安装到任何支持 Skills 的 AI 客户端（如 Google Antigravity、Cursor、Claude Code、Amp、Cline 等）：

```bash
# 全局安装（所有项目可用）
npx skills add acoldfox/wordtower-importer -g -y

# 或在当前项目中安装
npx skills add acoldfox/wordtower-importer -y
```

---

## 💡 使用方法

安装完成后，在 AI 对话框中**直接使用自然语言**提出需求，Agent 即可全自动处理：

### 1. YouTube 视频字幕学习（原生时间轴保留）
- **视频转精读课程**：
  > “把这个 YouTube 英语演讲导入词塔做成精读课程：`https://youtube.com/watch?v=xxxx`”  
  > “把这个 YouTube 视频和英文字幕导入词塔，保留时间轴”

### 2. 外刊杂志精读
- **查看期数**：
  > “查看《经济学人》最近期数”  
  > “查看《纽约客》最近期数”
- **下载并导入最新期**：
  > “帮我把最新一期《经济学人》导入词塔学习”  
  > “下载最新一期《纽约客》EPUB 并导入词塔”
- **指定章节导入**：
  > “把这期《经济学人》的 Leaders 章节导入词塔”

### 3. 外媒网页文章精读
- **网页文章转录**：
  > “把这篇 TechCrunch 科技报道导入词塔：`https://techcrunch.com/xxxx`”

---

## 🔑 词塔 API Key 配置指南

导入词塔课程需要配置 `WORDTOWER_API_KEY`（词塔官方 v0.7.0 凭证）：

1. 前往词塔官方平台（[WordTower](https://wordtower.app)），进入 **「账户 → Skill 与 Token」**。
2. 创建一个 Token（前缀为 `wtk-`），确保勾选导入权限（`imports:text` 与 `imports:epub`）。
3. 在终端设置环境变量：
   ```bash
   export WORDTOWER_API_KEY=wtk_xxxxxxxxxxxxxxxx
   ```
   *(或者在使用 Agent 时，直接将 Token 发送给 Agent 协助自动配置)*。

---

## 🙏 致谢与开源生态 (Credits & Data Sources)

本项目作为中枢调度器，离不开以下优秀开源项目的贡献，特此致谢：

- **词塔官方生态**：[word-tower/skills](https://github.com/word-tower/skills) 提供的官方 API 调用网关与 v0.7.0 视频字幕课程规范。
- **电子书与外刊源**：[hehonghui/awesome-english-ebooks](https://github.com/hehonghui/awesome-english-ebooks) 提供的定期更新与归档。
- **视频与文本提取方案**：[jimliu/baoyu-skills](https://github.com/jimliu/baoyu-skills) 提供的优质字幕与网页转录组件。

---

## ⚠️ 免责声明 (Disclaimer)

1. 本项目仅为方便个人外语学习、阅读研究而开发的自动化辅助工具。
2. 本项目仓库本身不存储、不修改、不分发任何受版权保护的期刊书籍原文件。所有数据均来自于网络公开第三方仓库。
3. 所涉期刊（如 *The Economist*, *The New Yorker* 等）版权均归原出版方所有，请支持正版订阅。

---

## 📄 开源许可证

本项目采用 [MIT 许可证](LICENSE)。
