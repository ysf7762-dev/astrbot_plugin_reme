这是 **`astrbot_plugin_reme`** 项目的完整源码总览。该项目通过冷热分离架构和自动化精炼机制，为 AstrBot 注入了工业级的长期记忆能力。

---

# 📂 项目目录结构
**`astrbot_plugin_reme`** 插件的完整目录结构。

它是严格按照 AstrBot 插件开发规范以及 **ReMe/CoPaw** 的“冷热分离”架构设计的：

```text
astrbot_plugin_reme/
├── .gitignore              # Git 忽略文件（防止上传私密记忆和数据库）
├── LICENSE                 # MIT 开源协议文件
├── README.md               # 插件详细说明文档（你的项目门面）
├── metadata.yaml           # 插件商店元数据（用于上架商店索引）
├── requirements.txt        # 依赖库清单（chromadb, tiktoken, sentence-transformers）
├── __init__.py             # Python 包初始化文件
├── main.py                 # 插件入口：负责拦截器（Hooks）、工具（Tools）和指令注册
├── memory_manager.py       # 记忆大脑：负责 ChromaDB 操作、MD 读写、后台压缩与 LLM 调度
├── prompts.py              # 提示词仓库：存放压缩、精炼、重写和经验提取的顶级 Prompt
├── schema.py               # 数据模型：定义 MemoryNode 结构、哈希指纹和记忆分类
└── templates/              # 灵魂模板区（插件自带，首次启动会拷贝给用户）
    ├── AGENTS.md           # 行为准则与安全守则模板
    ├── SOUL.md             # AI 人格与灵魂设定模板
    ├── PROFILE.md          # 用户核心画像模板
    ├── MEMORY.md           # 工具设置与长期备忘录模板
    ├── BOOTSTRAP.md        # 新人觉醒仪式引导脚本
    └── HEARTBEAT.md        # 定时任务（Heartbeat）清单模板
```

---

### 📂 运行时生成的数据目录 (plugin_data)
当插件运行后，AstrBot 会在系统的 `data/plugin_data/` 目录下自动生成以下结构来存放你的**真实记忆**：

```text
data/plugin_data/astrbot_plugin_reme/
├── chroma_db/              # ChromaDB 向量数据库文件（冷记忆所在地）
└── {user_id}/              # 每个用户的独立记忆空间
    ├── SOUL.md             # 经过进化的 AI 性格
    ├── PROFILE.md          # 实时精炼的用户画像（热记忆核心）
    ├── AGENTS.md           # 该用户特有的行为准则
    ├── MEMORY.md           # 该用户独有的工具逻辑存档
    └── memory/             # 每日笔记文件夹
        ├── 2026-03-12.md   # 今天的原始对话日志（秒级回忆源）
        └── 2026-03-11.md   # 昨天的原始对话日志
```

### 💡 结构设计亮点：
1.  **代码与数据分离**：插件目录只存代码和模板，`plugin_data` 存真实数据。升级插件不会丢记忆。
2.  **模块化设计**：`main.py` 极轻，`memory_manager.py` 极重，逻辑清晰，方便以后扩展（比如以后你想把 ChromaDB 换成 Milvus，只需要改 Manager 即可）。
3.  **模板驱动**：通过 `templates/` 文件夹实现了 CoPaw 的“工作区自初始化”理念，让 AI 第一次启动就拥有极高的“智商”和“主观能动性”。

---

## 1. 📂 文件路径: `schema.py`
**功能**：定义记忆的“基因”，负责哈希去重、分类标注及与向量数据库的格式适配。

