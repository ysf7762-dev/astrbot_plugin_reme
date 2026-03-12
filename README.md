# 🧠 AstrBot ReMe 长期记忆中枢

[![AstrBot](https://img.shields.io/badge/AstrBot-Plugin-brightgreen)](https://github.com/Soulter/AstrBot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

这是一个基于 [ReMe](https://github.com/agentscope-ai/ReMe) 和 [CoPaw](https://github.com/agentscope-ai/CoPaw) 架构思想，为 **AstrBot** 深度定制的工业级长期记忆插件。

它通过 **“冷热分离存储”** 和 **“多维记忆精炼”** 技术，让 AI 能够伴随用户成长，真正记住跨度长达数年的宝宝生活点滴、办公室工作方法以及复杂的专业工具逻辑。

---

## ✨ 核心特性

### 1. 🌡️ 冷热分离存储架构
*   **热记忆 (Hot Memory)**：存储在 `PROFILE.md`、`SOUL.md` 等 Markdown 文件中，每次对话必读，确保 AI 的身份认知和用户核心画像永远在线。
*   **冷记忆 (Cold Memory)**：基于 **ChromaDB** 向量数据库，存储海量的历史对话摘要和碎片化事实。支持跨年度的语义检索。

### 2. 🤖 智能记忆代谢 (Metabolism)
*   **自动压缩 (Auto-Compaction)**：当对话上下文超过阈值（默认 8000 Tokens）时，系统自动在后台异步生成摘要并存入冷记忆，彻底解决“爆 Token”导致的失忆。
*   **画像精炼 (Refinement)**：AI 会在对话中主动调用工具，不断更新和修正 `PROFILE.md` 中的信息，让 AI 越来越懂你。

### 3. 🛠️ 多维记忆管理
*   **个人记忆 (Personal)**：记录宝宝的成长历程、健康状况及家庭趣事。
*   **程序性记忆 (Procedural)**：记录工作方法论、SOP 流程及避坑教训。
*   **工具记忆 (Tool)**：记录专业软件（如 CAD、编程环境）的配置参数与操作逻辑。

### 4. 🌅 仪式感引导 (Bootstrap)
*   **觉醒仪式**：新用户首次使用时触发引导脚本，AI 会主动询问并建立初始档案，任务完成后引导脚本“阅后即焚”。

---

## 🛠️ 安装依赖

在使用前，请确保在你的环境或虚拟环境中安装了必要的支持库：

```bash
pip install chromadb tiktoken sentence-transformers
```

> **注意**：初次启动时，系统会自动下载 `all-MiniLM-L6-v2` 句向量模型（约 80MB），用于本地语义检索。

---

## 🚀 快速开始

1.  **安装插件**：将本仓库克隆至 AstrBot 的 `data/plugins/` 目录下。
2.  **启动仪式**：重启 AstrBot，AI 会自动初始化模板文件。
3.  **初次对话**：
    *   **用户**：“你好。”
    *   **小小七**：“嘿！我刚上线。我是谁？你是谁？... (进入引导模式)”
4.  **建立记忆**：
    *   **用户**：“我宝宝今天学会叫爸爸了，他特别喜欢吃草莓。”
    *   **AI**：(后台自动调用 `update_profile`) “太棒了！我已经记下了这个里程碑，还有宝宝对草莓的偏好。”

---

## 🔧 提供工具 (Agent Tools)

插件向大模型暴露出以下强力工具，大模型会根据语境自动调用：

*   `search_memory(query)`: 语义检索长期记忆和每日笔记。
*   `update_profile(new_facts)`: 智能精炼并更新核心画像。
*   `extract_experience(experience, when_to_use, tags)`: 沉淀专业的工作流程与操作经验。
*   `finish_bootstrap()`: 结束引导仪式并切换至正式工作状态。

---

## 📂 目录结构 (plugin_data)

所有记忆数据均保存在 `data/plugin_data/astrbot_plugin_reme` 目录下，极其方便备份与迁移：

```text
├── chroma_db/            # 冷记忆向量数据库
└── {user_id}/            # 用户隔离目录
    ├── SOUL.md           # AI 性格设定 (可手动编辑)
    ├── PROFILE.md        # 用户核心画像 (AI 自动精炼)
    ├── AGENTS.md         # 行为准则 (Workspace)
    ├── MEMORY.md         # 工具备忘录
    └── memory/           # 每日原始记录 (.md)
```

---

## 🤝 贡献与反馈

如果你有任何建议，欢迎提交 Issue 或 Pull Request。

*   **作者**: [ysf7762](https://github.com/ysf7762-dev)
*   **核心逻辑引用**: [ReMe Project](https://github.com/agentscope-ai/ReMe) & [AgentScope](https://github.com/modelscope/agentscope)

---

## 📄 开源协议

本项目基于 **MIT License** 协议开源。

---