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