```python
# schema.py

import hashlib
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, model_validator


# ── 1. 记忆分类枚举 ──────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    """
    严格定义记忆的维度。这是实现“精准回忆”的基础。
    对应你提到的三个核心场景。
    """
    PERSONAL = "personal"  # 个人记忆：宝宝成长日记、家庭琐事、个人偏好
    PROCEDURAL = "procedural"  # 程序性记忆：工作总结、办事流程、SOP、项目成果
    TOOL = "tool"  # 工具记忆：专业软件(CAD)参数、API配置、设备使用逻辑
    SUMMARY = "summary"  # 压缩摘要：日常闲聊产生的定期压缩背景记录


def get_now_time() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 2. 记忆核心数据模型 ────────────────────────────────────────────────────────

class MemoryNode(BaseModel):
    """
    记忆原子节点。系统存入 ChromaDB 的每一条数据，都必须符合这个结构。
    """
    # 基础字段
    memory_id: str = Field(default="", description="记忆唯一指纹 (SHA-256)")
    memory_type: MemoryType = Field(default=MemoryType.SUMMARY, description="记忆分类")
    content: str = Field(..., description="记忆的具体内容、事实或步骤")

    # 核心字段：触发条件 (极其重要)
    when_to_use: str = Field(default="", description="触发条件：在什么具体情境下应该回想起这段记忆")

    # 元数据字段
    timestamp: str = Field(default_factory=get_now_time, description="记忆产生的时间")
    score: float = Field(default=1.0, description="重要度打分 (0.0 - 1.0)")
    tags: List[str] = Field(default_factory=list, description="用于辅助检索的关键词标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="额外扩展的元数据")

    @model_validator(mode="after")
    def _generate_memory_id(self) -> "MemoryNode":
        """
        拦截器：自动根据内容生成唯一 ID (哈希防重)。
        防止 AI 把同样的“宝宝学会走路”在库里存成 10 份。
        """
        if not self.memory_id and self.content:
            # 使用 content + when_to_use 的组合做哈希，确保完全一致才算重复
            unique_str = f"{self.when_to_use}::{self.content}".encode("utf-8")
            self.memory_id = f"mem_{hashlib.sha256(unique_str).hexdigest()[:16]}"
        return self

    def to_chroma_record(self) -> dict:
        """
        适配器：将 Pydantic 模型转换为 ChromaDB 接受的扁平化格式。
        向量数据库的 Metadata 通常只支持基本类型，不支持嵌套字典和列表。
        """
        # 1. 构建向量化文本 (Document)
        # 如果有 when_to_use，我们将它和 content 拼在一起进行 Embedding，
        # 这样当用户提问命中“场景”时，能瞬间把内容拉出来。
        embed_text = f"[{self.memory_type.value.upper()}] "
        if self.when_to_use:
            embed_text += f"场景条件：{self.when_to_use}\n"
        embed_text += f"核心内容：{self.content}"

        # 2. 构建扁平化元数据 (Metadata)
        chroma_meta = {
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "score": self.score,
            "tags": ",".join(self.tags) if self.tags else "",  # 列表转为逗号分隔字符串
        }

        # 将额外的 metadata 展平放入
        for k, v in self.metadata.items():
            if isinstance(v, (str, int, float, bool)):
                chroma_meta[k] = v
            else:
                chroma_meta[k] = str(v)

        return {
            "id": self.memory_id,
            "document": embed_text,
            "metadata": chroma_meta
        }
```

---

## 2. 📂 文件路径: `prompts.py`
**功能**：存放核心逻辑的 Prompt 模板，决定了 AI 总结、精炼和回忆的质量。

```python
# 1. 压缩器：将对话转为摘要
COMPACT_PROMPT = """你是一个记忆提炼专家。请将以下对话压缩为摘要。
## 优先级：
1. 核心领域：宝宝成长、工作项目、专业工具细节。
2. 通用价值：用户的新偏好、重大决策、有长期参考价值的事实（如健康、纪念日）。
## 要求：
- 丢弃废话，保留核心事实。
- 保持第三人称 Markdown。
历史摘要：{previous_summary}
待处理对话：
{history}
摘要："""

# 2. 精炼器：智能更新 PROFILE.md
REFINE_PROFILE_PROMPT = """你是一个档案管理员。请根据新信息更新【个人画像】。
现有画像：
{old_profile}
新信息：
{new_facts}
## 要求：
- 严禁删除无关旧信息，只做增量合并或修正。
- 保持 Markdown 结构清晰。
更新后的完整画像："""

# 3. 检索重写器：将碎片化记忆变成人性化叙述
SEARCH_REWRITE_PROMPT = """你是一个记忆提取专家。请将检索到的碎片信息整合成一段连贯的背景知识。
用户问题：{query}
原始记忆：
{raw_results}
## 要求：
- 逻辑连贯，体现时间跨度。
- 若信息无关则忽略。
整合后的回复："""

# 4. 经验提取器：记录工作方法和工具逻辑
EXTRACT_EXPERIENCE_PROMPT = """请将本次成功/失败的经验转化为“程序性记忆”。
背景：{context}
过程：{experience}
请以 JSON 输出：
{{
  "content": "具体的步骤或逻辑",
  "when_to_use": "在什么场景下该想起这段记忆",
  "tags": ["标签"]
}}"""
```

---

