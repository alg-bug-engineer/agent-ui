"""人工干预机制：自然语言对话、可视化操作、策略模板下发、应急一键接管.

1.0 版本：对接 RunStore，实现自动执行、待审批、人工接管、恢复自动四态协同。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class InterventionLevel(str, Enum):
    """干预层级与权限：路口/干线/区域/应急接管."""

    INTERSECTION = "intersection"  # 操作员
    CORRIDOR = "corridor"         # 班组长
    REGION = "region"             # 主管
    EMERGENCY_TAKEOVER = "emergency_takeover"  # 应急值班主管


class InterventionRequest(BaseModel):
    """人工干预请求."""

    level: InterventionLevel
    target_id: str = Field(..., description="路口/干线/区域 ID")
    action: str = Field(..., description="approve | adjust | takeover | restore | reject")
    payload: dict[str, Any] = Field(default_factory=dict)
    operator_id: str = ""
    operator_role: str = "操作员"
    reason: str = ""
    run_id: str = ""    # 关联的 Run ID（若有）


class InterventionService:
    """人工干预服务：记录干预、转化为管控指令、推送至主智能体/Kafka.

    四类协同状态：
    - auto_exec: 高置信度、低风险，系统直接执行并留痕
    - pending_approval: 中高风险，进入待审批池，人工确认后继续
    - manual_takeover: 设备异常/执行失败/效果恶化，人工接管
    - restore: 人工接管完成后恢复自动控制
    """

    def __init__(self, kafka_producer: Any = None, redis_client: Any = None):
        self.kafka = kafka_producer
        self.redis = redis_client

    def submit(self, request: InterventionRequest) -> str:
        """提交干预请求，若有关联 Run 则更新 RunStore."""
        from src.demo.run_store import get_run_store
        store = get_run_store()

        if not request.run_id:
            return ""

        action = request.action
        op = request.operator_id or "值班交警"
        role = request.operator_role
        reason = request.reason

        if action == "approve":
            store.approve(request.run_id, op, role, reason)
        elif action == "reject":
            store.reject(request.run_id, op, role, reason)
        elif action == "takeover":
            store.takeover(request.run_id, op, role, reason, request.payload)
        elif action == "restore":
            store.restore_auto(request.run_id, op, role, reason)
        elif action == "adjust":
            store.adjust(
                request.run_id, op, role, reason,
                request.payload.get("before", {}),
                request.payload.get("after", {}),
            )

        return request.run_id

    def get_pending_confirmations(self, scope: str = "") -> list[dict]:
        """获取待人工确认的智能体推荐方案."""
        from src.demo.run_store import get_run_store
        store = get_run_store()
        runs = store.list_pending_approval()
        result = []
        for r in runs:
            if scope and r.target_id != scope and r.target_type != scope:
                continue
            result.append({
                "run_id": r.run_id,
                "target_id": r.target_id,
                "target_name": r.target_name,
                "target_type": r.target_type,
                "approval_reason": r.approval_reason,
                "risk_level": r.risk_level,
                "trigger_time": r.trigger_time,
            })
        return result

    def get_manual_takeovers(self, scope: str = "") -> list[dict]:
        """获取当前所有人工接管中的对象."""
        from src.demo.run_store import get_run_store
        store = get_run_store()
        runs = store.list_manual_takeover()
        result = []
        for r in runs:
            if scope and r.target_id != scope:
                continue
            last_action = r.human_actions[-1] if r.human_actions else None
            result.append({
                "run_id": r.run_id,
                "target_id": r.target_id,
                "target_name": r.target_name,
                "target_type": r.target_type,
                "operator": last_action.operator if last_action else "",
                "reason": last_action.reason if last_action else "",
                "takeover_time": last_action.time if last_action else r.start_time,
            })
        return result
