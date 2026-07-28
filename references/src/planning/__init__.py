"""方案生成算法包：单点优化、干线协调等.

算法实现放在本包内纯 Python 模块；对外通过 ``src.support.mcp_tools`` 注册为 MCP 工具，
供 ``PlanGenerationAgent`` 或其它子智能体调用。

开发约定：
- 入参/出参使用 ``dict``，字段见各模块顶部的「契约」说明；
- 算法函数名：``generate_*``，无副作用（除日志外），便于单测；
- MCP 工具只做参数归一化 + 调用 ``generate_*`` + 统一信封 ``ok/tool/error``。
"""

from src.planning.corridor import generate_corridor_coordination_plan
from src.planning.single_point import generate_single_point_plan

__all__ = [
    "generate_single_point_plan",
    "generate_corridor_coordination_plan",
]
