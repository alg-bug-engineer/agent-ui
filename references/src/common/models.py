"""信控智能体公共数据模型 - 对应方法论中的策略指令、三维画像等."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ControlLevel(str, Enum):
    """管控层级：区域-干线-路口."""

    REGION = "region"
    CORRIDOR = "corridor"
    INTERSECTION = "intersection"
    EMERGENCY = "emergency"


class TriggerMode(str, Enum):
    """Skill 触发模式."""

    KEYWORD = "keyword"
    SCENARIO_MATCH = "scenario_match"
    PERIODIC = "periodic"
    DISPATCH = "dispatch"


# ---------- 三维画像（场景认知） ----------


class SupplyDemandStateProfile(BaseModel):
    """供给-需求-状态三维画像."""

    supply: dict[str, Any] = Field(default_factory=dict, description="交通供给分析结果")
    demand: dict[str, Any] = Field(default_factory=dict, description="交通需求分析结果")
    state: dict[str, Any] = Field(default_factory=dict, description="交通状态分析结果")
    summary: str = Field("", description="自然语言态势总结")


# ---------- 策略指令（控制策略 → 方案生成） ----------


class StrategyInstruction(BaseModel):
    """可机读的策略指令 - 对应方法论「对外输出统一形成可机读的策略指令」."""

    scope: dict[str, Any] = Field(..., description="对象范围：区域边界/干线走廊/路口集合")
    target_priority: list[str] = Field(default_factory=list, description="目标优先级")
    background_plan: str = Field("", description="背景方案标识")
    realtime_patch: dict[str, Any] = Field(default_factory=dict, description="实时补丁")
    trigger_condition: str = Field("", description="触发条件")
    exit_condition: str = Field("", description="退出条件")
    hysteresis_minutes: int = Field(0, description="滞回时间(分钟)")
    hard_constraints: list[str] = Field(default_factory=list, description="硬约束")
    fallback_plan: str = Field("", description="降级回退方案")


# ---------- 任务与闭环 ----------


class TaskType(str, Enum):
    """全局任务类型."""

    CT_CHECK = "ct_check"  # 城市交通 CT 体检
    GLOBAL_OPTIMIZE = "global_optimize"  # 全域信控优化
    CONGESTION_RESPONSE = "congestion_response"  # 突发拥堵处置


class LoopPhase(str, Enum):
    """五环节闭环阶段."""

    SCENE_COGNITION = "scene_cognition"
    PROBLEM_DIAGNOSIS = "problem_diagnosis"
    CONTROL_STRATEGY = "control_strategy"
    PLAN_GENERATION = "plan_generation"
    EVALUATION_FEEDBACK = "evaluation_feedback"
