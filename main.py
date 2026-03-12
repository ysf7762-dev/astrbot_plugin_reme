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