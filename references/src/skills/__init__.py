"""Skill 技能化架构：可声明、可组合、可热更新的技能包."""

from src.skills.base import Skill, SkillRegistry
from src.skills.examples import (
    IntersectionDiagnosisSkill,
    CorridorGreenWaveSkill,
    EmergencyResponseSkill,
    RegionLoadBalanceSkill,
    StrategyEffectReviewSkill,
    DiagnosisToStrategyTemplateSkill,
    MultiScenarioDiagnosisBenchmarkSkill,
)
from src.skills.single_intersection_param_guidance import (
    SingleIntersectionParamGuidanceSkill,
)

__all__ = [
    "Skill",
    "SkillRegistry",
    "IntersectionDiagnosisSkill",
    "CorridorGreenWaveSkill",
    "EmergencyResponseSkill",
    "RegionLoadBalanceSkill",
    "StrategyEffectReviewSkill",
    "DiagnosisToStrategyTemplateSkill",
    "MultiScenarioDiagnosisBenchmarkSkill",
    "SingleIntersectionParamGuidanceSkill",
]
