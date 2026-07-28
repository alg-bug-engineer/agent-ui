"""四大场景管控子智能体：区域 / 干线 / 路口 / 应急.

承接控制策略子智能体的全局策略，生成场景化、精细化管控子策略，
反馈至方案生成子智能体做针对性配时方案设计。对应「一区一策、一路一策、一口一策」.
"""

from src.common.models import ControlLevel
from src.sub_agents.base import BaseSubAgent


class RegionControlAgent(BaseSubAgent):
    """区域级管控子智能体：全域负荷均衡、拥堵扩散防控."""

    name = "region_control"
    control_level = ControlLevel.REGION

    def run(self, task_input: dict) -> dict:
        """生成区域级管控子策略."""
        return {"phase": "region_control", "sub_strategy": {}, "success": True}


class CorridorControlAgent(BaseSubAgent):
    """干线级管控子智能体：连续通行、潮汐车流适配."""

    name = "corridor_control"
    control_level = ControlLevel.CORRIDOR

    def run(self, task_input: dict) -> dict:
        """生成干线级管控子策略."""
        return {"phase": "corridor_control", "sub_strategy": {}, "success": True}


class IntersectionControlAgent(BaseSubAgent):
    """路口级管控子智能体：精细化配时与机非人冲突防控."""

    name = "intersection_control"
    control_level = ControlLevel.INTERSECTION

    def run(self, task_input: dict) -> dict:
        """生成路口级管控子策略."""
        return {"phase": "intersection_control", "sub_strategy": {}, "success": True}


class EmergencyControlAgent(BaseSubAgent):
    """应急管控子智能体：事故/恶劣天气/大型活动等异常场景，截流分流与外部应急联动."""

    name = "emergency_control"
    control_level = ControlLevel.EMERGENCY

    def run(self, task_input: dict) -> dict:
        """生成应急管控子策略，联动外部应急工具."""
        return {"phase": "emergency_control", "sub_strategy": {}, "success": True}
