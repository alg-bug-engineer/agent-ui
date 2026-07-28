# 方案生成算法包（`src/planning`）

## 目录职责

| 模块 | 说明 |
|------|------|
| `single_point.py` | 单点优化：`generate_single_point_plan(request)` |
| `corridor.py` | 干线协调：`generate_corridor_coordination_plan(request)` |
| `coordination/` | 干线协调内核（MVP：双向带宽）；设计审查见 [corridor_coordination_design_review.md](corridor_coordination_design_review.md) |
| `types.py` | 公共辅助（如 `merge_request`、`empty_plan_meta`） |

算法保持 **纯函数风格**：输入 `dict`，输出 `dict`，便于单测与 MCP 薄封装。

## MCP 工具（对外调用名）

在 `src/support/mcp_tools.py` 中：

- `single_point_plan_tool` → 调用 `generate_single_point_plan`
- `corridor_coordination_plan_tool` → 调用 `generate_corridor_coordination_plan`

在 `src/api/main.py` 中：

- `POST /v1/planning/single-point` → 外部系统直接调用单路口配时优化
- `POST /v1/planning/corridor` → 干线协调；`GET /v1/planning/corridor/ui` → 跳转静态页 `/debug/corridor-coordination.html`

注册示例：

```python
from src.support.mcp_tools import MCPToolRegistry, register_plan_generation_mcp_tools

reg = MCPToolRegistry()
register_plan_generation_mcp_tools(reg)
reg.invoke(
    "single_point_plan_tool",
    interId="INT-01",
    phasePlanOfTimeList=[...],
    constraints={...},
)
```

## 与闭环的衔接

`PlanGenerationAgent`（`src/sub_agents/plan_generation.py`）会根据 `scope.type` 路由：

- `corridor` → 调用 `corridor_coordination_plan_tool`（或直连 `generate_corridor_coordination_plan`）
- 其它（如 `intersection`）→ 调用 `single_point_plan_tool`（或直连单点算法）

注入 MCP：

```python
from src.master_agent import MasterAgent
from src.sub_agents import PlanGenerationAgent
from src.support.mcp_tools import MCPToolRegistry, register_plan_generation_mcp_tools
from src.workflow.loop import FivePhaseLoop

reg = MCPToolRegistry()
register_plan_generation_mcp_tools(reg)
# 若诊断等也需 MCP，在此继续 register diagnosis_tool 等

loop = FivePhaseLoop(
    master=MasterAgent(),
    plan_agent=PlanGenerationAgent(mcp_tools=reg),
)
```

## 开发步骤建议

1. 在 `single_point.py` / `corridor.py` 的 `generate_*` 内替换占位逻辑，保持规范化返回结构稳定（或版本化 `meta.version`）。
2. 需要新参数时：在 `request` 中扩展键，并同步更新 MCP 工具的形参或 `**kwargs` 透传。
3. 新增第三类方案时：新建 `src/planning/xxx.py` + 在 `mcp_tools` 增加 `xxx_plan_tool` + `register_plan_generation_mcp_tools` + `PlanGenerationAgent._route_plan_type`。

当前单路口算法说明：

- 优先使用 `SciPy SLSQP` 多初值非线性优化求解；
- 输入统一采用 `interId + phasePlanOfTimeList/parameter_json_str`；
- 输出统一采用 `planType / intersectionId / cycleTime / phaseStageTimingList / meta`；
- 可通过返回结果中的 `plan.meta.solver` / `plan.meta.solver_family` 判断实际走的是哪条求解路径。
