"""五环节闭环执行与迭代 - 对应方法论图 2 与架构 8.2 节."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.common.models import LoopPhase
from src.master_agent import MasterAgent
from src.skills.base import SkillRegistry
from src.sub_agents import (
    SceneCognitionAgent,
    ProblemDiagnosisAgent,
    ControlStrategyAgent,
    PlanGenerationAgent,
    EvaluationFeedbackAgent,
)

logger = logging.getLogger(__name__)


class FivePhaseLoop:
    """五环节闭环：单轮执行与未达标时触发新一轮闭环."""

    def __init__(
        self,
        master: MasterAgent,
        scene_agent: SceneCognitionAgent | None = None,
        diagnosis_agent: ProblemDiagnosisAgent | None = None,
        strategy_agent: ControlStrategyAgent | None = None,
        plan_agent: PlanGenerationAgent | None = None,
        evaluation_agent: EvaluationFeedbackAgent | None = None,
        skill_registry: SkillRegistry | None = None,
    ):
        self.master = master
        self.scene = scene_agent or SceneCognitionAgent()
        self.diagnosis = diagnosis_agent or ProblemDiagnosisAgent()
        self.strategy = strategy_agent or ControlStrategyAgent()
        self.plan = plan_agent or PlanGenerationAgent()
        self.evaluation = evaluation_agent or EvaluationFeedbackAgent()
        self.skill_registry = skill_registry

    def run_one_cycle(self, task_input: dict[str, Any], loop_id: str | None = None) -> dict:
        """执行一轮五环节闭环."""
        loop_id = loop_id or str(uuid.uuid4())
        ctx = {"loop_id": loop_id, "task_input": task_input}

        # 1. 场景认知
        r1 = self.scene.run(task_input)
        ctx["profile"] = r1.get("profile", {})
        self.master.coordinate_phase_output(LoopPhase.SCENE_COGNITION.value, r1, loop_id)

        # 2. 问题诊断
        r2 = self.diagnosis.run({**task_input, "profile": ctx["profile"]})
        ctx["issues"] = r2.get("issues", [])
        ctx["priority_order"] = r2.get("priority_order", [])
        self.master.coordinate_phase_output(LoopPhase.PROBLEM_DIAGNOSIS.value, r2, loop_id)

        # 3. 控制策略
        r3 = self.strategy.run({**task_input, **ctx})
        ctx["strategy_instruction"] = r3.get("strategy_instruction", {})
        self.master.coordinate_phase_output(LoopPhase.CONTROL_STRATEGY.value, r3, loop_id)

        # 3.5 技能调度：诊断后若匹配到专业 Skill 则优先使用其方案
        skill_used = False
        if self.skill_registry:
            skill_event = {
                "priority_order": ctx.get("priority_order", []),
                "scope": task_input.get("scope", {}),
                **ctx,
            }
            matched = self.skill_registry.match_skills(skill_event)
            for skill in matched:
                logger.info("Skill 调度: %s", skill.manifest.id)
                skill_result = skill.execute({**task_input, **ctx})
                ctx.setdefault("skill_results", []).append(skill_result)
                if skill_result.get("plans"):
                    ctx["plans"] = skill_result["plans"]
                    skill_used = True

        # 4. 方案生成（若 Skill 已生成方案则跳过默认方案生成）
        if skill_used:
            r4 = {
                "phase": "plan_generation",
                "plans": ctx.get("plans", []),
                "compiled_for_device": {},
                "success": True,
                "meta": {"skill_override": True},
            }
        else:
            r4 = self.plan.run({**task_input, **ctx})
        ctx["plans"] = r4.get("plans", [])
        self.master.coordinate_phase_output(LoopPhase.PLAN_GENERATION.value, r4, loop_id)

        # 5. 评价反馈
        r5 = self.evaluation.run({**task_input, **ctx})
        ctx["evaluation"] = r5
        self.master.coordinate_phase_output(LoopPhase.EVALUATION_FEEDBACK.value, r5, loop_id)

        return {
            "loop_id": loop_id,
            "phases": [r1, r2, r3, r4, r5],
            "meets_target": r5.get("meets_target", False),
            "context": ctx,
        }


def run_loop_once(
    task_input: dict[str, Any],
    master: MasterAgent | None = None,
    loop: FivePhaseLoop | None = None,
    skill_registry: SkillRegistry | None = None,
) -> dict:
    """便捷函数：执行单轮五环节闭环."""
    master = master or MasterAgent()
    loop = loop or FivePhaseLoop(master=master, skill_registry=skill_registry)
    return loop.run_one_cycle(task_input)
