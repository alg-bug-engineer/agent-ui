"""调试与 HTTP 层可调用的 Skill 注册表.

新增可在调试控制台调用的技能时：
1. 在本文件 ``DEBUG_SKILL_BUILDERS`` 中增加 ``skill_id -> 懒加载工厂``；
2. 在 ``docs/skills/<技能名>/api-guide.md`` 编写 API 契约（体例见 ``single-intersection-param-guidance/api-guide.md``），
   并在 ``.cursor/skills/<技能名>/SKILL.md`` 编写 Agent 技能说明（体例见 ``single-intersection-param-guidance/SKILL.md``），
   无需再为每个技能单独增加 FastAPI 路由实现文件。

``POST /v1/debug/skill/execute`` 按 ``skill_id`` 查找工厂、实例化并执行 ``execute(context)``。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.skills.base import Skill

SkillBuilder = Callable[[], Skill]


def _build_intersection_diagnosis() -> Skill:
    from src.skills.examples import IntersectionDiagnosisSkill

    return IntersectionDiagnosisSkill()


def _build_corridor_green_wave() -> Skill:
    from src.skills.examples import CorridorGreenWaveSkill

    return CorridorGreenWaveSkill()


def _build_emergency_response() -> Skill:
    from src.skills.examples import EmergencyResponseSkill

    return EmergencyResponseSkill()


def _build_region_load_balance() -> Skill:
    from src.skills.examples import RegionLoadBalanceSkill

    return RegionLoadBalanceSkill()


def _build_strategy_effect_review() -> Skill:
    from src.skills.examples import StrategyEffectReviewSkill

    return StrategyEffectReviewSkill()


def _build_diagnosis_to_strategy_template() -> Skill:
    from src.skills.examples import DiagnosisToStrategyTemplateSkill

    return DiagnosisToStrategyTemplateSkill()


def _build_multi_scenario_diagnosis_benchmark() -> Skill:
    from src.skills.examples import MultiScenarioDiagnosisBenchmarkSkill

    return MultiScenarioDiagnosisBenchmarkSkill()


def _build_single_intersection_param_guidance() -> Skill:
    from src.skills.single_intersection_param_guidance import (
        SingleIntersectionParamGuidanceSkill,
    )

    return SingleIntersectionParamGuidanceSkill()


# skill_id 必须与各 Skill.manifest.id 一致
DEBUG_SKILL_BUILDERS: dict[str, SkillBuilder] = {
    "intersection_diagnosis": _build_intersection_diagnosis,
    "corridor_green_wave": _build_corridor_green_wave,
    "emergency_response": _build_emergency_response,
    "region_load_balance": _build_region_load_balance,
    "strategy_effect_review": _build_strategy_effect_review,
    "diagnosis_to_strategy_template": _build_diagnosis_to_strategy_template,
    "multi_scenario_diagnosis_benchmark": _build_multi_scenario_diagnosis_benchmark,
    "single_intersection_param_guidance": _build_single_intersection_param_guidance,
}


def build_debug_skill(skill_id: str) -> Skill | None:
    """按 id 构造 Skill 实例；未知 id 返回 None（不抛异常）。"""
    factory = DEBUG_SKILL_BUILDERS.get(skill_id)
    if factory is None:
        return None
    return factory()


def list_debug_skill_manifests() -> list[dict[str, Any]]:
    """列出注册表中技能的 manifest 摘要（每次列表会短暂实例化以读取声明）。"""
    rows: list[dict[str, Any]] = []
    for sid in sorted(DEBUG_SKILL_BUILDERS):
        skill = DEBUG_SKILL_BUILDERS[sid]()
        m = skill.manifest
        rows.append(
            {
                "id": m.id,
                "version": m.version,
                "description": m.description,
            }
        )
    return rows
