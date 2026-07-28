"""单路口信号优化技能：诊断驱动的配时参数自适应 + SciPy SLSQP 求解.

端到端流程：
    问题诊断 → 过滤 intersection 级问题 → 参数自适应 → 配时求解 → 质量评估

支持两种触发路径：
    1. SkillRegistry dispatch / 直接实例化
    2. FivePhaseLoop 中自动触发
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from src.common.models import TriggerMode
from src.config.business_rules_loader import get_business_rules
from src.planning.single_point import (
    DEFAULT_SINGLE_POINT_CONFIG,
    generate_single_point_plan,
)
from src.skills.base import Skill, SkillManifest
from src.sub_agents.control_strategy import ControlStrategyAgent
from src.sub_agents.problem_diagnosis import ProblemDiagnosisAgent
from src.support.mcp_tools import MCPToolRegistry, diagnosis_tool

logger = logging.getLogger(__name__)

INTERSECTION_TRIGGER_ISSUE_CODES: set[str] = {
    "signal_queue_overflow",
    "signal_green_waste",
    "signal_phase_imbalance",
    "dynamic_high_saturation",
    "dynamic_high_delay",
    "static_channelization_mismatch",
}

_PRIORITY_LEVEL_RANK: dict[str, int] = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

_DEFAULT_SKILL_CONFIG: dict[str, Any] = {
    "trigger": {
        "enabled": True,
        "issue_codes": list(INTERSECTION_TRIGGER_ISSUE_CODES),
        "min_priority_level": "P2",
    },
    "issue_param_adjustments": {
        "signal_queue_overflow": {
            "target_saturation": 0.75,
            "over_target_penalty_weight": 30.0,
        },
        "signal_green_waste": {
            "default_cycle_s": 90,
            "target_saturation_min": 0.55,
        },
        "signal_phase_imbalance": {
            "intensity_std_penalty_weight": 15.0,
        },
        "dynamic_high_delay": {
            "default_cycle_s": 100,
            "min_green_s": 15,
        },
        "dynamic_high_saturation": {
            "target_saturation": 0.78,
        },
        "static_channelization_mismatch": {
            "intensity_std_penalty_weight": 12.0,
        },
    },
    "quality_thresholds": {
        "max_phase_saturation_warn": 0.95,
        "max_phase_saturation_reject": 1.05,
    },
    "merge_strategy": "priority_first",
}


def load_single_intersection_optimization_config() -> dict[str, Any]:
    """加载单路口优化技能配置（与 SingleIntersectionOptimizationSkill 内部一致）."""
    try:
        rules = get_business_rules()
        cfg = rules.get("single_intersection_optimization", {})
        if cfg:
            return cfg
    except Exception:
        pass
    return copy.deepcopy(_DEFAULT_SKILL_CONFIG)


def filter_intersection_trigger_issues(
    priority_order: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """从 priority_order 中筛出参与单路口参数映射的问题项."""
    trigger_codes = set(
        cfg.get("trigger", {}).get("issue_codes", INTERSECTION_TRIGGER_ISSUE_CODES)
    )
    filtered: list[dict[str, Any]] = []
    for issue in priority_order:
        issue_id = issue.get("id", "")
        if issue_id in trigger_codes:
            filtered.append(issue)
    return filtered


def enforce_adapted_hard_constraints(adapted: dict[str, dict[str, Any]]) -> None:
    """对自适应参数字典就地施加安全上下限（与优化技能一致）."""
    hard_limits: dict[str, tuple[float, float]] = {
        "min_green_s": (5, 60),
        "target_saturation": (0.3, 0.98),
        "target_saturation_min": (0.3, 0.98),
        "target_saturation_max": (0.3, 0.99),
        "max_cycle_s": (30, 300),
        "default_cycle_s": (30, 300),
    }
    for param, entry in adapted.items():
        if param in hard_limits:
            lo, hi = hard_limits[param]
            clamped = max(lo, min(hi, float(entry["value"])))
            entry["value"] = type(entry["value"])(clamped)


def compute_adapted_params_from_issues(
    intersection_issues: list[dict[str, Any]],
    cfg: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """根据诊断问题列表计算求解器参数覆盖（不求解）.

    返回结构与 ``adapted_params`` 一致：``{param_name: {value, reason, default}}``。
    """
    adjustments_map = cfg.get("issue_param_adjustments", {})
    merge_strategy = cfg.get("merge_strategy", "priority_first")

    adapted: dict[str, dict[str, Any]] = {}

    for issue in intersection_issues:
        issue_id = issue.get("id", "")
        issue_adjustments = adjustments_map.get(issue_id, {})
        if not issue_adjustments:
            continue

        for param, value in issue_adjustments.items():
            if param in adapted and merge_strategy == "priority_first":
                continue
            if param in adapted and merge_strategy == "conservative_min":
                if float(value) >= float(adapted[param]["value"]):
                    continue
            if param in adapted and merge_strategy == "aggressive_max":
                if float(value) <= float(adapted[param]["value"]):
                    continue

            default_val = DEFAULT_SINGLE_POINT_CONFIG.get(param)
            adapted[param] = {
                "value": value,
                "reason": issue_id,
                "default": default_val,
            }

    enforce_adapted_hard_constraints(adapted)

    if adapted:
        logger.info(
            "单路口参数映射(问题码→求解器参数): %s",
            {k: v["value"] for k, v in adapted.items()},
        )

    return adapted


class SingleIntersectionOptimizationSkill(Skill):
    """单路口信号优化技能：诊断驱动参数自适应 + 配时方案生成 + 质量评估."""

    manifest = SkillManifest(
        id="single_intersection_optimization",
        version="1.0.0",
        description=(
            "单路口配时优化：根据问题诊断结果自适应调整求解器参数，"
            "生成经过质量评估的信号配时方案"
        ),
        trigger_mode=TriggerMode.SCENARIO_MATCH,
        trigger_threshold={"scope_type": "intersection"},
        required_tools=[
            "problem_diagnosis",
            "control_strategy",
            "single_point_plan_tool",
        ],
        input_schema={
            "interId": "string",
            "phasePlanOfTimeList": "array|dict(optional)",
            "parameter_json_str": "string|dict(optional)",
            "profile": "object(optional)",
            "priority_order": "array(optional)",
            "constraints": "object(optional)",
        },
        output_schema={
            "plans": "array",
            "adapted_params": "object",
            "quality_check": "object",
            "diagnosis_summary": "string",
        },
    )

    def check_trigger(self, event: dict[str, Any]) -> bool:
        """判断事件是否应触发本技能.

        触发条件：
        1. scope 为 intersection 级别
        2. priority_order 中存在可触发的问题码
        3. 至少一个问题的优先级 >= P2
        """
        scope = event.get("scope", {})
        if isinstance(scope, dict) and scope.get("type") not in (
            "intersection",
            None,
        ):
            if scope.get("type") != "intersection":
                return False

        priority_order = event.get("priority_order", [])
        if not isinstance(priority_order, list) or not priority_order:
            return False

        cfg = self._load_skill_config()
        trigger_codes = set(cfg.get("trigger", {}).get(
            "issue_codes", INTERSECTION_TRIGGER_ISSUE_CODES
        ))
        min_level = cfg.get("trigger", {}).get("min_priority_level", "P2")
        min_rank = _PRIORITY_LEVEL_RANK.get(min_level, 2)

        for issue in priority_order:
            issue_id = issue.get("id", "")
            level = issue.get("priority_level", "P3")
            level_rank = _PRIORITY_LEVEL_RANK.get(level, 3)
            if issue_id in trigger_codes and level_rank <= min_rank:
                return True

        return False

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """执行单路口优化全流程."""
        priority_order = context.get("priority_order")
        diagnosis_summary = ""
        diagnosis_result: dict[str, Any] = {}

        if not priority_order:
            registry = MCPToolRegistry()
            registry.register("diagnosis_tool", diagnosis_tool)
            diagnosis_agent = ProblemDiagnosisAgent(mcp_tools=registry)
            diagnosis_result = diagnosis_agent.run(context)
            priority_order = diagnosis_result.get("priority_order", [])
            diagnosis_summary = diagnosis_result.get("diagnosis_summary", "")

        intersection_issues = filter_intersection_trigger_issues(
            priority_order, self._load_skill_config()
        )

        strategy_result: dict[str, Any] = {}
        selected_templates: list[dict[str, Any]] = []
        if intersection_issues:
            strategy_agent = ControlStrategyAgent()
            strategy_result = strategy_agent.run(
                {
                    "scenario_type": context.get("scenario_type", "normal"),
                    "scope": context.get("scope", {}),
                    "priority_order": intersection_issues,
                    "target_priority": context.get("target_priority", []),
                }
            )
            selected_templates = strategy_result.get("selected_templates", [])

        adapted_params = self._adapt_config_from_diagnosis(intersection_issues)

        plan_request = self._build_plan_request(context, adapted_params)
        plan_result = generate_single_point_plan(plan_request)

        quality_check = self._evaluate_quality(plan_result)

        return {
            "skill_id": self.manifest.id,
            "success": not plan_result.get("isError", False),
            "diagnosis_summary": diagnosis_summary
            or context.get("diagnosis_summary", ""),
            "intersection_issues": intersection_issues,
            "adapted_params": adapted_params,
            "selected_templates": selected_templates,
            "strategy_instruction": strategy_result.get(
                "strategy_instruction", {}
            ),
            "plans": [plan_result],
            "quality_check": quality_check,
        }

    def _adapt_config_from_diagnosis(
        self, intersection_issues: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """根据诊断问题码自适应调整求解器参数.

        返回值结构：{param_name: {value, reason, default}}
        """
        return compute_adapted_params_from_issues(
            intersection_issues, self._load_skill_config()
        )

    def _build_plan_request(
        self,
        context: dict[str, Any],
        adapted_params: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """构造送入 generate_single_point_plan 的请求."""
        constraints = dict(context.get("constraints", {}) or {})
        for param, entry in adapted_params.items():
            constraints[param] = entry["value"]

        strategy_instruction = context.get("strategy_instruction", {})
        if isinstance(strategy_instruction, dict):
            strategy_instruction = dict(strategy_instruction)
        else:
            strategy_instruction = {}
        for param, entry in adapted_params.items():
            if param not in strategy_instruction:
                strategy_instruction[param] = entry["value"]

        request: dict[str, Any] = {}
        for key in (
            "interId",
            "intersection_id",
            "phasePlanOfTimeList",
            "parameter_json_str",
            "parameterJsonStr",
            "obj_intensity",
        ):
            if key in context:
                request[key] = context[key]

        if "interId" not in request and "intersection_id" in context:
            request["interId"] = context["intersection_id"]

        request["constraints"] = constraints
        request["strategy_instruction"] = strategy_instruction

        return request

    def _evaluate_quality(
        self, plan_result: dict[str, Any]
    ) -> dict[str, Any]:
        """评估方案质量."""
        cfg = self._load_skill_config()
        thresholds = cfg.get("quality_thresholds", {})
        warn_threshold = float(thresholds.get("max_phase_saturation_warn", 0.95))
        reject_threshold = float(
            thresholds.get("max_phase_saturation_reject", 1.05)
        )

        meta = plan_result.get("meta", {})
        max_sat = float(meta.get("max_phase_saturation", 0.0))

        warnings: list[str] = []
        rejected = False

        if plan_result.get("isError"):
            return {
                "passed": False,
                "max_phase_saturation": max_sat,
                "warnings": ["方案生成报错"],
                "rejected": True,
            }

        if max_sat > reject_threshold:
            rejected = True
            warnings.append(
                f"最大阶段饱和度 {max_sat:.4f} 超过拒绝阈值 {reject_threshold}，"
                "建议人工复核或放宽周期/流量约束"
            )
        elif max_sat > warn_threshold:
            warnings.append(
                f"最大阶段饱和度 {max_sat:.4f} 超过警告阈值 {warn_threshold}，"
                "建议复核流量数据"
            )

        return {
            "passed": not rejected,
            "max_phase_saturation": max_sat,
            "warnings": warnings,
            "rejected": rejected,
        }

    def _load_skill_config(self) -> dict[str, Any]:
        """加载技能配置，优先从 business_rules 读取."""
        return load_single_intersection_optimization_config()
