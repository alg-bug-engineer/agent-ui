"""方案生成子智能体：可落地的信号控制执行计划.

对应五环节闭环的「方案生成」环节，将控制策略转化为信号机可执行配时方案.

优先通过 MCP 工具调用 ``single_point_plan_tool`` / ``corridor_coordination_plan_tool``；
未注入 MCP 注册表时，直接调用 ``src.planning`` 下算法（与问题诊断回退模式一致）。
"""

from __future__ import annotations

from typing import Any

from src.planning.corridor import generate_corridor_coordination_plan
from src.planning.single_point import generate_single_point_plan
from src.sub_agents.base import BaseSubAgent
from src.support.mcp_tools import (
    corridor_coordination_plan_tool,
    register_plan_generation_mcp_tools,
    single_point_plan_tool,
)


class PlanGenerationAgent(BaseSubAgent):
    """方案生成子智能体：动态子区划分、协调/路口方案生成、方案编译与下发."""

    name = "plan_generation"

    def run(self, task_input: dict[str, Any]) -> dict[str, Any]:
        """将策略指令转化为配时方案；按 scope 路由单点或干线 MCP."""
        plans: list[dict[str, Any]] = []
        mcp_meta: dict[str, Any] = {"mcp_used": False, "tools": []}

        route = self._route_plan_type(task_input)
        si = task_input.get("strategy_instruction")
        si_dict = si if isinstance(si, dict) else {}
        profile = task_input.get("profile") if isinstance(task_input.get("profile"), dict) else {}
        scope = task_input.get("scope") if isinstance(task_input.get("scope"), dict) else {}
        constraints = task_input.get("plan_constraints")
        constraints = constraints if isinstance(constraints, dict) else {}

        if route == "corridor":
            raw = self._invoke_corridor_mcp(task_input, profile, si_dict, constraints)
            if raw:
                plans.append(raw.get("plan", raw))
                mcp_meta["mcp_used"] = True
                mcp_meta["tools"].append(raw.get("tool", "corridor_coordination_plan_tool"))
            else:
                plans.append(
                    generate_corridor_coordination_plan(
                        {
                            "corridor_id": self._corridor_id(scope, task_input),
                            "intersection_ids": self._scope_ids(scope),
                            "profile": profile,
                            "strategy_instruction": si_dict,
                            "constraints": constraints,
                        }
                    )
                )
        else:
            raw = self._invoke_single_point_mcp(task_input, profile, si_dict, constraints)
            if raw:
                plans.append(raw.get("plan", raw))
                mcp_meta["mcp_used"] = True
                mcp_meta["tools"].append(raw.get("tool", "single_point_plan_tool"))
            else:
                plans.append(
                    generate_single_point_plan(
                        {
                            "interId": self._intersection_id(scope, task_input),
                            "profile": profile,
                            "strategy_instruction": si_dict,
                            "constraints": constraints,
                        }
                    )
                )

        return {
            "phase": "plan_generation",
            "plans": plans,
            "compiled_for_device": {},
            "success": True,
            "meta": mcp_meta,
        }

    def _route_plan_type(self, task_input: dict[str, Any]) -> str:
        """返回 corridor | single_point."""
        scope = task_input.get("scope")
        if isinstance(scope, dict):
            st = str(scope.get("type") or "").lower()
            if st == "corridor":
                return "corridor"
        si = task_input.get("strategy_instruction")
        if isinstance(si, dict):
            si_scope = si.get("scope")
            if isinstance(si_scope, dict) and str(si_scope.get("type") or "").lower() == "corridor":
                return "corridor"
        return "single_point"

    def _scope_ids(self, scope: dict[str, Any]) -> list[str]:
        ids = scope.get("ids")
        if isinstance(ids, list):
            return [str(x) for x in ids if x is not None]
        return []

    def _intersection_id(self, scope: dict[str, Any], task_input: dict[str, Any]) -> str:
        explicit = task_input.get("interId")
        if explicit:
            return str(explicit)
        ids = self._scope_ids(scope)
        return ids[0] if ids else ""

    def _corridor_id(self, scope: dict[str, Any], task_input: dict[str, Any]) -> str:
        cid = task_input.get("corridor_id")
        if cid:
            return str(cid)
        ids = self._scope_ids(scope)
        return ids[0] if ids else "corridor_default"

    def _invoke_single_point_mcp(
        self,
        task_input: dict[str, Any],
        profile: dict[str, Any],
        strategy_instruction: dict[str, Any],
        constraints: dict[str, Any],
    ) -> dict[str, Any] | None:
        """调用 MCP 单点工具，失败返回 None."""
        scope = task_input.get("scope") if isinstance(task_input.get("scope"), dict) else {}
        intersection_id = self._intersection_id(scope, task_input)
        try:
            if hasattr(self.mcp_tools, "invoke"):
                return self.mcp_tools.invoke(
                    "single_point_plan_tool",
                    interId=intersection_id,
                    profile=profile or None,
                    strategy_instruction=strategy_instruction or None,
                    constraints=constraints or None,
                    scenario_type=task_input.get("scenario_type"),
                )
            if isinstance(self.mcp_tools, dict):
                fn = self.mcp_tools.get("single_point_plan_tool")
                if callable(fn):
                    return fn(
                        interId=intersection_id,
                        profile=profile or None,
                        strategy_instruction=strategy_instruction or None,
                        constraints=constraints or None,
                        scenario_type=task_input.get("scenario_type"),
                    )
        except Exception:
            return None
        return None

    def _invoke_corridor_mcp(
        self,
        task_input: dict[str, Any],
        profile: dict[str, Any],
        strategy_instruction: dict[str, Any],
        constraints: dict[str, Any],
    ) -> dict[str, Any] | None:
        scope = task_input.get("scope") if isinstance(task_input.get("scope"), dict) else {}
        corridor_id = self._corridor_id(scope, task_input)
        intersection_ids = self._scope_ids(scope)
        try:
            if hasattr(self.mcp_tools, "invoke"):
                return self.mcp_tools.invoke(
                    "corridor_coordination_plan_tool",
                    corridor_id=corridor_id,
                    intersection_ids=intersection_ids,
                    profile=profile or None,
                    strategy_instruction=strategy_instruction or None,
                    constraints=constraints or None,
                    scenario_type=task_input.get("scenario_type"),
                )
            if isinstance(self.mcp_tools, dict):
                fn = self.mcp_tools.get("corridor_coordination_plan_tool")
                if callable(fn):
                    return fn(
                        corridor_id=corridor_id,
                        intersection_ids=intersection_ids,
                        profile=profile or None,
                        strategy_instruction=strategy_instruction or None,
                        constraints=constraints or None,
                        scenario_type=task_input.get("scenario_type"),
                    )
        except Exception:
            return None
        return None


__all__ = [
    "PlanGenerationAgent",
    "register_plan_generation_mcp_tools",
    "single_point_plan_tool",
    "corridor_coordination_plan_tool",
]
