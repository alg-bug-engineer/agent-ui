"""运行实例状态存储（内存版 demo 用）.

维护：
- 当前运行队列（running / awaiting_human）
- 历史记录（completed / failed）
- 待审批队列
- 人工接管记录
- 全局统计
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Any

from src.demo.run_model import (
    AutomationStatus,
    EvaluationStatus,
    HumanAction,
    Run,
    RunStatus,
    TriggerSource,
)


class RunStore:
    """线程安全的运行实例内存存储."""

    _MAX_HISTORY = 200          # 历史记录上限
    _MAX_RUNNING = 20           # 并行运行上限

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # 活跃运行：run_id -> Run
        self._active: dict[str, Run] = {}
        # 历史记录（按完成时间倒序）
        self._history: deque[Run] = deque(maxlen=self._MAX_HISTORY)
        # 待审批队列
        self._pending_approval: list[str] = []
        # 今日统计（重启清零）
        self._stats = {
            "totalRuns": 0,
            "autoExecRuns": 0,
            "pendingApprovalRuns": 0,
            "manualTakeoverRuns": 0,
            "completedRuns": 0,
            "failedRuns": 0,
            "meetsTargetRuns": 0,
            "notMeetsTargetRuns": 0,
            "rerunCount": 0,
            "experienceSaved": 0,
        }
        self._date = datetime.now().strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # 写操作
    # ------------------------------------------------------------------

    def add(self, run: Run) -> None:
        """加入活跃队列."""
        with self._lock:
            self._reset_if_new_day()
            self._active[run.run_id] = run
            self._stats["totalRuns"] += 1
            if run.automation_status == AutomationStatus.AUTO_EXEC:
                self._stats["autoExecRuns"] += 1
            elif run.automation_status == AutomationStatus.PENDING_APPROVAL:
                self._stats["pendingApprovalRuns"] += 1
                self._pending_approval.append(run.run_id)

    def update(self, run: Run) -> None:
        """更新活跃 Run（若已移入历史则追加更新历史末尾）."""
        with self._lock:
            if run.run_id in self._active:
                self._active[run.run_id] = run
                # 检查是否需要移到历史
                if run.status in (RunStatus.COMPLETED, RunStatus.FAILED):
                    self._archive(run)

    def approve(self, run_id: str, operator: str, role: str, note: str = "") -> Run | None:
        """审批通过：把 PENDING_APPROVAL -> AUTO_EXEC 并继续运行."""
        with self._lock:
            run = self._active.get(run_id)
            if not run:
                return None
            action = HumanAction(
                operator=operator,
                operator_role=role,
                action_type="approve",
                reason="人工审批通过",
                note=note,
            )
            run.human_actions.append(action)
            run.automation_status = AutomationStatus.AUTO_EXEC
            run.requires_approval = False
            if run_id in self._pending_approval:
                self._pending_approval.remove(run_id)
            return run

    def reject(self, run_id: str, operator: str, role: str, reason: str = "") -> Run | None:
        """审批驳回：暂停该 Run。"""
        with self._lock:
            run = self._active.get(run_id)
            if not run:
                return None
            action = HumanAction(
                operator=operator,
                operator_role=role,
                action_type="reject",
                reason=reason,
            )
            run.human_actions.append(action)
            run.automation_status = AutomationStatus.SUSPENDED
            run.status = RunStatus.FAILED
            run.error_message = f"人工驳回：{reason}"
            if run_id in self._pending_approval:
                self._pending_approval.remove(run_id)
            self._archive(run)
            return run

    def takeover(self, run_id: str, operator: str, role: str, reason: str, params: dict[str, Any]) -> Run | None:
        """人工接管."""
        with self._lock:
            run = self._active.get(run_id)
            if not run:
                return None
            action = HumanAction(
                operator=operator,
                operator_role=role,
                action_type="takeover",
                reason=reason,
                params_after=params,
            )
            run.human_actions.append(action)
            run.automation_status = AutomationStatus.MANUAL_TAKEOVER
            run.status = RunStatus.AWAITING_HUMAN
            self._stats["manualTakeoverRuns"] += 1
            return run

    def restore_auto(self, run_id: str, operator: str, role: str, note: str = "") -> Run | None:
        """恢复自动控制."""
        with self._lock:
            run = self._active.get(run_id)
            if not run:
                return None
            action = HumanAction(
                operator=operator,
                operator_role=role,
                action_type="restore",
                reason=note or "恢复自动控制",
            )
            run.human_actions.append(action)
            run.automation_status = AutomationStatus.MANUAL_ADJUSTED
            run.status = RunStatus.RUNNING
            return run

    def adjust(
        self,
        run_id: str,
        operator: str,
        role: str,
        reason: str,
        params_before: dict[str, Any],
        params_after: dict[str, Any],
        ai_suggestion: str = "",
    ) -> Run | None:
        """人工参数微调."""
        with self._lock:
            run = self._active.get(run_id)
            if not run:
                return None
            action = HumanAction(
                operator=operator,
                operator_role=role,
                action_type="adjust",
                reason=reason,
                params_before=params_before,
                params_after=params_after,
                ai_suggestion=ai_suggestion,
            )
            run.human_actions.append(action)
            run.automation_status = AutomationStatus.MANUAL_ADJUSTED
            return run

    # ------------------------------------------------------------------
    # 读操作
    # ------------------------------------------------------------------

    def get(self, run_id: str) -> Run | None:
        with self._lock:
            run = self._active.get(run_id)
            if run:
                return run
            for h in self._history:
                if h.run_id == run_id:
                    return h
        return None

    def list_active(self) -> list[Run]:
        with self._lock:
            return list(self._active.values())

    def list_history(self, limit: int = 30, target_id: str | None = None) -> list[Run]:
        with self._lock:
            runs = list(self._history)
            if target_id:
                runs = [r for r in runs if r.target_id == target_id]
            return runs[:limit]

    def list_pending_approval(self) -> list[Run]:
        with self._lock:
            return [
                self._active[rid]
                for rid in self._pending_approval
                if rid in self._active
            ]

    def list_manual_takeover(self) -> list[Run]:
        with self._lock:
            return [
                r for r in self._active.values()
                if r.automation_status == AutomationStatus.MANUAL_TAKEOVER
            ]

    def get_global_stats(self) -> dict[str, Any]:
        """全局统计数据，用于左侧 KPI 区."""
        with self._lock:
            active = list(self._active.values())
            running_count = sum(1 for r in active if r.status == RunStatus.RUNNING)
            awaiting_count = sum(1 for r in active if r.status == RunStatus.AWAITING_HUMAN)
            pending_approval_count = len(self._pending_approval)
            manual_takeover_count = sum(
                1 for r in active if r.automation_status == AutomationStatus.MANUAL_TAKEOVER
            )
            return {
                **self._stats,
                "activeRuns": len(active),
                "runningRuns": running_count,
                "awaitingHumanRuns": awaiting_count,
                "pendingApprovalCount": pending_approval_count,
                "manualTakeoverCount": manual_takeover_count,
            }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _archive(self, run: Run) -> None:
        """将已完成/失败的 Run 移入历史."""
        if run.run_id in self._active:
            del self._active[run.run_id]
        if run.run_id in self._pending_approval:
            self._pending_approval.remove(run.run_id)
        self._history.appendleft(run)
        if run.status == RunStatus.COMPLETED:
            self._stats["completedRuns"] += 1
        elif run.status == RunStatus.FAILED:
            self._stats["failedRuns"] += 1
        if run.effect:
            if run.effect.meets_target:
                self._stats["meetsTargetRuns"] += 1
            elif run.effect.meets_target is False:
                self._stats["notMeetsTargetRuns"] += 1
        if run.experience.saved:
            self._stats["experienceSaved"] += 1

    def _reset_if_new_day(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._date:
            self._date = today
            for k in self._stats:
                self._stats[k] = 0


# 全局单例
_store: RunStore | None = None


def get_run_store() -> RunStore:
    global _store
    if _store is None:
        _store = RunStore()
    return _store
