"""大模型能力池：LLM、VL 多模态、代码生成大模型 - 对应架构 3.1 节."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class LLMPool:
    """整合 LLM、VL、代码生成三类模型，提供标准化调用接口."""

    def __init__(
        self,
        llm_client: Any = None,
        vl_client: Any = None,
        code_gen_client: Any = None,
    ):
        self.llm = llm_client
        self.vl = vl_client
        self.code_gen = code_gen_client

    def chat_completion(
        self,
        model_type: str = "llm",
        messages: list[dict] | None = None,
        **kwargs: Any,
    ) -> str:
        """同步调用大模型，model_type 为 llm / vl / code_gen."""
        client = {"llm": self.llm, "vl": self.vl, "code_gen": self.code_gen}.get(
            model_type, self.llm
        )
        if not client:
            return ""
        # 实际对接 OpenAI-compatible 或自研 API
        return ""

    async def chat_completion_async(
        self,
        model_type: str = "llm",
        messages: list[dict] | None = None,
        **kwargs: Any,
    ) -> str:
        """异步调用."""
        return self.chat_completion(model_type, messages, **kwargs)
