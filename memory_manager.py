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