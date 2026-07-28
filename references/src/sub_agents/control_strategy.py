"""控制策略子智能体：目标导向的分级管控方案制定.

对应五环节闭环的「控制策略」环节，按区域-干线-路口三级制定管控策略.
问题码→策略模板映射与模板元数据由 config/business_rules/*.yaml 配置。
"""

from src.common.models import StrategyInstruction
from src.config.business_rules_loader import get_business_rules
from src.sub_agents.base import BaseSubAgent


def _bootstrap_control_strategy_config() -> None:
    """从业务规则 YAML 注入类属性，供 demo API 与选择器共用."""
    r = get_business_rules()["control_strategy"]
    ControlStrategyAgent.ISSUE_TEMPLATE_MAP = {
        k: list(v) for k, v in r["issue_template_map"].items()
    }
    ControlStrategyAgent.TEMPLATE_META = {
        tid: {
            "control_level": m["control_level"],
            "allowed_levels": list(m["allowed_levels"]),
            "description": str(m.get("description", tid)),
        }
        for tid, m in r["template_meta"].items()
    }
    ControlStrategyAgent.MAX_SELECTED_TEMPLATES = int(r.get("max_templates", 5))


class ControlStrategyAgent(BaseSubAgent):
    """控制策略子智能体：区域/干线/路口级策略、特殊场景策略、策略可行性校验."""

    name = "control_strategy"

    ISSUE_TEMPLATE_MAP: dict[str, list[str]] = {}
    TEMPLATE_META: dict[str, dict] = {}
    MAX_SELECTED_TEMPLATES: int = 5

    def run(self, task_input: dict) -> dict:
        """生成可机读的策略指令，供方案生成环节使用."""
        # 输入包含问题诊断的症结与优先级
        # 调用 MCP：分级管控策略生成、目标匹配、可行性校验、潮汐/绿波策略设计
        # 调用 LLM：多场景策略生成、多目标优化、自然语言描述
        instruction = self._generate_strategy_instruction(task_input)
        selected_templates = self._select_templates_from_priority(task_input)
        return {
            "phase": "control_strategy",
            "strategy_instruction": instruction.model_dump(),
            "selected_templates": selected_templates,
            "success": True,
        }

    def _generate_strategy_instruction(self, task_input: dict) -> StrategyInstruction:
        """生成策略指令."""
        selected_templates = self._select_templates_from_priority(task_input)
        top_issue = self._get_top_issue(task_input)
        scenario_type = task_input.get("scenario_type", "normal")
        priority_names = [t["template_id"] for t in selected_templates]

        return StrategyInstruction(
            scope=task_input.get("scope", {}),
            target_priority=task_input.get("target_priority", []) or priority_names,
            background_plan=f"{scenario_type}_base_plan_v1",
            realtime_patch={
                "selected_templates": selected_templates,
                "top_issue": top_issue,
            },
            trigger_condition=f"top_issue={top_issue.get('id', 'none')}",
            exit_condition="evaluation_meets_target=true",
            hysteresis_minutes=15,
            hard_constraints=[
                "respect_national_signal_control_spec",
                "keep_min_pedestrian_green_time",
                "avoid_gridlock_with_downstream_blocking",
            ],
            fallback_plan="safe_fixed_time_plan",
        )

    def _get_top_issue(self, task_input: dict) -> dict:
        priority_order = task_input.get("priority_order", [])
        if isinstance(priority_order, list) and priority_order:
            return priority_order[0]
        return {}

    def _select_templates_from_priority(self, task_input: dict) -> list[dict]:
        """根据问题优先级选择策略模板（策略模板选择器）.

        输入：
        - priority_order: 问题诊断子智能体输出

        输出：
        - 模板列表（按推荐分值降序）
        """
        priority_order = task_input.get("priority_order", [])
        if not isinstance(priority_order, list):
            return []

        max_n = ControlStrategyAgent.MAX_SELECTED_TEMPLATES
        selected: dict[str, dict] = {}
        for issue in priority_order:
            issue_id = issue.get("id", "")
            issue_score = float(issue.get("priority_score", 0.0))
            issue_level = issue.get("priority_level", "P3")
            if not issue_id:
                continue
            templates = ControlStrategyAgent.ISSUE_TEMPLATE_MAP.get(issue_id, [])
            for rank, template_id in enumerate(templates):
                template_meta = ControlStrategyAgent.TEMPLATE_META.get(template_id, {})
                # 同一 issue 下首选模板权重更高
                rank_weight = 1.0 if rank == 0 else 0.85
                recommend_score = round(issue_score * rank_weight, 4)
                existing = selected.get(template_id)
                item = {
                    "template_id": template_id,
                    "recommended_by_issue": issue_id,
                    "issue_level": issue_level,
                    "recommend_score": recommend_score,
                    "control_level": template_meta.get("control_level", "intersection"),
                    "description": template_meta.get("description", template_id),
                }
                if existing is None or recommend_score > existing["recommend_score"]:
                    selected[template_id] = item

        sorted_templates = sorted(
            selected.values(), key=lambda x: x["recommend_score"], reverse=True
        )
        return sorted_templates[:max_n]


_bootstrap_control_strategy_config()
