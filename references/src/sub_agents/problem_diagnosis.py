"""问题诊断子智能体：精准定位拥堵与信控核心症结.

对应五环节闭环「问题诊断」环节：
1) 区分静态短板与动态问题；
2) 识别信控单点/区域干线问题；
3) 生成可解释的优先级排序，供控制策略环节直接消费。
"""

from __future__ import annotations

from typing import Any

from src.config.business_rules_loader import get_business_rules
from src.sub_agents.base import BaseSubAgent


class ProblemDiagnosisAgent(BaseSubAgent):
    """问题诊断子智能体：拥堵成因诊断、信控问题诊断、症结优先级排序."""

    name = "problem_diagnosis"

    def run(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """执行问题诊断，输出症结列表与优先级.

        输入约定（建议）：
        - profile: 场景认知输出（三维画像）
        - profile.supply / demand / state: 结构化指标
        - diagnosis_thresholds: 可选阈值覆盖（覆盖配置文件中的 diagnosis.thresholds）
        """
        profile = self._extract_profile(task_input)
        diag_cfg = get_business_rules()["diagnosis"]
        thresholds = {**diag_cfg["thresholds"], **task_input.get("diagnosis_thresholds", {})}

        mcp_result = self._invoke_mcp_diagnosis(task_input, profile)
        issues: list[dict[str, Any]] = []

        if mcp_result.get("issues"):
            # 若 MCP 已提供诊断结果，优先吸收并标准化
            issues.extend(self._normalize_mcp_issues(mcp_result["issues"]))
        else:
            # 回退规则引擎：在无 MCP 结果时保证 agent 可工作
            static_metrics = diag_cfg.get("static_metrics", {})
            issues.extend(self._diagnose_static_issues(profile, thresholds, static_metrics))
            issues.extend(self._diagnose_dynamic_issues(profile, thresholds))
            issues.extend(self._diagnose_signal_control_issues(profile, thresholds))

        issues = self._deduplicate_issues(issues)
        priority = self._rank_issues(issues, diag_cfg)

        # 可选：补充 LLM 解释（当前框架无真实模型时兜底为规则解释）
        diagnosis_summary = self._build_summary(priority)

        return {
            "phase": "problem_diagnosis",
            "issues": issues,
            "priority_order": priority,
            "diagnosis_summary": diagnosis_summary,
            "meta": {
                "issue_count": len(issues),
                "thresholds": thresholds,
                "mcp_used": bool(mcp_result.get("issues")),
            },
            "success": True,
        }

    def _extract_profile(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """提取场景认知画像，兼容 profile 在根层或嵌套层."""
        profile = task_input.get("profile", {})
        if not isinstance(profile, dict):
            profile = {}
        profile.setdefault("supply", {})
        profile.setdefault("demand", {})
        profile.setdefault("state", {})
        return profile

    def _invoke_mcp_diagnosis(
        self, task_input: dict[str, Any], profile: dict[str, Any]
    ) -> dict[str, Any]:
        """优先调用 MCP 诊断工具，失败时回退到本地规则."""
        try:
            if hasattr(self.mcp_tools, "invoke"):
                return self.mcp_tools.invoke(
                    "diagnosis_tool",
                    intersection_id=task_input.get("intersection_id", ""),
                    profile=profile,
                ) or {}
            if isinstance(self.mcp_tools, dict) and callable(self.mcp_tools.get("diagnosis_tool")):
                return self.mcp_tools["diagnosis_tool"](
                    intersection_id=task_input.get("intersection_id", ""),
                    profile=profile,
                ) or {}
        except Exception:
            # 诊断模块应尽量可用，不因 MCP 异常中断主流程
            return {}
        return {}

    def _normalize_mcp_issues(self, raw_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """将 MCP 返回的 issues 统一成标准结构."""
        normalized: list[dict[str, Any]] = []
        for item in raw_issues:
            issue_id = str(item.get("id") or item.get("code") or "unknown_issue")
            category = str(item.get("category") or "dynamic")
            severity = float(item.get("severity", 0.5))
            confidence = float(item.get("confidence", 0.7))
            normalized.append(
                {
                    "id": issue_id,
                    "name": str(item.get("name") or issue_id),
                    "category": category,  # static | dynamic | signal_control
                    "scope": item.get("scope", "intersection"),
                    "severity": max(0.0, min(1.0, severity)),
                    "confidence": max(0.0, min(1.0, confidence)),
                    "evidence": item.get("evidence", {}),
                    "reason": item.get("reason", ""),
                    "suggested_action_hint": item.get("suggested_action_hint", ""),
                }
            )
        return normalized

    def _diagnose_static_issues(
        self,
        profile: dict[str, Any],
        thresholds: dict[str, float],
        static_metrics: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """静态短板诊断：路网、渠化、停车、慢行连续性等."""
        supply = profile.get("supply", {})
        issues: list[dict[str, Any]] = []

        rd_max = float(static_metrics.get("road_density_sparse_below", 8.0))
        road_density = self._safe_float(supply.get("road_density_km_km2"))
        if road_density is not None and road_density < rd_max:
            issues.append(
                self._build_issue(
                    issue_id="static_road_network_sparse",
                    name="路网密度不足",
                    category="static",
                    severity=self._severity_by_gap(rd_max, road_density, 5.0),
                    confidence=0.8,
                    evidence={"road_density_km_km2": road_density},
                    reason="区域路网稀疏，主干道过载风险上升，支路分流能力不足",
                    action_hint="优先通过区域分流与边界控流兜底，并输出设施优化建议",
                )
            )

        ch_poor = float(static_metrics.get("channelization_poor_below", 0.6))
        channelization_score = self._safe_float(supply.get("channelization_match_score"))
        if channelization_score is not None and channelization_score < ch_poor:
            issues.append(
                self._build_issue(
                    issue_id="static_channelization_mismatch",
                    name="渠化设计与需求不匹配",
                    category="static",
                    severity=self._severity_by_gap(ch_poor, channelization_score, 0.2),
                    confidence=0.75,
                    evidence={"channelization_match_score": channelization_score},
                    reason="进口道车道功能配置与转向需求偏离，导致排队溢流与效率损失",
                    action_hint="建议路口级重构相位与车道功能，必要时提出土建优化",
                )
            )

        pk_min = float(static_metrics.get("parking_gap_high_above", 0.2))
        parking_gap = self._safe_float(supply.get("parking_gap_ratio"))
        if parking_gap is not None and parking_gap > pk_min:
            issues.append(
                self._build_issue(
                    issue_id="static_parking_supply_gap",
                    name="停车供给缺口",
                    category="static",
                    severity=min(1.0, parking_gap),
                    confidence=0.7,
                    evidence={"parking_gap_ratio": parking_gap},
                    reason="停车位供给不足导致找位绕行与路侧停靠扰动",
                    action_hint="叠加停车诱导与外围换乘策略，缓解无效交通流",
                )
            )
        return issues

    def _diagnose_dynamic_issues(
        self, profile: dict[str, Any], thresholds: dict[str, float]
    ) -> list[dict[str, Any]]:
        """动态问题诊断：供需失衡、速度下降、延误升高、溢流风险等."""
        state = profile.get("state", {})
        demand = profile.get("demand", {})
        issues: list[dict[str, Any]] = []

        saturation = self._safe_float(state.get("saturation"))
        if saturation is not None and saturation >= thresholds["saturation_high"]:
            issues.append(
                self._build_issue(
                    issue_id="dynamic_high_saturation",
                    name="高饱和运行",
                    category="dynamic",
                    severity=min(1.0, saturation),
                    confidence=0.9,
                    evidence={"saturation": saturation},
                    reason="实际需求接近或超过路网承载上限，存在持续拥堵风险",
                    action_hint="优先执行控流、防溢流和关键通道保通策略",
                )
            )

        speed_kmh = self._safe_float(state.get("avg_speed_kmh"))
        if speed_kmh is not None and speed_kmh <= thresholds["speed_low_kmh"]:
            issues.append(
                self._build_issue(
                    issue_id="dynamic_low_speed",
                    name="平均车速偏低",
                    category="dynamic",
                    severity=self._severity_by_gap(
                        thresholds["speed_low_kmh"], speed_kmh, max(5.0, thresholds["speed_low_kmh"] / 2)
                    ),
                    confidence=0.85,
                    evidence={"avg_speed_kmh": speed_kmh},
                    reason="走廊或区域运行效率下降，可能存在协调失效或局部瓶颈",
                    action_hint="优先检查干线协调方向与相位差匹配度",
                )
            )

        delay_s = self._safe_float(state.get("avg_delay_s"))
        if delay_s is not None and delay_s >= thresholds["delay_high_s"]:
            issues.append(
                self._build_issue(
                    issue_id="dynamic_high_delay",
                    name="延误时间过高",
                    category="dynamic",
                    severity=min(1.0, delay_s / max(thresholds["delay_high_s"] * 1.5, 1.0)),
                    confidence=0.85,
                    evidence={"avg_delay_s": delay_s},
                    reason="车辆等待时间显著增加，通行体验与网络稳定性下降",
                    action_hint="提升关键方向绿信比并抑制空放相位",
                )
            )

        demand_supply_ratio = self._safe_float(demand.get("demand_supply_ratio"))
        if demand_supply_ratio is not None and demand_supply_ratio > 1.0:
            issues.append(
                self._build_issue(
                    issue_id="dynamic_demand_supply_imbalance",
                    name="供需失衡",
                    category="dynamic",
                    severity=min(1.0, demand_supply_ratio - 0.1),
                    confidence=0.8,
                    evidence={"demand_supply_ratio": demand_supply_ratio},
                    reason="出行需求超过当前供给能力，拥堵扩散概率升高",
                    action_hint="区域级边界控流 + 干线级分流协同",
                )
            )

        return issues

    def _diagnose_signal_control_issues(
        self, profile: dict[str, Any], thresholds: dict[str, float]
    ) -> list[dict[str, Any]]:
        """信控问题诊断：失衡、溢流、空放、协调失效等."""
        state = profile.get("state", {})
        issues: list[dict[str, Any]] = []

        queue_ratio = self._safe_float(state.get("queue_overflow_ratio"))
        if queue_ratio is not None and queue_ratio >= thresholds["queue_overflow_ratio"]:
            issues.append(
                self._build_issue(
                    issue_id="signal_queue_overflow",
                    name="排队溢流",
                    category="signal_control",
                    severity=min(1.0, queue_ratio),
                    confidence=0.9,
                    evidence={"queue_overflow_ratio": queue_ratio},
                    reason="下游排队回堵或短车道存储不足，存在路口锁死风险",
                    action_hint="执行量出为入、出口优先、上游削峰",
                )
            )

        green_util = self._safe_float(state.get("green_utilization"))
        if green_util is not None and green_util < thresholds["green_util_low"]:
            issues.append(
                self._build_issue(
                    issue_id="signal_green_waste",
                    name="绿灯空放/利用率低",
                    category="signal_control",
                    severity=self._severity_by_gap(thresholds["green_util_low"], green_util, 0.2),
                    confidence=0.8,
                    evidence={"green_utilization": green_util},
                    reason="相位绿灯资源浪费，策略与实时需求匹配不足",
                    action_hint="缩短周期并启用请求式或自适应相位策略",
                )
            )

        phase_imbalance = self._safe_float(state.get("phase_imbalance_ratio"))
        if phase_imbalance is not None and phase_imbalance > thresholds["phase_imbalance_ratio"]:
            issues.append(
                self._build_issue(
                    issue_id="signal_phase_imbalance",
                    name="相位失衡",
                    category="signal_control",
                    severity=min(1.0, phase_imbalance),
                    confidence=0.85,
                    evidence={"phase_imbalance_ratio": phase_imbalance},
                    reason="关键方向绿信比分配与转向流量结构不匹配",
                    action_hint="重算绿信比与相序，保护高需求流向最小服务",
                )
            )
        return issues

    def _deduplicate_issues(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按 issue id 去重，保留严重度更高的一条."""
        dedup: dict[str, dict[str, Any]] = {}
        for issue in issues:
            issue_id = str(issue.get("id", "unknown_issue"))
            old = dedup.get(issue_id)
            if old is None or issue.get("severity", 0.0) > old.get("severity", 0.0):
                dedup[issue_id] = issue
        return list(dedup.values())

    def _rank_issues(
        self, issues: list[dict[str, Any]], diag_cfg: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """根据严重度、置信度和类别权重排序并生成优先级结果."""
        raw_cw = diag_cfg.get("category_weight", {})
        category_weight = {str(k): float(v) for k, v in raw_cw.items()}
        pl_cfg = diag_cfg.get("priority_level", {})
        ranked: list[dict[str, Any]] = []

        for issue in issues:
            severity = float(issue.get("severity", 0.5))
            confidence = float(issue.get("confidence", 0.7))
            weight = category_weight.get(str(issue.get("category", "dynamic")), 1.0)
            priority_score = round(severity * 0.65 + confidence * 0.25 + (weight - 1.0) * 0.10, 4)
            priority_level = self._score_to_level(priority_score, pl_cfg)
            ranked.append(
                {
                    "id": issue.get("id"),
                    "name": issue.get("name"),
                    "category": issue.get("category"),
                    "priority_score": priority_score,
                    "priority_level": priority_level,
                    "reason": issue.get("reason", ""),
                    "evidence": issue.get("evidence", {}),
                    "suggested_action_hint": issue.get("suggested_action_hint", ""),
                }
            )

        ranked.sort(key=lambda x: x["priority_score"], reverse=True)
        for i, item in enumerate(ranked, start=1):
            item["rank"] = i
        return ranked

    def _build_summary(self, priority_order: list[dict[str, Any]]) -> str:
        """构建诊断摘要，便于主智能体与策略智能体快速消费."""
        if not priority_order:
            return "未识别到明显问题，建议维持当前配时并持续监测。"
        top = priority_order[0]
        return (
            f"当前首要症结为「{top.get('name', '')}」"
            f"（类别：{top.get('category', '')}，优先级：{top.get('priority_level', '')}），"
            "建议优先执行对应管控动作，并在下一轮评价环节校验效果。"
        )

    @staticmethod
    def _build_issue(
        issue_id: str,
        name: str,
        category: str,
        severity: float,
        confidence: float,
        evidence: dict[str, Any],
        reason: str,
        action_hint: str,
    ) -> dict[str, Any]:
        return {
            "id": issue_id,
            "name": name,
            "category": category,
            "scope": "intersection",
            "severity": max(0.0, min(1.0, severity)),
            "confidence": max(0.0, min(1.0, confidence)),
            "evidence": evidence,
            "reason": reason,
            "suggested_action_hint": action_hint,
        }

    @staticmethod
    def _score_to_level(score: float, pl_cfg: dict[str, Any]) -> str:
        p0 = float(pl_cfg.get("P0_min", 0.8))
        p1 = float(pl_cfg.get("P1_min", 0.65))
        p2 = float(pl_cfg.get("P2_min", 0.5))
        if score >= p0:
            return "P0"
        if score >= p1:
            return "P1"
        if score >= p2:
            return "P2"
        return "P3"

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _severity_by_gap(threshold: float, current: float, max_gap: float) -> float:
        """将阈值差距映射到 0-1 严重度（差距越大，严重度越高）."""
        gap = max(0.0, threshold - current)
        if max_gap <= 0:
            return 0.5
        return min(1.0, gap / max_gap)
