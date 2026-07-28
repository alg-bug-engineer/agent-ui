"""单路口求解参数指导技能：说明「何种诊断/场景下应如何取值」，不求解."""

from __future__ import annotations

import copy
import logging
from typing import Any

from src.common.models import TriggerMode
from src.config.business_rules_loader import get_business_rules
from src.planning.single_point import DEFAULT_SINGLE_POINT_CONFIG
from src.skills.base import Skill, SkillManifest
from src.skills.single_intersection_optimization import (
    compute_adapted_params_from_issues,
    enforce_adapted_hard_constraints,
    filter_intersection_trigger_issues,
    load_single_intersection_optimization_config,
)
from src.sub_agents.problem_diagnosis import ProblemDiagnosisAgent
from src.support.mcp_tools import MCPToolRegistry, diagnosis_tool

logger = logging.getLogger(__name__)


def load_param_guidance_rules() -> dict[str, Any]:
    """读取 ``single_intersection_param_guidance`` 业务配置段."""
    try:
        rules = get_business_rules()
        raw = rules.get("single_intersection_param_guidance")
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _priority_order_from_issue_ids(issue_ids: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in issue_ids:
        if not isinstance(raw, str):
            continue
        iid = raw.strip()
        if not iid:
            continue
        out.append(
            {
                "id": iid,
                "priority_level": "P1",
                "priority_score": 0.8,
                "category": "manual",
                "evidence": [{"source": "issue_ids_input"}],
            }
        )
    return out


def _rationale_lines(adapted: dict[str, dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for name, meta in adapted.items():
        val = meta.get("value")
        reason = meta.get("reason", "")
        default = meta.get("default")
        lines.append(
            f"{name}={val}（默认 {default}，由问题码 {reason} 驱动调整）"
        )
    return lines


def _merge_scenario_suggested(
    issue_driven: dict[str, dict[str, Any]],
    suggested: dict[str, Any],
    scenario_type: str,
) -> dict[str, dict[str, Any]]:
    merged = copy.deepcopy(issue_driven)
    for param, raw_val in suggested.items():
        if not isinstance(raw_val, (int, float)):
            continue
        prev = merged.get(param)
        if prev:
            cast_type = type(prev["value"])
            merged[param] = {
                "value": cast_type(raw_val),
                "reason": f"{prev['reason']}+scenario:{scenario_type}",
                "default": prev.get("default"),
            }
        else:
            merged[param] = {
                "value": raw_val,
                "reason": f"scenario:{scenario_type}",
                "default": DEFAULT_SINGLE_POINT_CONFIG.get(param),
            }
    enforce_adapted_hard_constraints(merged)
    return merged


class SingleIntersectionParamGuidanceSkill(Skill):
    """根据诊断问题码（及可选场景标签）解释并给出求解器参数建议."""

    manifest = SkillManifest(
        id="single_intersection_param_guidance",
        version="1.0.0",
        description=(
            "单路口配时参数指导：说明当前诊断/场景下各求解参数建议取值及理由，"
            "不调用数值优化；可与 single_intersection_optimization 配合用于工程配置与复核"
        ),
        trigger_mode=TriggerMode.DISPATCH,
        trigger_threshold={},
        required_tools=["problem_diagnosis"],
        input_schema={
            "interId": "string(optional)",
            "profile": "object(optional)",
            "priority_order": "array(optional)",
            "issue_ids": "array(optional)",
            "scenario_type": "string(optional)",
            "apply_scenario_overlay": "boolean(optional)",
        },
        output_schema={
            "issue_driven_params": "object",
            "scenario_guidance": "object",
            "rationale_lines": "array",
        },
    )

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """输入三选一：``issue_ids`` / ``priority_order`` / 仅画像触发内置诊断。"""
        diagnosis_summary = ""
        priority_order: list[dict[str, Any]] | None = None

        issue_ids = context.get("issue_ids")
        if issue_ids is not None:
            if not isinstance(issue_ids, list):
                return {
                    "skill_id": self.manifest.id,
                    "success": False,
                    "error": "issue_ids 必须为字符串列表",
                }
            priority_order = _priority_order_from_issue_ids(issue_ids)

        if priority_order is None:
            priority_order = context.get("priority_order")

        if not priority_order:
            registry = MCPToolRegistry()
            registry.register("diagnosis_tool", diagnosis_tool)
            diagnosis_agent = ProblemDiagnosisAgent(mcp_tools=registry)
            dres = diagnosis_agent.run(context)
            priority_order = dres.get("priority_order", [])
            diagnosis_summary = dres.get("diagnosis_summary", "")

        if not isinstance(priority_order, list):
            priority_order = []

        sio_cfg = load_single_intersection_optimization_config()
        intersection_issues = filter_intersection_trigger_issues(
            priority_order, sio_cfg
        )
        issue_driven = compute_adapted_params_from_issues(
            intersection_issues, sio_cfg
        )

        guidance_cfg = load_param_guidance_rules()
        scenario_type = str(context.get("scenario_type", "normal")).strip() or "normal"
        hints = guidance_cfg.get("scenario_hints") or {}
        scenario_block: dict[str, Any] = {}
        if isinstance(hints, dict):
            raw_block = hints.get(scenario_type)
            if isinstance(raw_block, dict):
                scenario_block = raw_block
            elif isinstance(hints.get("default"), dict):
                scenario_block = hints["default"]

        summary = str(scenario_block.get("summary", ""))
        suggested_raw = scenario_block.get("suggested_constraints") or {}
        suggested_constraints: dict[str, Any] = {
            k: v
            for k, v in suggested_raw.items()
            if isinstance(v, (int, float))
        }

        apply_overlay = bool(context.get("apply_scenario_overlay"))
        merged_recommendation: dict[str, dict[str, Any]] | None = None
        if apply_overlay and suggested_constraints:
            merged_recommendation = _merge_scenario_suggested(
                issue_driven, suggested_constraints, scenario_type
            )

        lines = _rationale_lines(issue_driven)
        if summary:
            lines.insert(0, f"场景「{scenario_type}」：{summary}")
        if apply_overlay and merged_recommendation:
            lines.append(
                "已按 apply_scenario_overlay 合并场景建议约束（见 merged_recommendation）。"
            )

        logger.info(
            "单路口参数指导: scenario=%s issues=%s params=%s",
            scenario_type,
            [i.get("id") for i in intersection_issues],
            list(issue_driven.keys()),
        )

        return {
            "skill_id": self.manifest.id,
            "success": True,
            "scenario_type": scenario_type,
            "diagnosis_summary": diagnosis_summary
            or context.get("diagnosis_summary", ""),
            "intersection_issues": intersection_issues,
            "issue_driven_params": issue_driven,
            "scenario_guidance": {
                "matched": bool(scenario_block),
                "summary": summary,
                "suggested_constraints": suggested_constraints,
            },
            "apply_scenario_overlay": apply_overlay,
            "merged_recommendation": merged_recommendation,
            "rationale_lines": lines,
        }
