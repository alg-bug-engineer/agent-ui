"""信控场景 Skill 技能示例 - 对应架构 2.1.2 节."""

from src.common.models import TriggerMode
from src.sub_agents.control_strategy import ControlStrategyAgent
from src.sub_agents.problem_diagnosis import ProblemDiagnosisAgent
from src.skills.base import Skill, SkillManifest
from src.support.mcp_tools import MCPToolRegistry, diagnosis_tool


class IntersectionDiagnosisSkill(Skill):
    """路口单点诊断技能（已废弃，请使用 SingleIntersectionOptimizationSkill）.

    .. deprecated:: 1.1.0
        该 Skill 仅为占位实现。完整的单路口优化功能已迁移至
        ``src.skills.single_intersection_optimization.SingleIntersectionOptimizationSkill``，
        支持诊断驱动参数自适应、配时求解、质量评估等端到端能力。
    """

    manifest = SkillManifest(
        id="intersection_diagnosis",
        version="1.0.0",
        description="[DEPRECATED] 请使用 single_intersection_optimization",
        trigger_mode=TriggerMode.SCENARIO_MATCH,
        trigger_threshold={"saturation_gt": 0.85, "duration_minutes": 15},
        required_tools=["scene_cognition", "problem_diagnosis", "knowledge_rag"],
        input_schema={"intersection_id": "string", "metrics": "object"},
        output_schema={"report": "string", "suggestions": "array"},
    )

    def execute(self, context: dict) -> dict:
        """调用场景认知→问题诊断→策略推荐链，检索知识库历史管控经验."""
        return {"report": "", "suggestions": []}


class CorridorGreenWaveSkill(Skill):
    """干线绿波优化技能：干线通行效率下降>10% 或调度指令触发，全流程至方案下发."""

    manifest = SkillManifest(
        id="corridor_green_wave",
        version="1.0.0",
        description="干线通行效率下降时执行绿波优化，含配时计算、仿真验证、方案下发",
        trigger_mode=TriggerMode.SCENARIO_MATCH,
        trigger_threshold={"efficiency_drop_pct": 10},
        required_tools=[
            "control_strategy",
            "plan_generation",
            "timing_calc",
            "simulation",
            "knowledge_rag",
        ],
        input_schema={"corridor_id": "string", "current_metrics": "object"},
        output_schema={"plan_id": "string", "params": "object"},
    )

    def execute(self, context: dict) -> dict:
        """控制策略→配时参数计算→方案编译→仿真验证→方案下发."""
        return {"plan_id": "", "params": {}}


class EmergencyResponseSkill(Skill):
    """应急快速响应技能：事故/恶劣天气事件触发，2 分钟内完成截流分流方案生成与下发."""

    manifest = SkillManifest(
        id="emergency_response",
        version="1.0.0",
        description="接收交通事故或恶劣天气事件，快速生成截流分流方案并联动外部应急工具",
        trigger_mode=TriggerMode.KEYWORD,
        trigger_keywords=["事故", "恶劣天气", "应急", "突发事件"],
        required_tools=["emergency_control", "plan_generation", "external_emergency"],
        input_schema={"event_type": "string", "location": "object", "severity": "string"},
        output_schema={"plan": "object", "disseminated": "boolean"},
    )

    def execute(self, context: dict) -> dict:
        """生成截流分流方案、检索历史同类应急处置经验、联动外部应急工具."""
        return {"plan": {}, "disseminated": False}


class RegionLoadBalanceSkill(Skill):
    """区域负荷均衡技能：每 15 分钟周期触发，评估区域交通负荷并生成均衡调控方案."""

    manifest = SkillManifest(
        id="region_load_balance",
        version="1.0.0",
        description="周期性评估区域交通负荷分布，生成区域间流量均衡调控方案",
        trigger_mode=TriggerMode.PERIODIC,
        period_minutes=15,
        required_tools=["scene_cognition", "control_strategy", "region_control"],
        input_schema={"region_ids": "array"},
        output_schema={"adjustments": "array"},
    )

    def execute(self, context: dict) -> dict:
        """评估区域负荷、生成均衡方案."""
        return {"adjustments": []}


class StrategyEffectReviewSkill(Skill):
    """策略效果复盘技能：每日定时触发，汇总当日管控动作与效果，生成日度复盘报告并沉淀长期记忆."""

    manifest = SkillManifest(
        id="strategy_effect_review",
        version="1.0.0",
        description="每日定时汇总管控动作与效果指标，生成日度复盘报告并写入长期记忆与知识库",
        trigger_mode=TriggerMode.PERIODIC,
        period_minutes=24 * 60,  # 每日
        required_tools=["evaluation_feedback", "memory", "knowledge_rag"],
        input_schema={"date": "string"},
        output_schema={"report": "string", "cases_updated": "int"},
    )

    def execute(self, context: dict) -> dict:
        """汇总当日动作与指标、生成报告、沉淀至长期记忆、更新知识库案例."""
        return {"report": "", "cases_updated": 0}


