"""MCP 专业工具集：交通工程专业能力 - 对应架构 3.2 节.

按功能领域分为五类，与五大专业环节子智能体一一对应：
供给计算、需求统计、状态评估、诊断/策略/配时/评价等专业工具。
"""

from __future__ import annotations

from typing import Any, Callable

from src.sub_agents.problem_issue_codes import ISSUE_CODEBOOK


class MCPToolRegistry:
    """MCP 专业工具注册表，供分控层子智能体按需调用."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        """注册工具函数."""
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., Any] | None:
        """按名称获取工具."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """列出已注册工具名."""
        return list(self._tools.keys())

    def invoke(self, name: str, **kwargs: Any) -> Any:
        """调用指定工具."""
        fn = self._tools.get(name)
        if fn is None:
            raise KeyError(f"MCP tool not found: {name}")
        return fn(**kwargs)


# ---------- 占位：与五环节对应的 MCP 工具类（可逐步实现具体算法） ----------


def supply_calc_tool(region_id: str = "", **kwargs: Any) -> dict:
    """交通供给计算：路网密度、饱和流量、区域最大承载力、信控路口通行能力."""
    return {"capacity": {}, "density_km_km2": 0.0}


def demand_stats_tool(region_id: str = "", **kwargs: Any) -> dict:
    """交通需求统计：机动车出行量、区域进出流量、转向流量结构等."""
    return {"volume": {}, "turn_ratio": {}}


def state_assess_tool(region_id: str = "", **kwargs: Any) -> dict:
    """交通状态评估：饱和度、平均车速、延误、拥堵阶段分级."""
    return {"saturation": {}, "speed_kmh": {}, "delay_s": {}}


def diagnosis_tool(intersection_id: str = "", **kwargs: Any) -> dict:
    """问题诊断工具（mock 版）.

    输入：
    - profile: {supply, demand, state}
    输出：
    - issues: 标准问题码结构（与 ProblemDiagnosisAgent 对齐）

    阈值来自业务规则 YAML：diagnosis.thresholds、diagnosis.static_metrics、
    diagnosis_tool_mock（后者可覆盖前者便于现场调参）。
    """
    from src.config.business_rules_loader import get_business_rules

    rules = get_business_rules()
    diag = rules["diagnosis"]
    mock = rules.get("diagnosis_tool_mock") or {}
    thresholds = diag.get("thresholds") or {}
    static_metrics = diag.get("static_metrics") or {}

    profile = kwargs.get("profile", {}) or {}
    supply = profile.get("supply", {}) if isinstance(profile, dict) else {}
    demand = profile.get("demand", {}) if isinstance(profile, dict) else {}
    state = profile.get("state", {}) if isinstance(profile, dict) else {}

    issues: list[dict[str, Any]] = []

    def add_issue(code: str, severity: float, confidence: float, evidence: dict, reason: str) -> None:
        meta = ISSUE_CODEBOOK.get(code, {})
        issues.append(
            {
                "id": code,
                "name": meta.get("name", code),
                "category": meta.get("category", "dynamic"),
                "scope": meta.get("default_scope", "intersection"),
                "severity": max(0.0, min(1.0, severity)),
                "confidence": max(0.0, min(1.0, confidence)),
                "evidence": evidence,
                "reason": reason,
                "tags": meta.get("tags", []),
            }
        )

    rd_sparse_below = float(
        mock.get("road_density_sparse_below", static_metrics.get("road_density_sparse_below", 8.0))
    )
    sat_high = float(mock.get("saturation_high", thresholds.get("saturation_high", 0.85)))
    delay_high = float(mock.get("delay_high_s", thresholds.get("delay_high_s", 90.0)))
    q_overflow = float(mock.get("queue_overflow_ratio", thresholds.get("queue_overflow_ratio", 1.0)))
    green_low = float(mock.get("green_util_low", thresholds.get("green_util_low", 0.5)))

    # 轻量规则（用于联调阶段 mock）
    road_density = _to_float(supply.get("road_density_km_km2"))
    if road_density is not None and road_density < rd_sparse_below:
        add_issue(
            "static_road_network_sparse",
            severity=min(1.0, (rd_sparse_below - road_density) / 4.0),
            confidence=0.82,
            evidence={"road_density_km_km2": road_density},
            reason="路网密度低于经验阈值，支路分流能力不足。",
        )

    saturation = _to_float(state.get("saturation"))
    if saturation is not None and saturation >= sat_high:
        add_issue(
            "dynamic_high_saturation",
            severity=min(1.0, saturation),
            confidence=0.92,
            evidence={"saturation": saturation},
            reason="运行处于高饱和状态，拥堵风险显著升高。",
        )

    delay_s = _to_float(state.get("avg_delay_s"))
    if delay_s is not None and delay_s >= delay_high:
        add_issue(
            "dynamic_high_delay",
            severity=min(1.0, delay_s / max(delay_high * 1.67, 1.0)),
            confidence=0.87,
            evidence={"avg_delay_s": delay_s},
            reason="平均延误超过阈值，通行体验与稳定性下降。",
        )

    queue_ratio = _to_float(state.get("queue_overflow_ratio"))
    if queue_ratio is not None and queue_ratio >= q_overflow:
        add_issue(
            "signal_queue_overflow",
            severity=min(1.0, queue_ratio),
            confidence=0.9,
            evidence={"queue_overflow_ratio": queue_ratio},
            reason="存在排队回堵，可能引发路口锁死。",
        )

    green_util = _to_float(state.get("green_utilization"))
    if green_util is not None and green_util < green_low:
        add_issue(
            "signal_green_waste",
            severity=min(1.0, (green_low - green_util) / max(0.3, green_low * 0.6)),
            confidence=0.8,
            evidence={"green_utilization": green_util},
            reason="绿灯利用率偏低，存在空放和配时浪费。",
        )

    ds_ratio = _to_float(demand.get("demand_supply_ratio"))
    if ds_ratio is not None and ds_ratio > 1.0:
        add_issue(
            "dynamic_demand_supply_imbalance",
            severity=min(1.0, ds_ratio - 0.1),
            confidence=0.84,
            evidence={"demand_supply_ratio": ds_ratio},
            reason="需求高于供给，拥堵可能由局部向区域扩散。",
        )

    return {"issues": issues, "priority": []}


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def strategy_gen_tool(scope: dict = None, **kwargs: Any) -> dict:
    """分级管控策略生成：区域/干线/路口策略、可行性校验."""
    return {"strategy": {}, "feasible": True}


def timing_calc_tool(plan_spec: dict = None, **kwargs: Any) -> dict:
    """配时参数计算：周期、绿信比、相位差、绿波速度等."""
    return {"cycle_s": 0, "green_ratio": {}, "offset_s": {}}


def single_point_plan_tool(
    interId: str = "",
    profile: dict | None = None,
    strategy_instruction: dict | None = None,
    constraints: dict | None = None,
    **kwargs: Any,
) -> dict:
    """MCP：单点优化方案生成.

    将路口画像与策略指令交给单点优化算法，输出可下发的配时方案骨架。
    额外参数经 ``**kwargs`` 并入请求 dict（如 scenario_type）。
    """
    from src.planning.single_point import generate_single_point_plan

    req: dict[str, Any] = {
        "interId": interId,
        "profile": profile,
        "strategy_instruction": strategy_instruction,
        "constraints": constraints,
        **kwargs,
    }
    plan = generate_single_point_plan(req)
    return {
        "ok": True,
        "isError": bool(plan.get("isError", False)),
        "data": plan.get("data", []),
        "error": plan.get("error"),
        "tool": "single_point_plan_tool",
        "plan": plan,
    }


def corridor_coordination_plan_tool(
    corridor_id: str = "",
    intersection_ids: list | None = None,
    profile: dict | None = None,
    strategy_instruction: dict | None = None,
    constraints: dict | None = None,
    **kwargs: Any,
) -> dict:
    """MCP：干线协调方案生成.

    输入走廊及有序路口列表，输出绿波/协调方案骨架（相位差、带宽等占位）。
    """
    from src.planning.corridor import generate_corridor_coordination_plan

    ids = intersection_ids if isinstance(intersection_ids, list) else []
    req: dict[str, Any] = {
        "corridor_id": corridor_id,
        "intersection_ids": ids,
        "profile": profile,
        "strategy_instruction": strategy_instruction,
        "constraints": constraints,
        **kwargs,
    }
    plan = generate_corridor_coordination_plan(req)
    return {
        "ok": True,
        "tool": "corridor_coordination_plan_tool",
        "plan": plan,
    }


def register_plan_generation_mcp_tools(registry: MCPToolRegistry) -> None:
    """注册方案生成类 MCP 工具（单点 / 干线）."""
    registry.register("single_point_plan_tool", single_point_plan_tool)
    registry.register("corridor_coordination_plan_tool", corridor_coordination_plan_tool)


def evaluation_metrics_tool(before: dict = None, after: dict = None, **kwargs: Any) -> dict:
    """评价指标计算：车速提升率、延误降低率、冲突点减少率、绿灯利用率等."""
    return {"metrics": {}, "meets_target": False}
