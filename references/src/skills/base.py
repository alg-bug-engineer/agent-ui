"""Skill 技能包基类与注册中心 - 对应架构 2.1 节 Skill 设计规范."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.common.models import TriggerMode


class SkillManifest(BaseModel):
    """技能包声明：标识、描述、触发、工具、输入输出契约."""

    id: str = Field(..., description="唯一标识符")
    version: str = Field(default="1.0.0", description="版本号")
    description: str = Field("", description="自然语言描述，供智能体理解并选择调用")
    trigger_mode: TriggerMode = Field(..., description="触发模式")
    trigger_keywords: list[str] = Field(default_factory=list, description="关键词触发词")
    trigger_threshold: dict[str, Any] = Field(
        default_factory=dict, description="场景匹配阈值，如 saturation > 0.85"
    )
    period_minutes: int = Field(0, description="周期性触发间隔(分钟)，0 表示非周期")
    required_tools: list[str] = Field(
        default_factory=list, description="依赖的大模型、MCP 工具、知识库、DB 清单"
    )
    input_schema: dict[str, Any] = Field(default_factory=dict, description="输入数据格式")
    output_schema: dict[str, Any] = Field(default_factory=dict, description="输出结果格式")


class Skill(ABC):
    """Skill 技能包抽象基类：每个技能是独立能力单元，含能力描述、触发条件、工具、执行流程."""

    manifest: SkillManifest

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """执行技能内部推理与工具调用，支持条件分支、循环与异常处理."""
        pass

    def check_trigger(self, event: dict[str, Any]) -> bool:
        """根据触发模式判断当前事件是否触发本技能."""
        mode = self.manifest.trigger_mode
        if mode == TriggerMode.KEYWORD:
            text = event.get("text", "") or event.get("task_type", "")
            return any(kw in text for kw in self.manifest.trigger_keywords)
        if mode == TriggerMode.SCENARIO_MATCH:
            for k, v in self.manifest.trigger_threshold.items():
                if event.get(k) is not None and event.get(k) != v:
                    return False
            return True
        if mode == TriggerMode.DISPATCH:
            return event.get("dispatched_skill_id") == self.manifest.id
        return False


class SkillRegistry:
    """技能注册中心：统一管理已注册 Skill，支持版本管理、启用/禁用、依赖检查、热更新."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}
        self._enabled: set[str] = set()

    def register(self, skill: Skill, enable: bool = True) -> None:
        """注册技能包."""
        sid = skill.manifest.id
        self._skills[sid] = skill
        if enable:
            self._enabled.add(sid)

    def unregister(self, skill_id: str) -> None:
        """移除技能包."""
        self._skills.pop(skill_id, None)
        self._enabled.discard(skill_id)

    def get(self, skill_id: str) -> Skill | None:
        """按 ID 获取技能."""
        return self._skills.get(skill_id)

    def list_enabled(self) -> list[Skill]:
        """返回当前启用的技能列表."""
        return [self._skills[sid] for sid in self._enabled if sid in self._skills]

    def enable(self, skill_id: str) -> None:
        """启用技能."""
        if skill_id in self._skills:
            self._enabled.add(skill_id)

    def disable(self, skill_id: str) -> None:
        """禁用技能."""
        self._enabled.discard(skill_id)

    def match_skills(self, event: dict[str, Any]) -> list[Skill]:
        """根据事件匹配应触发的技能列表."""
        return [s for s in self.list_enabled() if s.check_trigger(event)]
