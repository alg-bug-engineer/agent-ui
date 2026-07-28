"""信控智能体 API 入口 - 对应架构 7.1 节标准化接口."""

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from src.master_agent import MasterAgent
from src.common.models import TaskType
from src.workflow.loop import run_loop_once
from src.api.debug_history import (
    clear_debug_history,
    get_debug_history,
    history_capacity,
    push_debug_history,
)
from src.demo.demo_routes import router as demo_router
from src.demo.demo_scheduler import get_scheduler
from src.api.signalctl_map_routes import router as signalctl_map_router

# 调试控制台静态资源目录（项目根目录下 static/）
STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static"

app = FastAPI(
    title="城市级信控智能体 API",
    description="感知—认知—决策—执行—评价—进化 六位一体信控智能体",
    version="0.1.0",
)

# 注册演示路由
app.include_router(demo_router)
app.include_router(signalctl_map_router)


@app.on_event("startup")
async def _startup_scheduler() -> None:
    """服务启动时自动启动 Demo 调度器，驱动全自动闭环运行."""
    get_scheduler().start()

SINGLE_POINT_OPENAPI_EXAMPLE: dict[str, Any] = {
    "interId": "INT-001",
    "obj_intensity": 0.8,
    "phasePlanOfTimeList": [
        {
            "interId": "INT-001",
            "phasePlanId": "PLAN-001",
            "phasePlanName": "默认相位方案",
            "startTime": "00:00",
            "endTime": "24:00",
            "controlPlanId": None,
            "cycleTime": None,
            "phaseStageInfoList": [
                {
                    "phaseStageId": "A",
                    "phaseStageName": "A",
                    "phaseDirInfoDTOList": [
                        {
                            "dir8No": 1,
                            "turnDirNo": 2,
                            "turnFlowTotal": 600,
                            "laneCount": 2,
                        },
                        {
                            "dir8No": 5,
                            "turnDirNo": 2,
                            "criticalLaneFlow": 280,
                            "laneCount": 1,
                        },
                    ],
                },
                {
                    "phaseStageId": "B",
                    "phaseStageName": "B",
                    "phaseDirInfoDTOList": [
                        {
                            "dir8No": 3,
                            "turnDirNo": 2,
                            "turnFlowTotal": 420,
                            "laneCount": 2,
                        },
                        {
                            "dir8No": 7,
                            "turnDirNo": 2,
                            "criticalLaneFlow": 210,
                            "laneCount": 1,
                        },
                    ],
                },
            ],
        }
    ],
    "constraints": {
        "max_cycle_s": 190,
        "min_green_s": 20,
        "green_loss_s": 5,
        "yellow_s": 3,
        "all_red_s": 2,
        "saturation_flow_vph": 1400,
    },
}