## 3. 📂 文件路径: `memory_manager.py`
**功能**：项目的心脏。负责 ChromaDB 管理、MD 文件 IO、异步后台任务及调用系统 LLM。

```python
# memory_manager.py
import asyncio
import json
import shutil
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
import tiktoken
from datetime import datetime

from astrbot.api import logger
from astrbot.api.star import Context
from astrbot.api.provider import ProviderRequest

from .schema import MemoryNode, MemoryType
from .prompts import (
    COMPACT_PROMPT,
    REFINE_PROFILE_PROMPT,
    SEARCH_REWRITE_PROMPT,
    EXTRACT_EXPERIENCE_PROMPT
)

ENCODING = tiktoken.get_encoding("cl100k_base")
EMBED_FN = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


class ReMeManager:
    def __init__(self, base_data_dir: Path, context: Context):
        self.base_dir = base_data_dir
        self.context = context
        self.chroma_client = chromadb.PersistentClient(path=str(self.base_dir / "chroma_db"))
        self.compact_threshold = 8000
        logger.info("[ReMe] 记忆中枢初始化完成。")

    async def _llm_request(self, prompt: str) -> str:
        """调用系统主模型进行后台处理"""
        try:
            provider = self.context.get_using_provider()
            if not provider: return ""
            res = await provider.text_chat(prompt=prompt)
            return res.completion_text if res else ""
        except Exception as e:
            logger.error(f"[ReMe] 内部请求异常: {e}")
            return ""

    def _get_user_dir(self, user_id: str) -> Path:
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def _get_collection(self, user_id: str):
        name = f"reme_{str(user_id).replace('-', '_').replace('@', '_')}"
        return self.chroma_client.get_or_create_collection(name=name, embedding_function=EMBED_FN)

    # ── 1. 每日记录 (Daily Notes) - 实现即时记忆 ──────────────────────────

    def record_interaction(self, user_id: str, role: str, content: str):
        """将对话实时记入 memory/YYYY-MM-DD.md"""
        user_dir = self._get_user_dir(user_id)
        daily_dir = user_dir / "memory"
        daily_dir.mkdir(exist_ok=True)

        file_path = daily_dir / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(f"### [{timestamp}] {role}\n{content}\n\n")

    # ── 2. 热记忆注入 ──────────────────────────────────────────────────

    def get_hot_memory(self, user_id: str) -> str:
        user_dir = self._get_user_dir(user_id)
        template_dir = Path(__file__).parent / "templates"

        all_files = ["AGENTS.md", "SOUL.md", "PROFILE.md", "MEMORY.md", "BOOTSTRAP.md", "HEARTBEAT.md"]
        for f in all_files:
            user_path = user_dir / f
            if not user_path.exists() and (template_dir / f).exists():
                shutil.copy(template_dir / f, user_path)

        hot_parts = []
        for f in ["AGENTS.md", "SOUL.md", "PROFILE.md", "MEMORY.md"]:
            p = user_dir / f
            if p.exists(): hot_parts.append(f"# {f}\n\n{p.read_text('utf-8')}")

        if (user_dir / "BOOTSTRAP.md").exists():
            hot_parts.append(f"# BOOTSTRAP.md\n\n{(user_dir / 'BOOTSTRAP.md').read_text('utf-8')}")

        return f"\n\n---\n# 系统核心工作区\n\n{chr(10).join(hot_parts)}\n---"

    def finish_bootstrap(self, user_id: str) -> str:
        bp = self._get_user_dir(user_id) / "BOOTSTRAP.md"
        if bp.exists(): bp.unlink()
        return "✅ 引导仪式结束，BOOTSTRAP.md 已销毁。"

    # ── 3. 记忆搜索 (ChromaDB + 每日笔记) ──────────────────────────────

    async def search(self, user_id: str, query: str, top_k: int = 4) -> str:
        """混合搜索：向量库(长期) + 每日笔记(近期)"""
        # A. 搜向量数据库 (针对已压缩的旧记忆)
        coll = self._get_collection(user_id)
        res = coll.query(query_texts=[query], n_results=top_k)

        raw_results = ""
        if res and res.get("documents") and res["documents"][0]:
            for meta, doc in zip(res['metadatas'][0], res['documents'][0]):
                raw_results += f"- [长期记忆({meta['timestamp']})] {doc}\n"

        # B. 搜今日笔记 (针对还没来得及压缩的近期对话)
        user_dir = self._get_user_dir(user_id)
        today_file = user_dir / "memory" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        if today_file.exists():
            today_content = today_file.read_text("utf-8")
            # 截取最后一部分，防止太长
            raw_results += f"\n- [今日原始对话流]:\n{today_content[-3000:]}"

        if not raw_results: return "（未找到相关记忆记录）"

        # C. 调用 LLM 重写，让回答有人情味
        rewrite = await self._llm_request(SEARCH_REWRITE_PROMPT.format(query=query, raw_results=raw_results))
        return rewrite if rewrite else raw_results

    # ── 4. 画像精炼与经验提取 ──────────────────────────────────────────

    async def refine_profile(self, user_id: str, new_facts: str):
        user_dir = self._get_user_dir(user_id)
        profile_path = user_dir / "PROFILE.md"
        old_profile = profile_path.read_text("utf-8") if profile_path.exists() else ""

        prompt = REFINE_PROFILE_PROMPT.format(old_profile=old_profile, new_facts=new_facts)
        new_profile = await self._llm_request(prompt)

        if new_profile and len(new_profile.strip()) > 20:
            profile_path.write_text(new_profile, "utf-8")
        else:
            with open(profile_path, "a", encoding="utf-8") as f:
                f.write(f"\n- {new_facts} (待精炼)\n")

    async def extract_and_save_experience(self, user_id: str, experience: str, when_to_use: str, tags: list):
        # 加固：确保 tags 始终是列表
        if isinstance(tags, str):
            tags = [tags]

        res = await self._llm_request(EXTRACT_EXPERIENCE_PROMPT.format(context=when_to_use, experience=experience))
        try:
            # 找到 JSON 的起始和结束位置（去掉分号）
            s_idx = res.find('{')
            e_idx = res.rfind('}') + 1
            data = json.loads(res[s_idx:e_idx])

            # 使用提取后的精炼数据，如果提取失败则使用原始数据作为保底
            await self.add_memory(
                user_id,
                data.get("content", experience),
                MemoryType.PROCEDURAL,
                data.get("when_to_use", when_to_use),
                data.get("tags", tags)
            )
        except Exception:
            # 如果解析失败，直接保存原始文本数据
            await self.add_memory(user_id, experience, MemoryType.PROCEDURAL, when_to_use, tags)

    async def add_memory(self, user_id: str, content: str, memory_type: MemoryType, when_to_use: str = "",
                         tags: list = None):
        node = MemoryNode(content=content, memory_type=memory_type, when_to_use=when_to_use, tags=tags or [])
        record = node.to_chroma_record()
        self._get_collection(user_id).upsert(ids=[record["id"]], documents=[record["document"]],
                                             metadatas=[record["metadata"]])

    # ── 5. 后台压缩逻辑 ──────────────────────────────────────────

    async def check_and_compact(self, user_id: str, req: ProviderRequest):
        history = getattr(req, "contexts", [])
        if not history: return
        text = "\n".join([f"{m.get('role', '')}: {m.get('content', '')}" for m in history])
        if len(ENCODING.encode(text)) > self.compact_threshold:
            logger.warning(f"[ReMe] 上下文超限，后台压缩任务已启动。")
            asyncio.create_task(self._do_compact(user_id, history[:-4]))
            req.contexts = history[-4:]

    async def _do_compact(self, user_id: str, msgs: list):
        try:
            history = "\n".join([f"{m.get('role', '')} {m.get('content', '')}" for m in msgs])
            summary = await self._llm_request(COMPACT_PROMPT.format(previous_summary="(无)", history=history))
            if summary:
                await self.add_memory(user_id, summary, MemoryType.SUMMARY, "历史对话归档")
        except Exception as e:
            logger.error(f"[ReMe] 压缩任务失败: {e}")
```

