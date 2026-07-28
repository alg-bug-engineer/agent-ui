"""分控层子智能体基类 - 所有专业环节与场景管控子智能体继承此基类."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSubAgent(ABC):
    """子智能体基类：接受主智能体调度，执行专业任务并反馈结果."""

    name: str = "base"
    """子智能体名称."""

    def __init__(
        self,
        llm_client: Any = None,
        mcp_tools: Any = None,
        knowledge_rag: Any = None,
        db_clients: dict[str, Any] | None = None,
    ):
        self.llm = llm_client
        self.mcp_tools = mcp_tools or {}
        self.rag = knowledge_rag
        self.db = db_clients or {}

    @abstractmethod
    def run(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """执行任务，返回结构化结果供主智能体或下一环节使用."""
        pass

    def get_required_skills(self) -> list[str]:
        """返回该子智能体依赖的 Skill 技能包 ID 列表，用于运行时动态加载."""
        return []
