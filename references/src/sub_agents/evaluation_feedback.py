"""评价反馈子智能体：全维度效果闭环校验.

对应五环节闭环的「评价反馈」环节，验证优化效果，驱动策略迭代.
"""

from __future__ import annotations

from typing import Any

from src.sub_agents.base import BaseSubAgent

# 各指标的默认达标阈值（相对改善百分比，正数表示期望提升，负数表示期望下降）
_DEFAULT_TARGET_IMPROVEMENT = {
    "saturation": -0.08,        # 饱和度降低 ≥ 8%
    "avg_delay_s": -0.15,       # 延误降低 ≥ 15%
    "avg_speed_kmh": 0.10,      # 车速提升 ≥ 10%
    "stop_rate": -0.20,         # 停车率降低 ≥ 20%
    "queue_overflow_ratio": -0.15,
}

# 综合评分达标线
OVERALL_SCORE_THRESHOLD = 0.70

# 经验值沉淀的评分线
EXPERIENCE_WORTHY_THRESHOLD = 0.80


class EvaluationFeedbackAgent(BaseSubAgent):
    """评价反馈子智能体：指标计算、效果分析、问题溯源、报告生成、闭环迭代触发."""

    name = "evaluation_feedback"

    def run(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """计算评价指标，判断是否达标，产出结构化评估结论.

        输入优先从以下路径读取：
        1. task_input["evaluation_data"]: 包含 before/after/target 的评价结构（来自 demo 数据）
        2. task_input["profile"]: 场景认知画像（当前状态）
        3. task_input["strategy_targets"]: 策略预期目标
        """
        eval_data = task_input.get("evaluation_data") or {}
        profile = task_input.get("profile", {})
        strategy_targets = task_input.get("strategy_targets", {})
        selected_templates = task_input.get("selected_templates", [])

        # 构建 before/after/target 指标集
        before, after, target = self._resolve_metrics(
            eval_data, profile, strategy_targets, selected_templates, task_input
        )

        improvements = self._calculate_improvements(before, after, target)
        overall_score = self._compute_overall_score(improvements)
        meets_target = overall_score >= OVERALL_SCORE_THRESHOLD
        side_effects = self._detect_side_effects(before, after)
        conclusion = "达标" if meets_target else "未达标"
        next_action = self._decide_next_action(meets_target, task_input)
        experience_worthy = overall_score >= EXPERIENCE_WORTHY_THRESHOLD and meets_target

        return {
            "phase": "evaluation_feedback",
            "meets_target": meets_target,
            "overall_score": round(overall_score, 3),
            "metrics": {"before": before, "after": after, "target": target},
            "improvements": improvements,
            "side_effects": side_effects,
            "conclusion": conclusion,
            "next_action": next_action,
            "experience_worthy": experience_worthy,
            "suggestions": self._build_suggestions(improvements, meets_target),
            "success": True,
        }

    # ------------------------------------------------------------------
    # 指标解析
    # ------------------------------------------------------------------

    def _resolve_metrics(
        self,
        eval_data: dict,
        profile: dict,
        strategy_targets: dict,
        selected_templates: list[dict],
        task_input: dict,
    ) -> tuple[dict, dict, dict]:
        """构建 before / after / target 指标字典."""

        # 优先从 eval_data 读（demo 数据中已有 before/after）
        before = dict(eval_data.get("before") or {})
        after = dict(eval_data.get("after") or {})
        target = dict(eval_data.get("target") or {})

        # 若 before 为空，从 profile.state 取当前状态作为「优化前」基准
        if not before:
            state = profile.get("state", {})
            before = {
                "saturation": state.get("saturation"),
                "avg_delay_s": state.get("avg_delay_s"),
                "avg_speed_kmh": state.get("avg_speed_kmh"),
                "stop_rate": state.get("stop_rate"),
            }
            before = {k: v for k, v in before.items() if v is not None}

        # 若 after 为空，基于策略预期改善模拟「优化后」（demo 演示用）
        if not after and before:
            after = self._simulate_after(before, selected_templates, task_input)

        # 若 target 为空，基于默认阈值生成目标值
        if not target and before:
            target = self._generate_target(before)

        return before, after, target

    def _simulate_after(
        self, before: dict, selected_templates: list[dict], task_input: dict
    ) -> dict:
        """在无真实 after 数据时，基于策略预期效果模拟优化后指标（demo 用）."""
        after = {}
        top_tpl = selected_templates[0] if selected_templates else {}
        improvement_rates = self._get_template_improvement_rates(top_tpl)

        for metric, val in before.items():
            if val is None:
                continue
            rate = improvement_rates.get(metric, 0.0)
            if metric in ("saturation", "avg_delay_s", "stop_rate", "queue_overflow_ratio"):
                # 这些指标期望下降
                after[metric] = round(float(val) * (1 + rate), 3)
            elif metric == "avg_speed_kmh":
                # 车速期望上升
                after[metric] = round(float(val) * (1 + abs(rate)), 3)
        return after

    def _generate_target(self, before: dict) -> dict:
        """基于 before 和默认改善率生成目标值."""
        target = {}
        for metric, val in before.items():
            if val is None:
                continue
            rate = _DEFAULT_TARGET_IMPROVEMENT.get(metric, 0.0)
            target[metric] = round(float(val) * (1 + rate), 3)
        return target

    # ------------------------------------------------------------------
    # 效果计算
    # ------------------------------------------------------------------

    def _calculate_improvements(
        self, before: dict, after: dict, target: dict
    ) -> list[dict[str, Any]]:
        improvements = []
        all_metrics = set(before) | set(after) | set(target)
        metric_labels = {
            "saturation": "饱和度",
            "avg_delay_s": "平均延误(s)",
            "avg_speed_kmh": "平均车速(km/h)",
            "stop_rate": "停车率",
            "queue_overflow_ratio": "排队溢流比",
        }
        for metric in sorted(all_metrics):
            b = before.get(metric)
            a = after.get(metric)
            t = target.get(metric)
            if b is None or a is None:
                continue
            delta = a - b
            delta_pct = round((delta / b) * 100, 1) if b != 0 else 0.0

            # 判断达标：对于"下降"指标，改善即 a < t（或 a <= b * (1 + rate)）
            lower_is_better = metric in ("saturation", "avg_delay_s", "stop_rate", "queue_overflow_ratio")
            if t is not None:
                meets = (a <= t) if lower_is_better else (a >= t)
            else:
                rate = _DEFAULT_TARGET_IMPROVEMENT.get(metric, 0.0)
                meets = (delta_pct <= rate * 100) if lower_is_better else (delta_pct >= rate * 100)

            improvements.append({
                "metric": metric_labels.get(metric, metric),
                "metric_key": metric,
                "unit": "%" if "rate" in metric or "ratio" in metric else "",
                "before": b,
                "after": a,
                "target": t,
                "delta": round(delta, 3),
                "delta_pct": delta_pct,
                "meets_target": meets,
                "lower_is_better": lower_is_better,
            })
        return improvements

    def _compute_overall_score(self, improvements: list[dict]) -> float:
        if not improvements:
            return 0.5
        met = sum(1 for i in improvements if i["meets_target"])
        base = met / len(improvements)

        # 加权：关键指标权重更高
        weighted_sum, weight_total = 0.0, 0.0
        weights = {"saturation": 2.0, "avg_delay_s": 1.5, "avg_speed_kmh": 1.5, "stop_rate": 1.0}
        for imp in improvements:
            w = weights.get(imp["metric_key"], 1.0)
            weighted_sum += w * (1.0 if imp["meets_target"] else 0.0)
            weight_total += w
        weighted = weighted_sum / weight_total if weight_total else base
        return round(base * 0.4 + weighted * 0.6, 3)

    def _detect_side_effects(self, before: dict, after: dict) -> list[dict[str, Any]]:
        """检测副作用（某些指标在改善其他指标时恶化）."""
        side_effects = []
        if before.get("avg_delay_s") and after.get("avg_delay_s"):
            # 延误恶化超过 10% 视为副作用
            b, a = before["avg_delay_s"], after["avg_delay_s"]
            if a > b * 1.10:
                side_effects.append({
                    "description": f"周边延误有所上升：{b}s → {a}s（+{((a-b)/b*100):.1f}%）",
                    "severity": "medium" if a > b * 1.20 else "low",
                    "acceptable": a <= b * 1.20,
                })
        return side_effects

    def _decide_next_action(self, meets_target: bool, task_input: dict) -> str:
        """决策下一步动作."""
        rerun_count = task_input.get("rerun_count", 0)
        if meets_target:
            return "continue"
        if rerun_count < 2:
            return "rerun"
        return "escalate_human"

    def _build_suggestions(self, improvements: list[dict], meets_target: bool) -> list[str]:
        suggestions = []
        not_met = [i for i in improvements if not i["meets_target"]]
        if meets_target:
            suggestions.append("本轮优化目标达成，建议维持当前策略方案并持续监测。")
        else:
            for i in not_met[:2]:
                delta = i.get("delta_pct", 0)
                suggestions.append(
                    f"{i['metric']} 未达标（实际变化 {delta:+.1f}%），建议调整相关参数后复跑。"
                )
        return suggestions

    @staticmethod
    def _get_template_improvement_rates(template: dict) -> dict[str, float]:
        """根据策略模板返回各指标预期改善率（demo 默认值）."""
        template_id = template.get("template_id", "")
        defaults = {
            "saturation": -0.10,
            "avg_delay_s": -0.20,
            "avg_speed_kmh": 0.15,
            "stop_rate": -0.25,
        }
        if "green_wave" in template_id:
            defaults["avg_speed_kmh"] = 0.50
            defaults["stop_rate"] = -0.45
        elif "expansion_control" in template_id:
            defaults["saturation"] = -0.12
            defaults["avg_delay_s"] = -0.18
        elif "phase_rebalance" in template_id:
            defaults["avg_delay_s"] = -0.25
            defaults["stop_rate"] = -0.30
        return defaults