SINGLE_POINT_OPENAPI_RESPONSE_EXAMPLE: dict[str, Any] = {
    "ok": True,
    "isError": False,
    "data": [
        {
            "phaseStageId": "A",
            "phaseStageName": "A",
            "splitTime": 70,
            "greenTime": 35,
            "yellowTime": 3,
            "redTime": 32,
            "allRedTime": 2,
            "splitRatio": 0.5,
            "phaseSaturation": 0.8231,
            "phaseDirInfoDTOList": [
                {
                    "movementKey": "d1_t2",
                    "dir8No": 1,
                    "turnDirNo": 2,
                    "turnFlowTotal": 600,
                    "laneCount": 2,
                    "criticalLaneFlow": 300,
                    "laneLevelFlow": 300,
                    "label": "北-直行",
                },
                {
                    "movementKey": "d5_t2",
                    "dir8No": 5,
                    "turnDirNo": 2,
                    "turnFlowTotal": 0,
                    "laneCount": 1,
                    "criticalLaneFlow": 280,
                    "laneLevelFlow": 280,
                    "label": "南-直行",
                },
            ],
        },
        {
            "phaseStageId": "B",
            "phaseStageName": "B",
            "splitTime": 70,
            "greenTime": 25,
            "yellowTime": 3,
            "redTime": 42,
            "allRedTime": 2,
            "splitRatio": 0.3571,
            "phaseSaturation": 0.7812,
            "phaseDirInfoDTOList": [
                {
                    "movementKey": "d3_t2",
                    "dir8No": 3,
                    "turnDirNo": 2,
                    "turnFlowTotal": 420,
                    "laneCount": 2,
                    "criticalLaneFlow": 210,
                    "laneLevelFlow": 210,
                    "label": "东-直行",
                }
            ],
        },
    ],
    "error": None,
    "tool": "single_point_plan_tool",
    "plan": {
        "isError": False,
        "data": [
            {
                "phaseStageId": "A",
                "phaseStageName": "A",
                "splitTime": 70,
                "greenTime": 35,
                "yellowTime": 3,
                "redTime": 32,
                "allRedTime": 2,
                "splitRatio": 0.5,
                "phaseSaturation": 0.8231,
                "phaseDirInfoDTOList": [
                    {
                        "movementKey": "d1_t2",
                        "dir8No": 1,
                        "turnDirNo": 2,
                        "turnFlowTotal": 600,
                        "laneCount": 2,
                        "criticalLaneFlow": 300,
                        "laneLevelFlow": 300,
                        "label": "北-直行",
                    }
                ],
            }
        ],
        "error": None,
        "planType": "single_point",
        "intersectionId": "INT-001",
        "cycleTime": 70,
        "phasePlanId": "PLAN-001",
        "phasePlanName": "默认相位方案",
        "phaseStageTimingList": [
            {
                "phaseStageId": "A",
                "phaseStageName": "A",
                "splitTime": 70,
                "greenTime": 35,
                "yellowTime": 3,
                "redTime": 32,
                "allRedTime": 2,
                "splitRatio": 0.5,
                "phaseSaturation": 0.8231,
                "phaseDirInfoDTOList": [
                    {
                        "movementKey": "d1_t2",
                        "dir8No": 1,
                        "turnDirNo": 2,
                        "turnFlowTotal": 600,
                        "laneCount": 2,
                        "criticalLaneFlow": 300,
                        "laneLevelFlow": 300,
                        "label": "北-直行",
                    }
                ],
            }
        ],
        "meta": {
            "algorithm": "single_point_optimizer",
            "version": "0.7.0",
            "target_saturation": 0.8,
            "lost_time_total_s": 10,
            "effective_green_total_s": 60,
            "max_phase_saturation": 0.8231,
            "direction_intensity_list": [
                {
                    "movementKey": "d1_t2",
                    "label": "北-直行",
                    "dir8No": 1,
                    "turnDirNo": 2,
                    "intensity": 0.8231,
                }
            ],
            "notes": ["使用文档 SQP 模型完成单路口优化。"],
        },
    },
}

CORRIDOR_OPENAPI_EXAMPLE: dict[str, Any] = {
    "corridor_id": "COR-DEMO",
    "intersection_ids": ["N1", "N2", "N3"],
    "links": [
        {"distance_m": 350, "forward_speed_kmh": 45},
        {"distance_m": 400, "forward_speed_kmh": 45},
    ],
    "intersections": [
        {
            "intersection_id": "N1",
            "phaseStageInfoList": [
                {
                    "phaseStageId": "A",
                    "phaseStageName": "南北直行",
                    "phaseDirInfoDTOList": [
                        {"dir8No": 1, "turnDirNo": 2, "turnFlowTotal": 600, "laneCount": 2},
                        {"dir8No": 5, "turnDirNo": 2, "turnFlowTotal": 550, "laneCount": 2},
                    ],
                },
                {
                    "phaseStageId": "B",
                    "phaseStageName": "东西直行",
                    "phaseDirInfoDTOList": [
                        {"dir8No": 3, "turnDirNo": 2, "turnFlowTotal": 400, "laneCount": 2},
                        {"dir8No": 7, "turnDirNo": 2, "turnFlowTotal": 380, "laneCount": 2},
                    ],
                },
            ],
        },
    ],
    "constraints": {
        "design_speed_kmh": 45,
        "default_link_spacing_m": 350,
        "min_cycle_s": 70,
        "max_cycle_s": 110,
        "min_green_s": 14,
        "max_green_s": 40,
        "progression_weight": 0.08,
        "strategy": "bidirectional",
        "target_non_coord_intensity": 0.8,
    },
}

