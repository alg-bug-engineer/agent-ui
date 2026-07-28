"""统一闭环运行实例（Run）数据模型.

Run 是整个 demo 的主线实体，承载从"场景触发"到"经验沉淀"的完整生命周期。
前端总览、地图图层、右侧详情、报告生成、人工协同都围绕 Run 工作。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 枚举：状态集合
# ---------------------------------------------------------------------------


class TriggerSource(str, Enum):
    """触发来源."""

    PERIODIC = "periodic"       # 周期定时触发
    REALTIME = "realtime"       # 实时异常触发
    MANUAL = "manual"           # 人工手动触发
    RERUN = "rerun"             # 未达标自动复跑
    EXCEPTION = "exception"     # 异常事件触发（设备故障/突发事件）


class SceneType(str, Enum):
    """场景类型."""

    PERIODIC = "periodic"       # 规律性场景（通勤高峰、学校接送、周期性拥堵等）
    DYNAMIC = "dynamic"         # 动态场景（突增流量、事故、恶劣天气等）


class AutomationStatus(str, Enum):
    """自动化执行状态."""

    AUTO_EXEC = "auto_exec"             # 自动执行（高置信度、低风险）
    PENDING_APPROVAL = "pending_approval"  # 待人工审批
    MANUAL_TAKEOVER = "manual_takeover"  # 人工接管
    MANUAL_ADJUSTED = "manual_adjusted"  # 人工微调后继续自动
    FAILED = "failed"                   # 执行失败
    SUSPENDED = "suspended"             # 暂停（等待条件满足）


class EvaluationStatus(str, Enum):
    """效果评估状态."""

    PENDING = "pending"             # 待评估（策略尚未执行或时间窗未到）
    MEETS_TARGET = "meets_target"   # 达标
    NOT_MEETS = "not_meets"         # 未达标
    RERUNNING = "rerunning"         # 复跑中
    EXCEPTION = "exception"         # 评估异常（数据缺失等）


class RunStatus(str, Enum):
    """Run 整体状态."""

    TRIGGERING = "triggering"       # 触发中（刚启动，尚未进入场景认知）
    RUNNING = "running"             # 运行中（任意环节进行中）
    AWAITING_HUMAN = "awaiting_human"  # 等待人工操作
    COMPLETED = "completed"         # 完成（含达标/不达标）
    FAILED = "failed"               # 失败（执行异常终止）


# ---------------------------------------------------------------------------
# 子模型
# ---------------------------------------------------------------------------


class PhaseRecord(BaseModel):
    """单个五环节的执行记录."""

    phase: str
    status: str = "pending"         # pending / running / ok / failed / skipped
    start_time: str | None = None
    end_time: str | None = None
    duration_s: int | None = None
    summary: str | None = None      # 自然语言摘要
    evidence: dict[str, Any] = Field(default_factory=dict)   # 结构化证据（关键指标、诊断结论等）
    output: dict[str, Any] = Field(default_factory=dict)     # 原始输出（供下游阶段消费）


class HumanAction(BaseModel):
    """人工操作记录."""

    action_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    time: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    operator: str = ""
    operator_role: str = ""
    action_type: str = ""           # approve / adjust / takeover / restore / reject
    reason: str = ""
    params_before: dict[str, Any] = Field(default_factory=dict)
    params_after: dict[str, Any] = Field(default_factory=dict)
    ai_suggestion: str = ""         # AI 给出的审批建议
    note: str = ""


class EffectRecord(BaseModel):
    """效果评估记录."""

    evaluated_at: str | None = None
    window_minutes: int = 30
    meets_target: bool | None = None
    overall_score: float = 0.0
    metrics_before: dict[str, Any] = Field(default_factory=dict)
    metrics_after: dict[str, Any] = Field(default_factory=dict)
    metrics_target: dict[str, Any] = Field(default_factory=dict)
    improvements: list[dict[str, Any]] = Field(default_factory=list)
    side_effects: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str = ""
    next_action: str = ""           # continue / rerun / escalate_human / suspend
    experience_worthy: bool = False


class MapContext(BaseModel):
    """地图联动上下文：确定哪些对象、区域在地图上需要高亮."""

    primary_object_id: str = ""
    primary_object_type: str = ""       # region / corridor / intersection
    affected_object_ids: list[str] = Field(default_factory=list)
    influence_polygon: list[list[float]] = Field(default_factory=list)
    poi_ids: list[str] = Field(default_factory=list)
    upstream_ids: list[str] = Field(default_factory=list)
    downstream_ids: list[str] = Field(default_factory=list)


class ReportSnapshot(BaseModel):
    """Run 完成后自动生成的结构化报告快照（作为 LLM 报告的结构化输入）."""

    traffic_situation: str = ""         # 交通态势变化
    trigger_and_findings: str = ""      # 场景触发与问题发现
    od_change_analysis: str = ""        # OD 变化与影响范围
    key_bottleneck: str = ""            # 关键堵点与主因
    strategy_and_action: str = ""       # 已生成策略和执行动作
    effect_and_suggestion: str = ""     # 当前效果与后续建议
    generated_at: str | None = None
    llm_text: str = ""                  # LLM 生成的全文报告


class ExperienceRecord(BaseModel):
    """经验沉淀记录."""

    saved: bool = False
    tag: str = ""
    scene: str = ""
    applicable_scenario: str = ""
    key_conditions: str = ""
    recommended_params: str = ""
    expected_improvement: str = ""
    summary: str = ""


# ---------------------------------------------------------------------------
# 主模型
# ---------------------------------------------------------------------------


class Run(BaseModel):
    """统一闭环运行实例.

    一个 Run 对应一次完整或进行中的智能体闭环任务，覆盖从触发到经验沉淀的全流程。
    """

    # 基础标识
    run_id: str = Field(default_factory=lambda: f"RUN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6].upper()}")
    parent_run_id: str | None = None    # 若为复跑，记录上轮 run_id

    # 触发上下文
    trigger_source: TriggerSource = TriggerSource.REALTIME
    trigger_time: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    trigger_reason: str = ""            # 触发原因说明
    trigger_confidence: float = 1.0    # 触发置信度

    # 目标对象
    target_id: str = ""
    target_name: str = ""
    target_type: str = ""               # region / corridor / intersection

    # 场景
    scene_type: SceneType = SceneType.DYNAMIC
    scene_id: str = ""                  # 关联的场景 ID（如 SCN-COMMUTE）
    scene_name: str = ""

    # 运行状态
    status: RunStatus = RunStatus.TRIGGERING
    automation_status: AutomationStatus = AutomationStatus.AUTO_EXEC
    evaluation_status: EvaluationStatus = EvaluationStatus.PENDING

    # 时间
    start_time: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    end_time: str | None = None
    elapsed_seconds: int | None = None

    # 五环节记录
    phases: list[PhaseRecord] = Field(default_factory=lambda: [
        PhaseRecord(phase="scene_cognition"),
        PhaseRecord(phase="problem_diagnosis"),
        PhaseRecord(phase="control_strategy"),
        PhaseRecord(phase="plan_generation"),
        PhaseRecord(phase="evaluation_feedback"),
    ])

    # 当前活跃环节
    current_phase: str = "scene_cognition"

    # 风险与审批
    risk_level: str = "low"             # low / medium / high
    requires_approval: bool = False
    approval_reason: str = ""

    # 人工干预
    human_actions: list[HumanAction] = Field(default_factory=list)

    # 效果评估
    effect: EffectRecord | None = None

    # 地图联动
    map_context: MapContext = Field(default_factory=MapContext)

    # 报告
    report: ReportSnapshot | None = None

    # 经验沉淀
    experience: ExperienceRecord = Field(default_factory=ExperienceRecord)

    # 复跑次数
    rerun_count: int = 0
    max_reruns: int = 2

    # 异常信息
    error_message: str | None = None

    # 关联的方案 ID（方案生成后写入）
    plan_id: str | None = None

    def get_phase(self, phase_name: str) -> PhaseRecord | None:
        for p in self.phases:
            if p.phase == phase_name:
                return p
        return None

    def is_complete(self) -> bool:
        return self.status in (RunStatus.COMPLETED, RunStatus.FAILED)

    def can_auto_execute(self) -> bool:
        return (
            self.automation_status == AutomationStatus.AUTO_EXEC
            and not self.requires_approval
            and self.risk_level == "low"
        )

    def can_rerun(self) -> bool:
        return (
            self.evaluation_status == EvaluationStatus.NOT_MEETS
            and self.rerun_count < self.max_reruns
            and self.automation_status not in (AutomationStatus.MANUAL_TAKEOVER, AutomationStatus.FAILED)
        )

    def to_summary_dict(self) -> dict[str, Any]:
        """生成供总览列表使用的精简摘要."""
        phase_statuses = {p.phase: p.status for p in self.phases}
        return {
            "runId": self.run_id,
            "parentRunId": self.parent_run_id,
            "triggerSource": self.trigger_source.value,
            "triggerTime": self.trigger_time,
            "triggerReason": self.trigger_reason,
            "targetId": self.target_id,
            "targetName": self.target_name,
            "targetType": self.target_type,
            "sceneType": self.scene_type.value,
            "sceneName": self.scene_name,
            "status": self.status.value,
            "automationStatus": self.automation_status.value,
            "evaluationStatus": self.evaluation_status.value,
            "currentPhase": self.current_phase,
            "riskLevel": self.risk_level,
            "requiresApproval": self.requires_approval,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "elapsedSeconds": self.elapsed_seconds,
            "rerunCount": self.rerun_count,
            "phaseStatuses": phase_statuses,
            "meetsTarget": self.effect.meets_target if self.effect else None,
            "overallScore": self.effect.overall_score if self.effect else None,
            "mapContext": self.map_context.model_dump(),
            "hasPlan": self.plan_id is not None,
            "hasReport": self.report is not None and bool(self.report.llm_text),
            "experienceSaved": self.experience.saved,
            "errorMessage": self.error_message,
        }

    def to_detail_dict(self) -> dict[str, Any]:
        """生成供右侧详情面板使用的完整输出."""
        d = self.to_summary_dict()
        d["phases"] = [
            {
                "phase": p.phase,
                "status": p.status,
                "startTime": p.start_time,
                "endTime": p.end_time,
                "durationS": p.duration_s,
                "summary": p.summary,
                "evidence": p.evidence,
            }
            for p in self.phases
        ]
        d["humanActions"] = [a.model_dump() for a in self.human_actions]
        d["effect"] = self.effect.model_dump() if self.effect else None
        d["report"] = self.report.model_dump() if self.report else None
        d["experience"] = self.experience.model_dump()
        d["approvalReason"] = self.approval_reason
        return d