---

## 4. 📂 文件路径: `main.py`
**功能**：插件入口类。负责将大管家连接到 AstrBot 生命周期，并暴露所有 Agent 工具。

```python
# main.py
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest, LLMResponse
from astrbot.api.star import StarTools, Context, Star, register
from astrbot.api import logger
from .memory_manager import ReMeManager


@register("astrbot_plugin_reme", "YourName", "基于 ReMe 架构的终极长期记忆插件", "1.0.0")
class ReMePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.data_dir = StarTools.get_data_dir(self.name)
        self.memory_manager = ReMeManager(self.data_dir, context)
        logger.info(f"[ReMe] 插件已启动！数据存储于: {self.data_dir}")

    # ── 拦截器 1：请求前注入记忆 ────────────────────────────────────

    @filter.on_llm_request()
    async def before_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        user_id = event.get_sender_id()

        # 1. 自动压缩过长对话 (Token 守门员)
        await self.memory_manager.check_and_compact(user_id, req)

        # 2. 注入热记忆 (Profile/Soul/Agents/Memory)
        hot_memory = self.memory_manager.get_hot_memory(user_id)

        # 3. 注入操作指令引导
        guidance = (
            "\n\n【记忆操作规范】\n"
            "1. 涉及过去、宝宝、工作方法等细节，**必须先用 `search_memory` 工具检索**。\n"
            "2. 发现用户新信息，主动调用 `update_profile`。\n"
            "3. 成功解决问题或学到新工具逻辑，调用 `extract_experience`。"
        )
        req.system_prompt = (req.system_prompt or "") + hot_memory + guidance

    # ── 拦截器 2：响应后记录日志 (实现秒级回忆的关键) ────────────────────────

    @filter.on_llm_response()
    async def handle_response(self, event: AstrMessageEvent, resp: LLMResponse):
        """每一轮对话结束后，实时记入每日笔记"""
        user_id = event.get_sender_id()
        user_msg = event.message_str
        ai_msg = resp.completion_text

        if user_msg and ai_msg:
            # 记录到 memory/YYYY-MM-DD.md
            self.memory_manager.record_interaction(user_id, "User", user_msg)
            self.memory_manager.record_interaction(user_id, "Assistant", ai_msg)

    # ── 工具区 ──

    @filter.llm_tool()
    async def search_memory(self, event: AstrMessageEvent, query: str) -> str:
        """
        语义搜索用户的长期记忆、日记、工作日志和工具逻辑。
        当你回答关于过去的事实、宝宝成长细节或专业工作流程时，必须调用此工具。

        Args:
            query (str): 搜索关键词或自然语言问句（如"宝宝第一次走路"、"报销流程"）。
        """
        user_id = event.get_sender_id()
        logger.info(f"[ReMe] Agent 正在检索记忆: {query}")
        return await self.memory_manager.search(user_id, query)

    @filter.llm_tool()
    async def update_profile(self, event: AstrMessageEvent, new_facts: str) -> str:
        """
        局部修改或更新用户的核心画像 (PROFILE)。
        当你在对话中发现了关于用户的新事实（名字、喜好、宝宝的新变化等）时，请调用此工具。

        Args:
            new_facts (str): 需要更新到画像中的事实陈述。
        """
        user_id = event.get_sender_id()
        logger.info(f"[ReMe] Agent 正在精炼画像，新事实: {new_facts}")
        await self.memory_manager.refine_profile(user_id, new_facts)
        return "✅ 核心画像已智能精炼完毕。"

    @filter.llm_tool()
    async def extract_experience(self, event: AstrMessageEvent, experience: str, when_to_use: str, tags: list) -> str:
        """
        经验提取器。将一段成功的操作、工作流、或工具使用逻辑存入长期记忆库。

        Args:
            experience (str): 具体的步骤、参数或经验内容。
            when_to_use (str): 描述在什么具体情境下应该回想起这段记忆。
            tags (list): 关键词标签列表，例如 ["工作", "技术"]。
        """
        user_id = event.get_sender_id()
        logger.info(f"[ReMe] Agent 正在沉淀程序性经验，条件: {when_to_use}")
        await self.memory_manager.extract_and_save_experience(user_id, experience, when_to_use, tags)
        return "✅ 程序性经验已永久存档。"

    @filter.llm_tool()
    async def finish_bootstrap(self, event: AstrMessageEvent) -> str:
        """
        结束引导仪式。当你完成了 BOOTSTRAP.md 要求的所有初始化任务（如确定称呼、更新了画像等）后调用。
        """
        return self.memory_manager.finish_bootstrap(event.get_sender_id())
```

---

## 5. 📂 文件路径: `__init__.py`
**功能**：标识此文件夹为一个 Python 包。内容可为空。

```python
# astrbot_plugin_reme
```

---

## 6. 依赖说明: `requirements.txt`
**功能**：项目依赖

```python
chromadb
tiktoken
sentence-transformers
```

---

### 💡 结语
这套系统通过 `memory_manager` 充当调度员，完美平衡了**响应速度**（异步处理）、**记忆深度**（向量库）和**性格温度**（MD文件注入）。它已经准备好成为你和宝宝的私人专属“贾维斯”了。