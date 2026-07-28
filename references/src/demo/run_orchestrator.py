"""Demo 级闭环运行编排器.

职责：
1. 接收触发请求（周期/实时/手动/复跑）
2. 创建并推进 Run 实例经历五环节
3. 在每个阶段更新 Run 状态并持久化到 RunStore
4. 评估结束后决策：达标 -> 报告; 未达标 -> 复跑或转人工
5. 全程异步推进，不阻塞 API 返回
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from src.demo.run_model import (
    AutomationStatus,
    EffectRecord,
    EvaluationStatus,
    ExperienceRecord,
    HumanAction,
    MapContext,
    PhaseRecord,
    ReportSnapshot,
    Run,
    RunStatus,
    SceneType,
    TriggerSource,
)
from src.demo.run_store import RunStore, get_run_store
from src.master_agent import MasterAgent
from src.sub_agents import (
    ControlStrategyAgent,
    EvaluationFeedbackAgent,
    PlanGenerationAgent,
    ProblemDiagnosisAgent,
    SceneCognitionAgent,
)
from src.workflow.loop import FivePhaseLoop


# 高风险策略模板（需要人工审批）
HIGH_RISK_TEMPLATES = {
    "region_core_expansion_control",
    "region_boundary_flow_control",
    "region_long_term_infra_gap_guard",
}

# 自动审批置信度阈值
AUTO_EXEC_CONFIDENCE_THRESHOLD = 0.90


class RunOrchestrator:
    """闭环运行编排器，负责创建、推进和归档 Run 实例."""

    def __init__(self, store: RunStore | None = None) -> None:
        self._store = store or get_run_store()
        self._master = MasterAgent()
        self._scene_agent = SceneCognitionAgent()
        self._diagnosis_agent = ProblemDiagnosisAgent()
        self._strategy_agent = ControlStrategyAgent()
        self._plan_agent = PlanGenerationAgent()
        self._eval_agent = EvaluationFeedbackAgent()
        self._loop = FivePhaseLoop(
            master=self._master,
            scene_agent=self._scene_agent,
            diagnosis_agent=self._diagnosis_agent,
            strategy_agent=self._strategy_agent,
            plan_agent=self._plan_agent,
            evaluation_agent=self._eval_agent,
        )

    # ------------------------------------------------------------------
    # 触发入口
    # ------------------------------------------------------------------

    def trigger(
        self,
        target_id: str,
        target_name: str,
        target_type: str,
        trigger_source: TriggerSource = TriggerSource.REALTIME,
        scene_type: SceneType = SceneType.DYNAMIC,
        scene_id: str = "",
        scene_name: str = "",
        trigger_reason: str = "",
        trigger_confidence: float = 1.0,
        task_input: dict[str, Any] | None = None,
        parent_run_id: str | None = None,
        rerun_count: int = 0,
        demo_target_data: dict[str, Any] | None = None,
    ) -> str:
        """触发一次闭环 Run，返回 run_id；实际执行在后台线程进行."""
        run = Run(
            parent_run_id=parent_run_id,
            trigger_source=trigger_source,
            trigger_reason=trigger_reason,
            trigger_confidence=trigger_confidence,
            target_id=target_id,
            target_name=target_name,
            target_type=target_type,
            scene_type=scene_type,
            scene_id=scene_id,
            scene_name=scene_name,
            status=RunStatus.TRIGGERING,
            rerun_count=rerun_count,
        )

        # 确定自动执行还是待审批
        self._set_initial_automation_status(run, trigger_confidence)

        # 构建地图联动上下文
        run.map_context = self._build_map_context(target_id, target_type, demo_target_data)

        self._store.add(run)

        # 异步执行五环节
        t = threading.Thread(
            target=self._execute_run_safe,
            args=(run.run_id, task_input or {}, demo_target_data or {}),
            daemon=True,
        )
        t.start()

        return run.run_id

    def trigger_sync(
        self,
        target_id: str,
        target_name: str,
        target_type: str,
        trigger_source: TriggerSource = TriggerSource.REALTIME,
        scene_type: SceneType = SceneType.DYNAMIC,
        trigger_reason: str = "",
        trigger_confidence: float = 1.0,
        task_input: dict[str, Any] | None = None,
        demo_target_data: dict[str, Any] | None = None,
    ) -> Run:
        """同步触发一次闭环 Run，等待完成后返回 Run 实例（仅用于调试/单元测试）."""
        run_id = self.trigger(
            target_id=target_id,
            target_name=target_name,
            target_type=target_type,
            trigger_source=trigger_source,
            scene_type=scene_type,
            trigger_reason=trigger_reason,
            trigger_confidence=trigger_confidence,
            task_input=task_input,
            demo_target_data=demo_target_data,
        )
        # 轮询等待完成（最多等 60 秒）
        for _ in range(120):
            run = self._store.get(run_id)
            if run and run.is_complete():
                return run
            time.sleep(0.5)
        return self._store.get(run_id) or Run()

    # ------------------------------------------------------------------
    # 五环节推进
    # ------------------------------------------------------------------

    def _execute_run_safe(self, run_id: str, task_input: dict, demo_target_data: dict) -> None:
        """带异常兜底的执行入口."""
        try:
            self._execute_run(run_id, task_input, demo_target_data)
        except Exception as e:
            run = self._store.get(run_id)
            if run:
                run.status = RunStatus.FAILED
                run.error_message = str(e)
                run.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._store.update(run)

    def _execute_run(self, run_id: str, task_input: dict, demo_target_data: dict) -> None:
        run = self._store.get(run_id)
        if not run:
            return

        # 若需要审批，先挂起等待（最多等 60 秒，demo 演示用）
        if run.automation_status == AutomationStatus.PENDING_APPROVAL:
            run.status = RunStatus.AWAITING_HUMAN
            self._store.update(run)
            for _ in range(60):
                time.sleep(1)
                run = self._store.get(run_id)
                if not run or run.automation_status != AutomationStatus.PENDING_APPROVAL:
                    break
            run = self._store.get(run_id)
            if not run or run.automation_status == AutomationStatus.SUSPENDED:
                return

        run.status = RunStatus.RUNNING
        self._store.update(run)

        # 从 demo 数据构建任务输入
        merged_input = self._build_task_input(run, task_input, demo_target_data)

        PHASE_NAMES = [
            "scene_cognition",
            "problem_diagnosis",
            "control_strategy",
            "plan_generation",
            "evaluation_feedback",
        ]
        PHASE_AGENTS = [
            self._scene_agent,
            self._diagnosis_agent,
            self._strategy_agent,
            self._plan_agent,
            self._eval_agent,
        ]

        ctx: dict[str, Any] = {"loop_id": run_id, "task_input": merged_input}

        for phase_name, agent in zip(PHASE_NAMES, PHASE_AGENTS):
            run = self._store.get(run_id)
            if not run:
                return
            # 被人工接管则中止自动环节
            if run.automation_status == AutomationStatus.MANUAL_TAKEOVER:
                break

            phase_rec = run.get_phase(phase_name)
            if not phase_rec:
                continue

            phase_rec.status = "running"
            phase_rec.start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            run.current_phase = phase_name
            self._store.update(run)

            t0 = time.time()
            try:
                result = agent.run({**merged_input, **ctx})
                elapsed = int(time.time() - t0)
                phase_rec.status = "ok"
                phase_rec.duration_s = elapsed
                phase_rec.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                phase_rec.output = result
                # 写摘要和证据
                self._annotate_phase(phase_rec, phase_name, result, ctx)
                # 把重要输出合并到 ctx 供下游环节消费
                self._merge_ctx(phase_name, result, ctx)
            except Exception as e:
                phase_rec.status = "failed"
                phase_rec.duration_s = int(time.time() - t0)
                phase_rec.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                phase_rec.summary = f"执行异常：{e}"
                run.error_message = str(e)

            self._store.update(run)

        # 五环节结束后处理评估结果
        self._finalize_run(run_id, ctx)

    def _annotate_phase(
        self,
        phase_rec: PhaseRecord,
        phase_name: str,
        result: dict[str, Any],
        ctx: dict[str, Any],
    ) -> None:
        """为每个阶段结果填入人类可读摘要和结构化证据."""
        if phase_name == "scene_cognition":
            profile = result.get("profile", {})
            state = profile.get("state", {})
            supply = profile.get("supply", {})
            demand = profile.get("demand", {})
            sat = state.get("saturation", ctx.get("saturation"))
            speed = state.get("avg_speed_kmh", state.get("avgSpeed"))
            delay = state.get("avg_delay_s", state.get("avgDelay"))
            phase_rec.evidence = {
                "saturation": sat,
                "avgSpeedKmh": speed,
                "avgDelayS": delay,
                "demandSupplyRatio": demand.get("demand_supply_ratio"),
                "congestionPhase": state.get("congestion_phase"),
            }
            phase_rec.summary = (
                f"三维画像已构建：饱和度 {sat}，平均车速 {speed} km/h，"
                f"平均延误 {delay}s，{supply.get('summary', '')}"
            )

        elif phase_name == "problem_diagnosis":
            issues = result.get("issues", [])
            priority = result.get("priority_order", [])
            top = priority[0] if priority else {}
            phase_rec.evidence = {
                "issueCount": len(issues),
                "topIssueId": top.get("id"),
                "topIssueName": top.get("name"),
                "topPriorityLevel": top.get("priority_level"),
            }
            phase_rec.summary = result.get("diagnosis_summary", f"诊断出 {len(issues)} 个问题")

        elif phase_name == "control_strategy":
            templates = result.get("selected_templates", [])
            top_tpl = templates[0] if templates else {}
            si = result.get("strategy_instruction", {})
            phase_rec.evidence = {
                "selectedTemplateCount": len(templates),
                "topTemplateId": top_tpl.get("template_id"),
                "topTemplateDesc": top_tpl.get("description"),
                "riskLevel": top_tpl.get("risk_level", "low"),
            }
            phase_rec.summary = (
                f"策略已选定：{top_tpl.get('description', top_tpl.get('template_id', '—'))}，"
                f"风险等级 {top_tpl.get('risk_level', 'low')}"
            )

        elif phase_name == "plan_generation":
            plans = result.get("plans", [])
            phase_rec.evidence = {
                "planCount": len(plans),
                "firstPlanId": plans[0].get("plan_id") if plans else None,
            }
            phase_rec.summary = f"已生成 {len(plans)} 套配时方案" if plans else "方案生成中"

        elif phase_name == "evaluation_feedback":
            meets = result.get("meets_target", False)
            metrics = result.get("metrics", {})
            phase_rec.evidence = {
                "meetsTarget": meets,
                "overallScore": result.get("overall_score", 0),
                "metrics": metrics,
            }
            phase_rec.summary = (
                f"评估{'达标' if meets else '未达标'}，综合评分 {result.get('overall_score', 0):.2f}"
            )

    def _merge_ctx(self, phase_name: str, result: dict[str, Any], ctx: dict[str, Any]) -> None:
        if phase_name == "scene_cognition":
            ctx["profile"] = result.get("profile", {})
        elif phase_name == "problem_diagnosis":
            ctx["issues"] = result.get("issues", [])
            ctx["priority_order"] = result.get("priority_order", [])
        elif phase_name == "control_strategy":
            ctx["strategy_instruction"] = result.get("strategy_instruction", {})
            ctx["selected_templates"] = result.get("selected_templates", [])
        elif phase_name == "plan_generation":
            ctx["plans"] = result.get("plans", [])
        elif phase_name == "evaluation_feedback":
            ctx["evaluation"] = result

    def _finalize_run(self, run_id: str, ctx: dict[str, Any]) -> None:
        run = self._store.get(run_id)
        if not run:
            return

        eval_result = ctx.get("evaluation", {})
        meets_target = eval_result.get("meets_target", False)
        metrics = eval_result.get("metrics", {})
        score = eval_result.get("overall_score", 0.0)

        # 填入评估结果
        run.effect = EffectRecord(
            evaluated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            meets_target=meets_target,
            overall_score=score,
            metrics_before=metrics.get("before", {}),
            metrics_after=metrics.get("after", {}),
            metrics_target=metrics.get("target", {}),
            improvements=eval_result.get("improvements", []),
            side_effects=eval_result.get("side_effects", []),
            conclusion="达标" if meets_target else "未达标",
            next_action=eval_result.get("next_action", "continue"),
            experience_worthy=eval_result.get("experience_worthy", False),
        )
        run.evaluation_status = (
            EvaluationStatus.MEETS_TARGET if meets_target else EvaluationStatus.NOT_MEETS
        )

        # 生成报告快照
        run.report = self._build_report_snapshot(run, ctx)

        # 经验沉淀
        if meets_target and run.effect.experience_worthy:
            run.experience = self._build_experience(run, ctx)

        # 判断是否需要复跑
        if not meets_target and run.can_rerun():
            run.evaluation_status = EvaluationStatus.RERUNNING
            run.status = RunStatus.COMPLETED
            run.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._store.update(run)
            # 触发复跑（带上本轮结论）
            self._trigger_rerun(run, ctx)
            return

        run.status = RunStatus.COMPLETED
        run.end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run.elapsed_seconds = self._calc_elapsed(run)
        self._store.update(run)

    def _trigger_rerun(self, prev_run: Run, ctx: dict[str, Any]) -> None:
        """基于上一轮结果发起复跑."""
        task_input = {
            **ctx.get("task_input", {}),
            "prev_run_id": prev_run.run_id,
            "prev_evaluation": ctx.get("evaluation", {}),
            "prev_priority_order": ctx.get("priority_order", []),
        }
        self.trigger(
            target_id=prev_run.target_id,
            target_name=prev_run.target_name,
            target_type=prev_run.target_type,
            trigger_source=TriggerSource.RERUN,
            scene_type=prev_run.scene_type,
            scene_id=prev_run.scene_id,
            scene_name=prev_run.scene_name,
            trigger_reason=f"上一轮未达标，自动复跑（第 {prev_run.rerun_count + 1} 次）",
            trigger_confidence=prev_run.trigger_confidence,
            task_input=task_input,
            parent_run_id=prev_run.run_id,
            rerun_count=prev_run.rerun_count + 1,
        )

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _set_initial_automation_status(self, run: Run, confidence: float) -> None:
        """根据置信度和风险，决定初始执行状态."""
        if confidence >= AUTO_EXEC_CONFIDENCE_THRESHOLD:
            run.automation_status = AutomationStatus.AUTO_EXEC
            run.risk_level = "low"
        else:
            run.automation_status = AutomationStatus.PENDING_APPROVAL
            run.requires_approval = True
            run.risk_level = "medium" if confidence >= 0.7 else "high"
            run.approval_reason = f"触发置信度 {confidence:.0%}，低于自动执行阈值，需人工确认"

    def _build_task_input(
        self, run: Run, extra_input: dict, demo_target_data: dict
    ) -> dict[str, Any]:
        """从 demo 对象数据构建完整任务输入，让五环节子智能体有真实数据可消费."""
        t = demo_target_data or {}
        profile_raw = t.get("profile", {})

        # 将 demo 数据中的驼峰命名转为子智能体期望的下划线命名
        supply = profile_raw.get("supply", {})
        demand = profile_raw.get("demand", {})
        state_raw = profile_raw.get("state", {})
        state = {
            "saturation": t.get("saturation") or state_raw.get("saturation"),
            "avg_speed_kmh": t.get("avgSpeed") or state_raw.get("avgSpeed"),
            "avg_delay_s": t.get("avgDelay") or state_raw.get("avgDelay"),
            "queue_overflow_ratio": state_raw.get("queueOverflowRatio"),
            "green_utilization": state_raw.get("greenUtilization"),
            "phase_imbalance_ratio": state_raw.get("phaseImbalanceRatio"),
            "congestion_phase": state_raw.get("congestionPhase"),
        }
        norm_supply = {
            "road_density_km_km2": supply.get("roadDensity"),
            "intersection_capacity": supply.get("intersectionCapacity"),
            "parking_gap_ratio": supply.get("parkingGap"),
            "channelization_match_score": supply.get("channelizationMatchScore"),
        }
        norm_demand = {
            "peak_hour_flow": demand.get("peakHourFlow"),
            "demand_supply_ratio": demand.get("demandSupplyRatio"),
            "commute_ratio": demand.get("commuteRatio"),
        }

        return {
            "target_id": run.target_id,
            "target_name": run.target_name,
            "target_type": run.target_type,
            "intersection_id": run.target_id,
            "scene_type": run.scene_type.value,
            "scene_id": run.scene_id,
            "profile": {
                "supply": norm_supply,
                "demand": norm_demand,
                "state": state,
                "summary": profile_raw.get("summary", ""),
            },
            "issues": t.get("issues", []),
            "strategies": t.get("strategies", []),
            "scope": {"type": run.target_type, "ids": [run.target_id]},
            "scenario_type": run.scene_type.value,
            **extra_input,
        }

    def _build_map_context(
        self, target_id: str, target_type: str, demo_data: dict | None
    ) -> MapContext:
        t = demo_data or {}
        affected = []
        # 对于走廊，影响对象包含所有成员路口
        if target_type == "corridor":
            affected = t.get("intersectionIds", [])
        # 对于区域，影响对象包含关联路口
        elif target_type == "region":
            issues = t.get("issues", [])
            for iss in issues:
                affected.extend(iss.get("evidence", {}).get("affectedIntersections", []))

        polygon = t.get("polygon", [])
        poi_ids = []  # 可后续从 pois 数据关联

        return MapContext(
            primary_object_id=target_id,
            primary_object_type=target_type,
            affected_object_ids=list(set(affected)),
            influence_polygon=polygon,
            poi_ids=poi_ids,
        )

    def _build_report_snapshot(self, run: Run, ctx: dict[str, Any]) -> ReportSnapshot:
        """生成结构化报告快照，供 LLM 报告生成使用."""
        profile = ctx.get("profile", {})
        state = profile.get("state", {})
        priority = ctx.get("priority_order", [])
        templates = ctx.get("selected_templates", [])
        effect = run.effect

        sat = state.get("saturation", "—")
        speed = state.get("avg_speed_kmh", "—")

        top_issue = priority[0] if priority else {}
        top_tpl = templates[0] if templates else {}

        traffic_situation = (
            f"{run.target_name}当前饱和度 {sat}，平均车速 {speed} km/h，"
            f"处于 {state.get('congestion_phase', '未知')} 阶段。"
        )
        trigger_and_findings = (
            f"由 {run.trigger_source.value} 触发（{run.trigger_reason}），"
            f"诊断发现 {len(priority)} 个问题，首要症结：{top_issue.get('name', '待确认')}。"
        )
        key_bottleneck = (
            f"首要问题 [{top_issue.get('priority_level', '')}]：{top_issue.get('name', '—')}，"
            f"成因：{top_issue.get('reason', '—')}"
        )
        strategy_and_action = (
            f"已选定策略：{top_tpl.get('description', top_tpl.get('template_id', '—'))}，"
            f"风险等级 {top_tpl.get('risk_level', 'low')}。"
        )
        effect_and_suggestion = ""
        if effect:
            effect_and_suggestion = (
                f"评估结论：{'达标' if effect.meets_target else '未达标'}，"
                f"综合评分 {effect.overall_score:.2f}。{effect.conclusion}"
            )

        return ReportSnapshot(
            traffic_situation=traffic_situation,
            trigger_and_findings=trigger_and_findings,
            od_change_analysis="",
            key_bottleneck=key_bottleneck,
            strategy_and_action=strategy_and_action,
            effect_and_suggestion=effect_and_suggestion,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _build_experience(self, run: Run, ctx: dict[str, Any]) -> ExperienceRecord:
        templates = ctx.get("selected_templates", [])
        top_tpl = templates[0] if templates else {}
        return ExperienceRecord(
            saved=True,
            tag=f"{run.target_name}_{top_tpl.get('template_id', '')}",
            scene=run.scene_name or run.scene_type.value,
            applicable_scenario=run.trigger_reason,
            recommended_params=top_tpl.get("description", ""),
            summary=f"{run.target_name}经本次优化达标，模板 {top_tpl.get('template_id', '')} 效果良好",
        )

    @staticmethod
    def _calc_elapsed(run: Run) -> int | None:
        try:
            fmt = "%Y-%m-%d %H:%M:%S"
            start = datetime.strptime(run.start_time, fmt)
            end = datetime.strptime(run.end_time, fmt)
            return int((end - start).total_seconds())
        except Exception:
            return None


# 全局单例
_orchestrator: RunOrchestrator | None = None


def get_orchestrator() -> RunOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RunOrchestrator()
    return _orchestrator
