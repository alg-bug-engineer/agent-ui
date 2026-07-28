"""场景认知子智能体：城市交通全维度 CT 体检.

对应五环节闭环的「场景认知」环节，构建供给-需求-状态三维画像，实现交通态势全息感知.
"""

from __future__ import annotations

from typing import Any

from src.common.models import SupplyDemandStateProfile
from src.sub_agents.base import BaseSubAgent

# 规律性场景标签库（场景 ID -> 标签）
_PERIODIC_SCENE_LABELS = {
    "SCN-COMMUTE": "通勤主导型",
    "SCN-SCHOOL": "学校接送型",
    "SCN-HOSPITAL": "医疗就诊型",
    "SCN-MALL": "商业活动型",
}

# 信控问题类别列表
_SIGNAL_ISSUE_CATEGORIES = {"signal_control"}


class SceneCognitionAgent(BaseSubAgent):
    """场景认知子智能体：交通供给分析、需求分析、状态分析、三维画像生成."""

    name = "scene_cognition"

    def run(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """执行场景认知任务，输出三维画像与态势总结.

        优先从 task_input 中提取已有的 profile 数据（来自 demo 对象数据），
        在此基础上补充派生指标、场景标签、自然语言摘要，确保输出不再为空。
        """
        profile = self._build_three_dimension_profile(task_input)
        scene_tags = self._detect_scene_tags(task_input, profile)
        diagnosis_type = self._classify_diagnosis_type(task_input, profile)
        summary = self._build_summary(task_input, profile, scene_tags, diagnosis_type)

        return {
            "phase": "scene_cognition",
            "profile": {
                **profile.model_dump(),
                "sceneTags": scene_tags,
                "diagnosisType": diagnosis_type,
                "summary": summary,
            },
            "scene_tags": scene_tags,
            "diagnosis_type": diagnosis_type,
            "summary": summary,
            "success": True,
        }

    def _build_three_dimension_profile(self, task_input: dict[str, Any]) -> SupplyDemandStateProfile:
        """构建供给-需求-状态三维画像.

        1.0 版本：优先从 task_input["profile"] 读取 demo 数据已有结构；
        若缺失则从 task_input 根层兼容字段构建。
        """
        raw = task_input.get("profile", {})
        if not isinstance(raw, dict):
            raw = {}

        supply = self._extract_supply(raw, task_input)
        demand = self._extract_demand(raw, task_input)
        state = self._extract_state(raw, task_input)

        # 派生指标
        self._enrich_state(state, supply, demand)

        return SupplyDemandStateProfile(
            supply=supply,
            demand=demand,
            state=state,
            summary="",  # 摘要由上层生成
        )

    # ------------------------------------------------------------------
    # 三维提取
    # ------------------------------------------------------------------

    def _extract_supply(self, raw: dict, task_input: dict) -> dict[str, Any]:
        """提取供给维度指标（路网密度、通行能力、停车供给等）."""
        raw_supply = raw.get("supply", {})
        return {
            "road_density_km_km2": self._coerce_float(
                raw_supply.get("road_density_km_km2")
                or raw_supply.get("roadDensity")
            ),
            "intersection_capacity": self._coerce_float(
                raw_supply.get("intersection_capacity")
                or raw_supply.get("intersectionCapacity")
            ),
            "parking_gap_ratio": self._coerce_float(
                raw_supply.get("parking_gap_ratio")
                or raw_supply.get("parkingGap")
            ),
            "channelization_match_score": self._coerce_float(
                raw_supply.get("channelization_match_score")
                or raw_supply.get("channelizationMatchScore")
            ),
            "road_density_level": self._classify_road_density(
                self._coerce_float(raw_supply.get("road_density_km_km2") or raw_supply.get("roadDensity"))
            ),
        }

    def _extract_demand(self, raw: dict, task_input: dict) -> dict[str, Any]:
        raw_demand = raw.get("demand", {})
        return {
            "peak_hour_flow": self._coerce_float(
                raw_demand.get("peak_hour_flow") or raw_demand.get("peakHourFlow")
            ),
            "demand_supply_ratio": self._coerce_float(
                raw_demand.get("demand_supply_ratio") or raw_demand.get("demandSupplyRatio")
            ),
            "commute_ratio": self._coerce_float(
                raw_demand.get("commute_ratio") or raw_demand.get("commuteRatio")
            ),
        }

    def _extract_state(self, raw: dict, task_input: dict) -> dict[str, Any]:
        raw_state = raw.get("state", {})
        return {
            "saturation": self._coerce_float(
                raw_state.get("saturation")
                or task_input.get("saturation")
            ),
            "avg_speed_kmh": self._coerce_float(
                raw_state.get("avg_speed_kmh")
                or raw_state.get("avgSpeed")
                or task_input.get("avgSpeed")
            ),
            "avg_delay_s": self._coerce_float(
                raw_state.get("avg_delay_s")
                or raw_state.get("avgDelay")
                or task_input.get("avgDelay")
            ),
            "queue_overflow_ratio": self._coerce_float(
                raw_state.get("queue_overflow_ratio")
                or raw_state.get("queueOverflowRatio")
            ),
            "green_utilization": self._coerce_float(
                raw_state.get("green_utilization")
            ),
            "phase_imbalance_ratio": self._coerce_float(
                raw_state.get("phase_imbalance_ratio")
                or raw_state.get("phaseImbalanceRatio")
            ),
            "congestion_phase": (
                raw_state.get("congestion_phase")
                or raw_state.get("congestionPhase")
                or "未知"
            ),
        }

    def _enrich_state(self, state: dict, supply: dict, demand: dict) -> None:
        """派生补充指标."""
        sat = state.get("saturation")
        if sat is not None:
            state["congestion_level"] = (
                "严重" if sat >= 0.90
                else "预警" if sat >= 0.80
                else "轻度" if sat >= 0.65
                else "正常"
            )
        dsr = demand.get("demand_supply_ratio")
        if dsr is not None:
            state["demand_pressure"] = "高" if dsr > 1.1 else "中" if dsr > 0.9 else "低"

    # ------------------------------------------------------------------
    # 场景识别
    # ------------------------------------------------------------------

    def _detect_scene_tags(self, task_input: dict, profile: SupplyDemandStateProfile) -> list[str]:
        """识别场景标签：通勤/学校/医院/商圈/信控/动态。"""
        tags: list[str] = []
        scene_id = task_input.get("scene_id", "")
        if scene_id in _PERIODIC_SCENE_LABELS:
            tags.append(_PERIODIC_SCENE_LABELS[scene_id])
        commute = profile.demand.get("commute_ratio", 0) or 0
        if commute > 0.6:
            tags.append("通勤主导型")
        elif commute > 0.4:
            tags.append("混合出行型")
        else:
            tags.append("商业吸引型")

        issues = task_input.get("issues", [])
        has_signal = any(i.get("category") in _SIGNAL_ISSUE_CATEGORIES for i in issues)
        has_dynamic = any(i.get("category") == "dynamic" for i in issues)
        has_static = any(i.get("category") == "static" for i in issues)

        if has_signal:
            tags.append("信控问题型")
        if has_dynamic:
            tags.append("动态需求型")
        if has_static:
            tags.append("结构性短板型")
        return list(dict.fromkeys(tags))  # 去重保序

    def _classify_diagnosis_type(self, task_input: dict, profile: SupplyDemandStateProfile) -> str:
        """区分规律性诊断或实时运行诊断."""
        scene_type = task_input.get("scene_type", "dynamic")
        sat = profile.state.get("saturation") or 0
        if scene_type == "periodic":
            return "规律性需求型"
        if sat >= 0.88:
            return "实时运行型"
        if sat >= 0.75:
            return "动态预警型"
        return "规律性监测型"

    def _build_summary(
        self,
        task_input: dict,
        profile: SupplyDemandStateProfile,
        tags: list[str],
        diag_type: str,
    ) -> str:
        """生成三维画像的自然语言摘要."""
        name = task_input.get("target_name", "")
        sat = profile.state.get("saturation")
        speed = profile.state.get("avg_speed_kmh")
        delay = profile.state.get("avg_delay_s")
        phase = profile.state.get("congestion_phase", "")
        dsr = profile.demand.get("demand_supply_ratio")
        tag_str = "、".join(tags[:2]) if tags else "未知场景"

        parts = []
        if name:
            parts.append(f"{name}被识别为「{tag_str}」，诊断类型：{diag_type}。")
        if sat is not None:
            parts.append(f"当前饱和度 {sat:.2f}，平均车速 {speed} km/h，平均延误 {delay}s，处于{phase}阶段。")
        if dsr is not None:
            parts.append(f"供需比 {dsr:.2f}，{'需求明显超出供给能力' if dsr > 1.1 else '供需基本平衡'}。")
        return "".join(parts) or "已完成场景认知，三维画像构建成功。"

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_float(v: Any) -> float | None:
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _classify_road_density(density: float | None) -> str:
        if density is None:
            return "未知"
        if density >= 10:
            return "高密度"
        if density >= 7:
            return "中密度"
        return "低密度"