CORRIDOR_OPENAPI_RESPONSE_EXAMPLE: dict[str, Any] = {
    "ok": True,
    "tool": "corridor_coordination_plan_tool",
    "plan": {
        "plan_type": "corridor_coordination",
        "corridor_id": "COR-DEMO",
        "coordination": {
            "bandwidth_s": 29.0,
            "bandwidth_forward_s": 30.0,
            "bandwidth_reverse_s": 29.0,
            "design_speed_kmh": 45,
            "cycle_s": 90.0,
            "total_delay_s": 45.2,
            "strategy": "bidirectional",
            "nodes": [
                {
                    "intersection_id": "N1",
                    "offset_s": 0.0,
                    "main_coordination_offset_s": 0.0,
                    "main_coordination_phase_id": "A",
                    "cycle_s": 90.0,
                    "coordinated_green_s": 30.0,
                    "green_ratio": 0.333,
                    "webster_delay_s": 15.1,
                    "phase_stage_timing_list": [
                        {"phase_stage_id": "A", "green_s": 30.0, "green_ratio": 0.333},
                        {"phase_stage_id": "B", "green_s": 25.0, "green_ratio": 0.278},
                    ],
                },
            ],
        },
        "meta": {
            "algorithm": "corridor_coordination_optimizer",
            "version": "1.0.0",
            "strategy": "bidirectional",
            "kpis": {
                "bandwidth_s": 29.0,
                "bandwidth_forward_s": 30.0,
                "bandwidth_reverse_s": 29.0,
                "total_webster_delay_s": 45.2,
                "adjacent_double_stop_proxy": 0.0,
            },
        },
    },
}


class TaskRequest(BaseModel):
    """全局任务请求."""

    task_type: str = Field(..., description="ct_check | global_optimize | congestion_response")
    payload: dict[str, Any] = Field(default_factory=dict)


class LoopRequest(BaseModel):
    """五环节闭环单轮执行请求（内部/调试）."""

    task_input: dict[str, Any] = Field(default_factory=dict)


class DiagnosisTemplateRequest(BaseModel):
    """诊断到策略模板选择请求（调试用）."""

    context: dict[str, Any] = Field(default_factory=dict)


class MultiScenarioRequest(BaseModel):
    """多场景基准请求（调试用）."""

    context: dict[str, Any] = Field(default_factory=dict)


class DebugSkillExecuteRequest(BaseModel):
    """按 skill_id 执行已注册调试技能（懒加载实例，无需为每个技能单独写路由）."""

    skill_id: str = Field(..., description="与 Skill.manifest.id 一致，见 GET /v1/skills")
    context: dict[str, Any] = Field(default_factory=dict)