class DiagnosisToStrategyTemplateSkill(Skill):
    """诊断到策略模板技能：将问题优先级直接映射为策略模板选择结果."""

    manifest = SkillManifest(
        id="diagnosis_to_strategy_template",
        version="1.0.0",
        description="接收问题诊断 priority_order，输出控制策略模板选择结果与机读策略指令",
        trigger_mode=TriggerMode.DISPATCH,
        required_tools=["problem_diagnosis", "control_strategy", "diagnosis_tool"],
        input_schema={
            "scenario_type": "string",
            "scope": "object",
            "profile": "object",
            "priority_order": "array(optional)",
        },
        output_schema={
            "selected_templates": "array",
            "strategy_instruction": "object",
            "top_issue": "object",
        },
    )

    def execute(self, context: dict) -> dict:
        """执行诊断到策略模板链路.

        若 context 已给出 priority_order，则直接进入模板选择；
        否则自动调用问题诊断子智能体生成 priority_order。
        """
        priority_order = context.get("priority_order")
        diagnosis_result = {}

        if not priority_order:
            registry = MCPToolRegistry()
            registry.register("diagnosis_tool", diagnosis_tool)
            diagnosis_agent = ProblemDiagnosisAgent(mcp_tools=registry)
            diagnosis_result = diagnosis_agent.run(context)
            priority_order = diagnosis_result.get("priority_order", [])

        strategy_agent = ControlStrategyAgent()
        strategy_result = strategy_agent.run(
            {
                "scenario_type": context.get("scenario_type", "normal"),
                "scope": context.get("scope", {}),
                "priority_order": priority_order or [],
                "target_priority": context.get("target_priority", []),
            }
        )

        return {
            "diagnosis_summary": diagnosis_result.get("diagnosis_summary", ""),
            "priority_order": priority_order or [],
            "selected_templates": strategy_result.get("selected_templates", []),
            "strategy_instruction": strategy_result.get("strategy_instruction", {}),
            "top_issue": (priority_order or [{}])[0],
        }


class MultiScenarioDiagnosisBenchmarkSkill(Skill):
    """多场景诊断基准技能：学校/医院/活动散场三类场景对比输出."""

    manifest = SkillManifest(
        id="multi_scenario_diagnosis_benchmark",
        version="1.0.0",
        description="执行学校、医院、活动散场多场景诊断并输出模板选择对比结果",
        trigger_mode=TriggerMode.DISPATCH,
        required_tools=["problem_diagnosis", "control_strategy", "diagnosis_tool"],
        input_schema={"scenarios": "array(optional)"},
        output_schema={"rows": "array", "summary": "string"},
    )

    def execute(self, context: dict) -> dict:
        """执行多场景 mock 对比并返回结构化摘要."""
        scenarios = context.get("scenarios") or [
            {
                "scenario_name": "学校上下学高峰",
                "scenario_type": "school_peak",
                "scope": {"type": "intersection", "ids": ["SCH-INT-01"]},
                "intersection_id": "SCH-INT-01",
                "profile": {
                    "supply": {"road_density_km_km2": 7.2, "channelization_match_score": 0.45},
                    "demand": {"demand_supply_ratio": 1.18},
                    "state": {"saturation": 0.88, "avg_delay_s": 115, "queue_overflow_ratio": 1.10},
                },
            },
            {
                "scenario_name": "医院早高峰就诊",
                "scenario_type": "hospital_morning",
                "scope": {"type": "region", "ids": ["HOS-REG-01"]},
                "intersection_id": "HOS-INT-03",
                "profile": {
                    "supply": {"road_density_km_km2": 6.8, "parking_gap_ratio": 0.36},
                    "demand": {"demand_supply_ratio": 1.27},
                    "state": {"saturation": 0.93, "avg_delay_s": 135, "queue_overflow_ratio": 1.22},
                },
            },
            {
                "scenario_name": "大型活动散场",
                "scenario_type": "event_dispersal",
                "scope": {"type": "corridor", "ids": ["EVT-COR-01"]},
                "intersection_id": "EVT-INT-09",
                "profile": {
                    "supply": {"road_density_km_km2": 7.8, "parking_gap_ratio": 0.24},
                    "demand": {"demand_supply_ratio": 1.34},
                    "state": {"saturation": 0.95, "avg_delay_s": 150, "queue_overflow_ratio": 1.30},
                },
            },
        ]

        registry = MCPToolRegistry()
        registry.register("diagnosis_tool", diagnosis_tool)
        diagnosis_agent = ProblemDiagnosisAgent(mcp_tools=registry)
        strategy_agent = ControlStrategyAgent()

        rows = []
        for scene in scenarios:
            diag = diagnosis_agent.run(scene)
            strat = strategy_agent.run(
                {
                    "scenario_type": scene.get("scenario_type", "normal"),
                    "scope": scene.get("scope", {}),
                    "priority_order": diag.get("priority_order", []),
                }
            )
            top_issue = (diag.get("priority_order") or [{}])[0]
            top_tpl = (strat.get("selected_templates") or [{}])[0]
            rows.append(
                {
                    "scenario_name": scene.get("scenario_name", ""),
                    "issue_count": diag.get("meta", {}).get("issue_count", 0),
                    "top_issue_id": top_issue.get("id", ""),
                    "top_issue_level": top_issue.get("priority_level", ""),
                    "top_template_id": top_tpl.get("template_id", ""),
                }
            )

        summary = "；".join(
            [
                f"{r['scenario_name']}: {r['top_issue_id']} -> {r['top_template_id']}"
                for r in rows
            ]
        )
        return {"rows": rows, "summary": summary}
