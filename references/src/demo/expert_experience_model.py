"""专家经验录入数据模型（ExpertExperienceRecord）.

与智能体输出结构对齐：StrategyInstruction / issues[] / SupplyDemandStateProfile，
便于后续 RAG / ExperienceSink.promote_to_knowledge 消费同一 schema。
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# 1. 目标对象                                                          #
# ------------------------------------------------------------------ #

class CustomTargetDetail(BaseModel):
    """自定义目标的范围描述（MVP：名称 + 关联路口/干线列表）."""
    custom_kind: str = Field(default="", description="自定义类型描述，如 '学校周边区域'")
    intersection_ids: list[str] = Field(default_factory=list)
    corridor_ids: list[str] = Field(default_factory=list)
    note: str = Field(default="")


class ExperienceTarget(BaseModel):
    level: Literal["region", "corridor", "intersection", "custom"]
    id: str | None = Field(default=None, description="预置实体 ID")
    name: str = Field(description="显示名")
    custom: CustomTargetDetail | None = None


# ------------------------------------------------------------------ #
# 2. 适用上下文                                                        #
# ------------------------------------------------------------------ #

class ExperienceContext(BaseModel):
    time_periods: list[str] = Field(
        default_factory=list,
        description="适用时段，如 ['早高峰 07:00-09:00', '晚高峰 17:00-19:00']",
    )
    date_types: list[str] = Field(
        default_factory=list,
        description="日期类型，如 ['工作日', '节假日']",
    )
    weather_event_tags: list[str] = Field(
        default_factory=list,
        description="天气/事件标签，如 ['暴雨', '大型活动', '常态']",
    )
    confidence: Literal["high", "medium", "low"] = Field(default="medium", description="可信度自评")
    valid_until: str | None = Field(default=None, description="有效期，ISO 日期字符串")
    author: str = Field(default="", description="作者/班组")


# ------------------------------------------------------------------ #
# 3. 场景认知（对齐 SupplyDemandStateProfile）                         #
# ------------------------------------------------------------------ #

class SceneCognitionRecord(BaseModel):
    mode: Literal["minimal", "structured", "narrative"] = "minimal"
    summary: str = Field(default="", description="场景一句话摘要")
    supply: dict[str, Any] = Field(default_factory=dict, description="供给侧键值，如 {lanes:3, saturation:0.85}")
    demand: dict[str, Any] = Field(default_factory=dict)
    state: dict[str, Any] = Field(default_factory=dict)
    scene_tags: list[str] = Field(default_factory=list, description="场景标签，如 ['学校周边', '潮汐']")
    diagnosis_type: str = Field(default="", description="诊断类型，如 '信控优化' / '应急接管'")
    narrative: str = Field(default="", description="叙事描述（叙事模式使用）")


# ------------------------------------------------------------------ #
# 4. 问题诊断（对齐 issues[]）                                         #
# ------------------------------------------------------------------ #

class IssueRecord(BaseModel):
    issue_id: str = Field(default="", description="对齐 ISSUE_CODEBOOK 问题码，或自定义")
    name: str = Field(default="")
    category: str = Field(default="", description="static | dynamic | signal_control | custom")
    scope: str = Field(default="", description="region | corridor | intersection")
    severity: str = Field(default="P2", description="P0-P3 或 1-5")
    confidence: str = Field(default="medium", description="high | medium | low")
    evidence: str = Field(default="")
    reason: str = Field(default="")
    suggested_action_hint: str = Field(default="")
    rank: int = Field(default=0, description="人工设置的优先序号，映射为 priority_order")


class ProblemDiagnosisRecord(BaseModel):
    mode: Literal["minimal", "structured", "narrative"] = "minimal"
    main_issue_summary: str = Field(default="", description="精简模式：主要问题描述")
    issues: list[IssueRecord] = Field(default_factory=list)
    priority_order: list[str] = Field(default_factory=list, description="问题 ID 优先序列")
    narrative: str = Field(default="")


# ------------------------------------------------------------------ #
# 5. 控制策略（对齐 StrategyInstruction + selected_templates）         #
# ------------------------------------------------------------------ #

class SelectedTemplateRecord(BaseModel):
    template_id: str = Field(default="", description="对齐 TEMPLATE_META")
    description: str = Field(default="")
    recommended_by_issue: str = Field(default="", description="关联推荐的 issue_id")


class ControlStrategyRecord(BaseModel):
    mode: Literal["minimal", "structured", "narrative"] = "minimal"
    strategy_summary: str = Field(default="", description="精简模式：自然语言描述")
    selected_templates: list[SelectedTemplateRecord] = Field(default_factory=list)
    scope: str = Field(default="")
    target_priority: str = Field(default="")
    background_plan: str = Field(default="")
    realtime_patch: str = Field(default="")
    trigger_condition: str = Field(default="")
    exit_condition: str = Field(default="")
    hysteresis_minutes: int | None = Field(default=None)
    hard_constraints: list[str] = Field(default_factory=list)
    fallback_plan: str = Field(default="")
    narrative: str = Field(default="")


# ------------------------------------------------------------------ #
# 6. 调控经验（运维与效果，无单一智能体模型）                            #
# ------------------------------------------------------------------ #

class RegulationExperienceRecord(BaseModel):
    trigger_condition: str = Field(default="", description="触发条件描述")
    execution_actions: str = Field(default="", description="执行动作（配时/相位/协调/手动接管）")
    observation_window: str = Field(default="", description="观察窗口，如 '干预后30分钟'")
    before_metrics: dict[str, Any] = Field(default_factory=dict, description="干预前指标")
    after_metrics: dict[str, Any] = Field(default_factory=dict, description="干预后指标")
    improvement_summary: str = Field(default="", description="改善摘要，如 '延误降低21%'")
    review_conclusion: str = Field(default="", description="复盘结论")
    taboo_and_rollback: str = Field(default="", description="禁忌/回滚条件")
    intervention_id: str | None = Field(default=None, description="关联干预记录 ID（可选弱关联）")
    narrative: str = Field(default="")


# ------------------------------------------------------------------ #
# 7. 顶层记录                                                          #
# ------------------------------------------------------------------ #

class ExpertExperienceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    author: str = Field(default="")
    status: Literal["draft", "published"] = "draft"
    ref_template_id: str | None = Field(default=None, description="参考模版 ID（若从模版载入）")

    target: ExperienceTarget
    context: ExperienceContext = Field(default_factory=ExperienceContext)
    scene_cognition: SceneCognitionRecord = Field(default_factory=SceneCognitionRecord)
    problem_diagnosis: ProblemDiagnosisRecord = Field(default_factory=ProblemDiagnosisRecord)
    control_strategy: ControlStrategyRecord = Field(default_factory=ControlStrategyRecord)
    regulation_experience: RegulationExperienceRecord = Field(default_factory=RegulationExperienceRecord)

    links: dict[str, str] = Field(default_factory=dict, description="弱关联：intervention_id / run_id 等")


# ------------------------------------------------------------------ #
# 8. API 请求/响应模型                                                  #
# ------------------------------------------------------------------ #

class ExpertExperienceCreateRequest(BaseModel):
    record: ExpertExperienceRecord


class ExpertExperienceListResponse(BaseModel):
    total: int
    records: list[ExpertExperienceRecord]