class SinglePointPlanRequest(BaseModel):
    """单路口配时优化请求（外部调用接口）."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": SINGLE_POINT_OPENAPI_EXAMPLE,
            "examples": [SINGLE_POINT_OPENAPI_EXAMPLE],
        },
    )

    interId: str = Field(..., description="目标路口 ID")
    phasePlanOfTimeList: list[dict[str, Any]] = Field(
        default_factory=list,
        description="规范化相位方案输入，Swagger 推荐请求体主字段",
    )
    parameter_json_str: str | dict[str, Any] | None = Field(
        default=None,
        description="可选：字符串化参数 JSON，内容可包含 phasePlanOfTimeList",
    )
    obj_intensity: float | None = Field(default=None, description="目标供需强度，推荐使用")
    profile: dict[str, Any] = Field(default_factory=dict, description="画像输入扩展信息")
    strategy_instruction: dict[str, Any] = Field(default_factory=dict, description="策略约束")
    constraints: dict[str, Any] = Field(default_factory=dict, description="工程约束")


class CorridorPlanRequest(BaseModel):
    """干线协调（单走廊 MVP）请求."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": CORRIDOR_OPENAPI_EXAMPLE,
            "examples": [CORRIDOR_OPENAPI_EXAMPLE],
        },
    )

    corridor_id: str = Field(default="", description="走廊标识")
    intersection_ids: list[str] = Field(
        default_factory=list,
        description="沿协调正向有序的路口 ID 列表",
    )
    links: list[dict[str, Any]] | None = Field(
        default=None,
        description="相邻路口间路段，长度应为 len(intersection_ids)-1；缺省则用 default_link_spacing_m",
    )
    intersections: list[dict[str, Any]] | None = Field(
        default=None,
        description="每路口配时与流量数据（含 phaseStageInfoList / phaseDirInfoDTOList 等），索引与 intersection_ids 对齐",
    )
    profile: dict[str, Any] = Field(default_factory=dict, description="画像扩展")
    strategy_instruction: dict[str, Any] = Field(default_factory=dict, description="策略说明")
    constraints: dict[str, Any] = Field(default_factory=dict, description="周期、绿时、设计速度、strategy 等约束")


@app.get("/health")
def health():
    """健康检查."""
    return {"status": "ok", "service": "traffic-signal-control-agent"}


@app.get("/v1/planning/single-point/ui", include_in_schema=False)
def timing_optimizer_ui():
    """单路口配时优化可视化界面（跳转到静态页面）."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/debug/timing-optimizer.html")


@app.get("/v1/planning/corridor/ui", include_in_schema=False)
def corridor_coordination_ui():
    """干线协调绿波可视化界面."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/debug/corridor-coordination.html")


@app.get("/v1/signalctl-map/ui", include_in_schema=False)
def signalctl_map_ui():
    """MySQL 信控数据（路口/渠化/配时/流量/排队）高德地图叠加."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/debug/signalctl-map.html")


@app.post("/v1/task/dispatch")
def dispatch_task(req: TaskRequest):
    """任务拆解与分发：将城市级任务下发至分控子智能体."""
    master = MasterAgent()
    try:
        task_type = TaskType(req.task_type)
    except ValueError:
        task_type = TaskType.GLOBAL_OPTIMIZE
    task_id = master.dispatch_task(task_type, req.payload)
    return {"task_id": task_id, "task_type": req.task_type}


@app.post("/v1/loop/run")
def run_loop(req: LoopRequest):
    """执行一轮五环节闭环（场景认知→问题诊断→控制策略→方案生成→评价反馈）."""
    result = run_loop_once(req.task_input)
    out = {
        "loop_id": result["loop_id"],
        "meets_target": result["meets_target"],
        "phases": [
            {"phase": p.get("phase"), "success": p.get("success")}
            for p in result["phases"]
        ],
    }
    push_debug_history("loop", out)
    return out


@app.post(
    "/v1/planning/single-point",
    responses={
        200: {
            "description": "单路口优化结果，返回规范化阶段配时结构。",
            "content": {
                "application/json": {
                    "example": SINGLE_POINT_OPENAPI_RESPONSE_EXAMPLE,
                }
            },
        }
    },
)
def single_point_plan(req: SinglePointPlanRequest):
    """单路口配时优化接口，供外部系统直接调用."""
    from src.support.mcp_tools import single_point_plan_tool

    req_payload = req.model_dump(exclude_none=True)
    plan_result = single_point_plan_tool(**req_payload)
    stage_count = len(plan_result.get("plan", {}).get("phaseStageTimingList", []))
    push_debug_history(
        "single_point_plan",
        {
            "interId": req_payload.get("interId"),
            "cycleTime": plan_result.get("plan", {}).get("cycleTime"),
            "phaseStageCount": stage_count,
        },
    )
    return plan_result


@app.post(
    "/v1/planning/corridor",
    responses={
        200: {
            "description": "干线协调绿波优化结果（周期、绿时、相位差、带宽与延误）。",
            "content": {
                "application/json": {
                    "example": CORRIDOR_OPENAPI_RESPONSE_EXAMPLE,
                }
            },
        }
    },
)
def corridor_plan(req: CorridorPlanRequest):
    """干线协调配时优化接口，供可视化页面与外部系统调用."""
    from src.support.mcp_tools import corridor_coordination_plan_tool

    req_payload = req.model_dump(exclude_none=True)
    plan_result = corridor_coordination_plan_tool(**req_payload)
    coord = plan_result.get("plan", {}).get("coordination") or {}
    push_debug_history(
        "corridor_plan",
        {
            "corridor_id": req_payload.get("corridor_id"),
            "node_count": len(coord.get("nodes") or []),
            "cycle_s": coord.get("cycle_s"),
            "bandwidth_s": coord.get("bandwidth_s"),
        },
    )
    return plan_result


@app.get("/v1/skills")
def list_skills():
    """列出调试注册表中的 Skill（按需实例化读取 manifest，见 src/skills/debug_registry.py）."""
    from src.skills.debug_registry import list_debug_skill_manifests

    manifests = list_debug_skill_manifests()
    return {
        "skill_ids": [m["id"] for m in manifests],
        "skills": manifests,
    }


def _execute_debug_skill(skill_id: str, context: dict[str, Any], history_key: str) -> Any:
    from src.skills.debug_registry import build_debug_skill

    skill = build_debug_skill(skill_id)
    if skill is None:
        raise HTTPException(
            status_code=404,
            detail=f"未知 skill_id: {skill_id}，请使用 GET /v1/skills 查看已注册列表",
        )
    data = skill.execute(context or {})
    push_debug_history(history_key, data)
    return data


@app.post("/v1/debug/skill/execute")
def debug_skill_execute(req: DebugSkillExecuteRequest):
    """统一调试入口：按 skill_id 懒加载并执行 Skill，无需为每个技能单独增加路由。"""
    return _execute_debug_skill(req.skill_id, req.context, req.skill_id)


@app.post("/v1/debug/diagnosis-template")
def diagnosis_template(req: DiagnosisTemplateRequest):
    """执行“问题诊断 -> 策略模板选择”链路（调试接口）."""
    return _execute_debug_skill(
        "diagnosis_to_strategy_template",
        req.context or {},
        "diagnosis_template",
    )


@app.post("/v1/debug/multiscenario-benchmark")
def multiscenario_benchmark(req: MultiScenarioRequest):
    """执行多场景诊断与模板选择对比（调试接口）."""
    return _execute_debug_skill(
        "multi_scenario_diagnosis_benchmark",
        req.context or {},
        "multiscenario_benchmark",
    )


@app.get("/v1/debug/history")
def debug_history(limit: int = 20):
    """最近 N 次调试执行记录（进程内缓存）."""
    return {
        "capacity": history_capacity(),
        "limit": max(1, min(limit, history_capacity())),
        "items": get_debug_history(limit),
    }


@app.delete("/v1/debug/history")
def debug_history_clear():
    """清空调试历史."""
    clear_debug_history()
    return {"ok": True, "cleared": True}


# 挂载调试控制台：访问 http://localhost:8000/debug/ 打开可视化调试界面
if STATIC_DIR.is_dir():
    from fastapi.responses import RedirectResponse

    @app.get("/", include_in_schema=False)
    def _redirect_to_debug():
        return RedirectResponse(url="/debug/")

    app.mount("/debug", StaticFiles(directory=str(STATIC_DIR), html=True), name="debug-console")
