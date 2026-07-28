"""Demo 路由：城市级演示数据接口 + LLM 语义生成接口 + 统一 Run 接口.

所有模型调用均在服务端完成，前端不接触密钥。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.common.config import get_settings
from src.demo.llm_service import get_llm_service
from src.demo.run_model import TriggerSource, SceneType
from src.demo.run_store import get_run_store
from src.demo.run_orchestrator import get_orchestrator
from src.demo.demo_scheduler import get_scheduler

router = APIRouter(prefix="/v1/demo", tags=["城市级演示"])

# 演示数据文件路径
_DEMO_DATA_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "data" / "jinan_demo_data.json"


def _load_demo_data() -> dict:
    """加载济南演示数据."""
    try:
        return json.loads(_DEMO_DATA_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"演示数据加载失败: {exc}")


@router.get("/frontend-config", summary="前端公开配置")
def get_frontend_config():
    """返回前端可安全使用的公开配置，例如地图 JS Key。"""
    settings = get_settings()
    return {
        "amapJsApiKey": settings.amap_js_api_key,
        "amapSecurityJsCode": settings.amap_security_js_code,
    }


# ------------------------------------------------------------------
# 结构化数据接口（纯演示数据，快速响应）
# ------------------------------------------------------------------

@router.get("/overview", summary="城市总览数据")
def get_city_overview():
    """返回全市交通态势总览：统计数据、智能体状态、人工干预态势、问题榜单."""
    data = _load_demo_data()
    return data["cityOverview"]


@router.get("/regions", summary="区域列表")
def get_regions():
    data = _load_demo_data()
    return {"regions": data["regions"]}


@router.get("/regions/{region_id}", summary="区域详情")
def get_region(region_id: str):
    data = _load_demo_data()
    region = next((r for r in data["regions"] if r["id"] == region_id), None)
    if not region:
        raise HTTPException(status_code=404, detail=f"区域 {region_id} 不存在")
    return region


@router.get("/corridors", summary="干线列表")
def get_corridors():
    data = _load_demo_data()
    return {"corridors": data["corridors"]}


@router.get("/corridors/{corridor_id}", summary="干线详情")
def get_corridor(corridor_id: str):
    data = _load_demo_data()
    corridor = next((c for c in data["corridors"] if c["id"] == corridor_id), None)
    if not corridor:
        raise HTTPException(status_code=404, detail=f"干线 {corridor_id} 不存在")
    return corridor


@router.get("/intersections", summary="路口列表")
def get_intersections():
    data = _load_demo_data()
    return {"intersections": data["intersections"]}


@router.get("/intersections/{intersection_id}", summary="路口详情")
def get_intersection(intersection_id: str):
    data = _load_demo_data()
    inter = next((i for i in data["intersections"] if i["id"] == intersection_id), None)
    if not inter:
        raise HTTPException(status_code=404, detail=f"路口 {intersection_id} 不存在")
    return inter


@router.get("/agent-runs", summary="智能体运行记录")
def get_agent_runs(target_id: str | None = None):
    data = _load_demo_data()
    runs = data["agentRuns"]
    if target_id:
        runs = [r for r in runs if r.get("targetId") == target_id]
    return {"agentRuns": runs}


@router.get("/interventions", summary="人工干预记录")
def get_interventions(target_id: str | None = None, status: str | None = None):
    data = _load_demo_data()
    ivs = data["humanInterventions"]
    if target_id:
        ivs = [i for i in ivs if i.get("targetId") == target_id]
    if status:
        ivs = [i for i in ivs if i.get("status") == status]
    return {"interventions": ivs}


# ------------------------------------------------------------------
# LLM 语义生成接口（真实调用大模型）
# ------------------------------------------------------------------

class LLMRequest(BaseModel):
    context: dict[str, Any] = {}
    force_refresh: bool = False


@router.post("/llm/city-summary", summary="城市态势总结（LLM生成）")
def llm_city_summary(req: LLMRequest):
    """调用大模型生成全市交通态势语义总结."""
    data = _load_demo_data()
    overview = {**data["cityOverview"], **req.context}
    svc = get_llm_service()
    result = svc.city_overview_summary(overview)
    return result


@router.post("/llm/scene-cognition/{object_id}", summary="场景认知画像解读（LLM生成）")
def llm_scene_cognition(object_id: str, req: LLMRequest):
    """调用大模型解读某区域/走廊/路口的三维画像.

    profile 读取优先级：
    1. 请求上下文显式传入 profile
    2. 对象的 profile 字段（统一格式，三类对象均已支持）
    3. 对象的 sceneCognition 字段（部分旧数据兜底）
    4. 空 dict（LLM 使用兜底文案）
    """
    data = _load_demo_data()
    target = (
        next((r for r in data["regions"] if r["id"] == object_id), None)
        or next((c for c in data["corridors"] if c["id"] == object_id), None)
        or next((i for i in data["intersections"] if i["id"] == object_id), None)
    )
    if not target:
        raise HTTPException(status_code=404, detail=f"对象 {object_id} 不存在")
    # 统一三维画像来源：优先 profile，回落 sceneCognition，再回落请求 context
    sc = target.get("sceneCognition", {})
    sc_profile = {}
    if sc and any(k in sc for k in ("supply", "demand", "state")):
        sc_profile = {
            "supply": sc.get("supply", {}),
            "demand": sc.get("demand", {}),
            "state": sc.get("state", {}),
            "summary": sc.get("summary", ""),
        }
    profile = (
        req.context.get("profile")
        or target.get("profile")
        or sc_profile
        or {}
    )
    svc = get_llm_service()
    return svc.scene_cognition_report(target, profile)


@router.post("/llm/diagnosis/{object_id}", summary="诊断归因报告（LLM生成）")
def llm_diagnosis(object_id: str, req: LLMRequest):
    """调用大模型生成诊断结果的可解释报告."""
    data = _load_demo_data()
    target = (
        next((r for r in data["regions"] if r["id"] == object_id), None)
        or next((i for i in data["intersections"] if i["id"] == object_id), None)
        or next((c for c in data["corridors"] if c["id"] == object_id), None)
    )
    if not target:
        raise HTTPException(status_code=404, detail=f"对象 {object_id} 不存在")
    issues = target.get("issues", [])
    svc = get_llm_service()
    return svc.diagnosis_report(target, issues)


@router.post("/llm/strategy/{object_id}", summary="策略解读（LLM生成）")
def llm_strategy(object_id: str, req: LLMRequest):
    """调用大模型说明策略选择逻辑与预期效果."""
    data = _load_demo_data()
    target = (
        next((r for r in data["regions"] if r["id"] == object_id), None)
        or next((i for i in data["intersections"] if i["id"] == object_id), None)
        or next((c for c in data["corridors"] if c["id"] == object_id), None)
    )
    if not target:
        raise HTTPException(status_code=404, detail=f"对象 {object_id} 不存在")
    strategies = target.get("strategies", [])
    issues = target.get("issues", [])
    svc = get_llm_service()
    return svc.strategy_explanation(target, strategies, issues)


@router.post("/llm/evaluation/{run_id}", summary="闭环复盘报告（LLM生成）")
def llm_evaluation(run_id: str, req: LLMRequest):
    """调用大模型生成某次智能体闭环执行的复盘报告."""
    data = _load_demo_data()
    run = next((r for r in data["agentRuns"] if r["runId"] == run_id), None)
    if not run:
        raise HTTPException(status_code=404, detail=f"运行记录 {run_id} 不存在")
    svc = get_llm_service()
    return svc.evaluation_report(run)


@router.post("/llm/intervention-advice/{intervention_id}", summary="干预审批建议（LLM生成）")
def llm_intervention_advice(intervention_id: str, req: LLMRequest):
    """调用大模型给出人工干预操作的风险分析与审批建议."""
    data = _load_demo_data()
    iv = next((i for i in data["humanInterventions"] if i["id"] == intervention_id), None)
    if not iv:
        raise HTTPException(status_code=404, detail=f"干预记录 {intervention_id} 不存在")

    # 从数据中找到对象的当前状态作为上下文
    target_id = iv.get("targetId", "")
    context = next(
        (i for i in data["intersections"] if i["id"] == target_id),
        next((r for r in data["regions"] if r["id"] == target_id), {})
    )
    svc = get_llm_service()
    return svc.intervention_advice(iv, context)


@router.get("/scenarios", summary="交通场景列表")
def get_scenarios():
    """返回场景列表，包含规律性场景（通勤、学校接送等）和实时触发场景."""
    data = _load_demo_data()
    return {"scenarios": data.get("scenarios", [])}


@router.get("/pois", summary="交通吸引点列表")
def get_pois():
    """返回 POI（交通吸引点）列表：学校、医院、商场、办公楼、交通枢纽等."""
    data = _load_demo_data()
    return {"pois": data.get("pois", [])}


@router.get("/topology", summary="路网拓扑链路列表")
def get_topology(object_id: str | None = None):
    """返回路网拓扑边数据，可按对象 ID 过滤上下游关系."""
    data = _load_demo_data()
    links = data.get("topologyLinks", [])
    if object_id:
        links = [lk for lk in links if lk.get("fromId") == object_id or lk.get("toId") == object_id]
    return {"topologyLinks": links}


@router.get("/plans", summary="方案列表")
def get_plans(target_id: str | None = None):
    data = _load_demo_data()
    plans = data.get("plans", [])
    if target_id:
        plans = [p for p in plans if p.get("targetId") == target_id]
    return {"plans": plans}


@router.get("/plans/{plan_id}", summary="方案详情")
def get_plan(plan_id: str):
    data = _load_demo_data()
    plan = next((p for p in data.get("plans", []) if p["planId"] == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail=f"方案 {plan_id} 不存在")
    return plan


@router.get("/evaluations", summary="评价记录列表")
def get_evaluations(target_id: str | None = None):
    data = _load_demo_data()
    evals = data.get("evaluations", [])
    if target_id:
        evals = [e for e in evals if e.get("targetId") == target_id]
    return {"evaluations": evals}


@router.get("/evaluations/{eval_id}", summary="评价记录详情")
def get_evaluation(eval_id: str):
    data = _load_demo_data()
    ev = next((e for e in data.get("evaluations", []) if e["evalId"] == eval_id), None)
    if not ev:
        raise HTTPException(status_code=404, detail=f"评价记录 {eval_id} 不存在")
    return ev


class CoordinateFixRequest(BaseModel):
    coordinates: dict[str, dict[str, float]]


@router.post("/fix-coordinates", summary="批量修正路口坐标")
def fix_coordinates(req: CoordinateFixRequest):
    """批量更新路口坐标（GCJ-02）并持久化到演示数据文件."""
    data = _load_demo_data()
    updated = 0
    for inter in data.get("intersections", []):
        if inter["id"] in req.coordinates:
            coord = req.coordinates[inter["id"]]
            inter["lng"] = coord["lng"]
            inter["lat"] = coord["lat"]
            if "center" in inter:
                inter["center"] = [coord["lng"], coord["lat"]]
            updated += 1
    _DEMO_DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"updated": updated, "total": len(req.coordinates)}


@router.post("/llm/plan-summary/{plan_id}", summary="方案生成说明（LLM生成）")
def llm_plan_summary(plan_id: str, req: LLMRequest):
    """调用大模型生成配时方案的生成逻辑说明."""
    data = _load_demo_data()
    plan = next((p for p in data.get("plans", []) if p["planId"] == plan_id), None)
    if not plan:
        raise HTTPException(status_code=404, detail=f"方案 {plan_id} 不存在")
    target = (
        next((r for r in data["regions"] if r["id"] == plan.get("targetId")), None)
        or next((c for c in data["corridors"] if c["id"] == plan.get("targetId")), None)
        or next((i for i in data["intersections"] if i["id"] == plan.get("targetId")), None)
        or {}
    )
    svc = get_llm_service()
    return svc.plan_generation_summary(plan, target)


@router.post("/llm/eval-summary/{eval_id}", summary="评价复盘报告（LLM生成）")
def llm_eval_summary(eval_id: str, req: LLMRequest):
    """调用大模型生成优化效果综合评价复盘报告."""
    data = _load_demo_data()
    ev = next((e for e in data.get("evaluations", []) if e["evalId"] == eval_id), None)
    if not ev:
        raise HTTPException(status_code=404, detail=f"评价记录 {eval_id} 不存在")
    svc = get_llm_service()
    return svc.evaluation_summary(ev)


class ExperienceRequest(BaseModel):
    intervention_id: str
    effect: dict[str, Any] = {}


@router.post("/llm/experience-summary", summary="经验沉淀总结（LLM生成）")
def llm_experience_summary(req: ExperienceRequest):
    """调用大模型生成干预经验的结构化摘要，供知识库沉淀."""
    data = _load_demo_data()
    iv = next((i for i in data["humanInterventions"] if i["id"] == req.intervention_id), None)
    if not iv:
        raise HTTPException(status_code=404, detail=f"干预记录 {req.intervention_id} 不存在")
    svc = get_llm_service()
    return svc.experience_summary(iv, req.effect or iv.get("effectMetrics", {}))


# ------------------------------------------------------------------
# 人机协同干预操作接口
# ------------------------------------------------------------------

class InterventionActionRequest(BaseModel):
    intervention_id: str
    action: str  # approve | adjust | takeover | restore
    params: dict[str, Any] = {}
    operator: str = "演示用户"
    note: str = ""


@router.post("/intervention/action", summary="执行干预操作")
def do_intervention_action(req: InterventionActionRequest):
    """处理人工干预动作（演示态：更新内存状态，不真实下发）."""
    ACTION_LABELS = {
        "approve": "审批通过",
        "adjust": "参数微调",
        "takeover": "人工接管",
        "restore": "恢复自动控制",
        "reject": "驳回方案",
    }
    label = ACTION_LABELS.get(req.action, req.action)
    return {
        "ok": True,
        "action": req.action,
        "label": label,
        "operator": req.operator,
        "intervention_id": req.intervention_id,
        "params": req.params,
        "note": req.note,
        "message": f"操作【{label}】已记录，演示模式下不执行实际下发",
    }


# ==================================================================
# 统一 Run 接口（基于 RunStore 的活跃闭环运行管理）
# ==================================================================

class TriggerRunRequest(BaseModel):
    target_id: str
    target_name: str = ""
    target_type: str = "intersection"    # region / corridor / intersection
    trigger_source: str = "manual"
    scene_type: str = "dynamic"
    scene_id: str = ""
    scene_name: str = ""
    trigger_reason: str = "手动触发"


class HumanActionRequest(BaseModel):
    run_id: str
    action: str          # approve / reject / takeover / restore / adjust
    operator: str = "演示用户"
    operator_role: str = "操作员"
    reason: str = ""
    params_before: dict[str, Any] = {}
    params_after: dict[str, Any] = {}
    note: str = ""


def _find_demo_object(data: dict, obj_id: str, obj_type: str) -> dict:
    """在 demo 数据中查找对象."""
    key_map = {"region": "regions", "corridor": "corridors", "intersection": "intersections"}
    key = key_map.get(obj_type, "intersections")
    return next((o for o in data.get(key, []) if o["id"] == obj_id), {})


@router.get("/runs", summary="获取运行列表")
def get_runs(status: str | None = None, target_id: str | None = None, limit: int = 20):
    """获取智能体运行实例列表（活跃 + 历史）."""
    store = get_run_store()
    active = store.list_active()
    history = store.list_history(limit=limit, target_id=target_id)

    runs = active + history
    if target_id:
        runs = [r for r in runs if r.target_id == target_id]
    if status:
        runs = [r for r in runs if r.status.value == status]
    runs = sorted(runs, key=lambda r: r.start_time, reverse=True)[:limit]

    return {
        "runs": [r.to_summary_dict() for r in runs],
        "activeCount": len(active),
        "historyCount": len(history),
    }


@router.get("/runs/{run_id}", summary="获取 Run 详情")
def get_run_detail(run_id: str):
    store = get_run_store()
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} 不存在")
    return run.to_detail_dict()


@router.post("/runs/trigger", summary="手动触发闭环 Run")
def trigger_run(req: TriggerRunRequest):
    """手动为指定对象触发一次完整闭环 Run."""
    data = _load_demo_data()
    demo_obj = _find_demo_object(data, req.target_id, req.target_type)
    target_name = req.target_name or demo_obj.get("name", req.target_id)
    orchestrator = get_orchestrator()
    run_id = orchestrator.trigger(
        target_id=req.target_id,
        target_name=target_name,
        target_type=req.target_type,
        trigger_source=TriggerSource.MANUAL,
        scene_type=SceneType.DYNAMIC if req.scene_type == "dynamic" else SceneType.PERIODIC,
        scene_id=req.scene_id,
        scene_name=req.scene_name,
        trigger_reason=req.trigger_reason,
        trigger_confidence=1.0,
        demo_target_data=demo_obj,
    )
    return {"ok": True, "runId": run_id, "message": f"已为 {target_name} 触发闭环 Run"}


@router.post("/runs/human-action", summary="执行人机协同操作")
def run_human_action(req: HumanActionRequest):
    """对活跃 Run 执行人工审批/接管/恢复/调整操作."""
    store = get_run_store()
    run = store.get(req.run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {req.run_id} 不存在")

    ACTION_LABELS = {
        "approve": "审批通过",
        "reject": "驳回方案",
        "takeover": "人工接管",
        "restore": "恢复自动控制",
        "adjust": "参数微调",
    }

    if req.action == "approve":
        run = store.approve(req.run_id, req.operator, req.operator_role, req.note)
    elif req.action == "reject":
        run = store.reject(req.run_id, req.operator, req.operator_role, req.reason)
    elif req.action == "takeover":
        run = store.takeover(req.run_id, req.operator, req.operator_role, req.reason, req.params_after)
    elif req.action == "restore":
        run = store.restore_auto(req.run_id, req.operator, req.operator_role, req.note)
    elif req.action == "adjust":
        run = store.adjust(
            req.run_id, req.operator, req.operator_role,
            req.reason, req.params_before, req.params_after,
        )
    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作类型: {req.action}")

    label = ACTION_LABELS.get(req.action, req.action)
    return {
        "ok": True,
        "action": req.action,
        "label": label,
        "runId": req.run_id,
        "automationStatus": run.automation_status.value if run else "",
        "message": f"操作【{label}】已记录",
    }


@router.get("/runs/pending-approval/list", summary="获取待人工审批列表")
def get_pending_approvals():
    store = get_run_store()
    runs = store.list_pending_approval()
    return {"pendingApprovals": [r.to_summary_dict() for r in runs], "count": len(runs)}


@router.get("/runs/manual-takeover/list", summary="获取人工接管列表")
def get_manual_takeovers():
    store = get_run_store()
    runs = store.list_manual_takeover()
    return {"manualTakeovers": [r.to_summary_dict() for r in runs], "count": len(runs)}


@router.get("/runs/stats/global", summary="全局运行统计")
def get_global_run_stats():
    """获取今日智能体运行汇总统计，用于左侧 KPI 区显示。"""
    store = get_run_store()
    return store.get_global_stats()


@router.get("/scheduler/status", summary="调度器状态")
def get_scheduler_status():
    scheduler = get_scheduler()
    return {
        "running": scheduler.is_running(),
        "scanIntervalSeconds": scheduler._scan_interval,
    }


@router.post("/scheduler/start", summary="启动自动调度器")
def start_scheduler():
    scheduler = get_scheduler()
    scheduler.start()
    return {"ok": True, "message": "调度器已启动，将持续自动扫描触发 Run"}


@router.post("/scheduler/stop", summary="停止自动调度器")
def stop_scheduler():
    scheduler = get_scheduler()
    scheduler.stop()
    return {"ok": True, "message": "调度器已停止"}


@router.post("/runs/llm-report/{run_id}", summary="为 Run 生成 LLM 报告")
def generate_run_report(run_id: str):
    """基于 Run 的结构化快照调用 LLM 生成完整报告文本."""
    store = get_run_store()
    run = store.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} 不存在")
    if not run.report:
        raise HTTPException(status_code=400, detail="该 Run 尚未生成报告快照")

    svc = get_llm_service()
    prompt = _build_run_report_prompt(run)
    fallback = _build_run_report_fallback(run)
    result = svc._call_with_cache(f"run_report_{run_id}", prompt, fallback)

    if result.get("ok"):
        run.report.llm_text = result["text"]
        store.update(run)

    return {
        "runId": run_id,
        "report": run.report.model_dump() if run.report else {},
        "llmResult": result,
    }


def _build_run_report_prompt(run) -> str:
    r = run.report
    effect = run.effect
    metrics_str = ""
    if effect and effect.improvements:
        metrics_str = "；".join(
            f"{i['metric']} {'+' if i['delta_pct'] > 0 else ''}{i['delta_pct']:.1f}%（{'达标' if i['meets_target'] else '未达标'}）"
            for i in effect.improvements[:4]
        )

    return (
        f"请生成一份信控智能体闭环运行报告，结构如下：\n"
        f"【交通态势】{r.traffic_situation}\n"
        f"【问题发现】{r.trigger_and_findings}\n"
        f"【关键堵点】{r.key_bottleneck}\n"
        f"【策略执行】{r.strategy_and_action}\n"
        f"【优化效果】{r.effect_and_suggestion}。指标改善：{metrics_str}\n"
        f"要求：用3-5句专业文字输出综合报告，禁止markdown符号，结构清晰，数据准确。"
    )


def _build_run_report_fallback(run) -> str:
    r = run.report
    return (
        f"{r.traffic_situation} {r.trigger_and_findings} "
        f"主要处置：{r.strategy_and_action} {r.effect_and_suggestion}"
    )


# ==================================================================
# 专家经验录入 CRUD（演示态：内存 + JSON 文件持久化）
# ==================================================================

_EXPERT_EXP_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "data" / "expert_experiences_store.json"
_EXPERT_REF_FILE = Path(__file__).resolve().parent.parent.parent / "static" / "data" / "expert_experience_reference_templates.json"

# 延迟导入以避免循环
def _get_experience_model():
    from src.demo.expert_experience_model import ExpertExperienceRecord, ExpertExperienceCreateRequest
    return ExpertExperienceRecord, ExpertExperienceCreateRequest


def _load_expert_experiences() -> list[dict]:
    if _EXPERT_EXP_FILE.exists():
        try:
            return json.loads(_EXPERT_EXP_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_expert_experiences(records: list[dict]) -> None:
    _EXPERT_EXP_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/expert-experience-references", summary="参考模版列表（只读）")
def get_expert_experience_references(level: str | None = None, tag: str | None = None):
    """返回专家经验参考模版，可按 target_level 或 tag 过滤."""
    try:
        refs = json.loads(_EXPERT_REF_FILE.read_text(encoding="utf-8"))
    except Exception:
        refs = []

    if level:
        refs = [r for r in refs if r.get("suggested_target_level") in (level, "any")]
    if tag:
        refs = [r for r in refs if tag in r.get("tags", [])]

    return {"total": len(refs), "references": refs}


@router.get("/expert-experiences", summary="专家经验记录列表")
def get_expert_experiences(
    level: str | None = None,
    status: str | None = None,
    target_id: str | None = None,
    limit: int = 50,
):
    """返回已保存的专家经验记录列表，支持按 level / status / target_id 过滤."""
    records = _load_expert_experiences()

    if level:
        records = [r for r in records if r.get("target", {}).get("level") == level]
    if status:
        records = [r for r in records if r.get("status") == status]
    if target_id:
        records = [r for r in records if r.get("target", {}).get("id") == target_id]

    records = sorted(records, key=lambda r: r.get("created_at", ""), reverse=True)[:limit]
    return {"total": len(records), "records": records}


@router.post("/expert-experiences", summary="保存专家经验记录")
def create_expert_experience(body: dict):
    """接收并保存一条专家经验记录（演示态写入本地 JSON 文件）."""
    ExpertExperienceRecord, _ = _get_experience_model()

    try:
        # 支持 { record: {...} } 或直接 {...} 两种提交格式
        payload = body.get("record", body)
        record = ExpertExperienceRecord(**payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"数据校验失败: {exc}")

    records = _load_expert_experiences()
    # 覆盖同 id 的旧记录（幂等更新）
    records = [r for r in records if r.get("id") != record.id]
    records.append(record.model_dump())
    _save_expert_experiences(records)

    return {"ok": True, "id": record.id, "message": "经验记录已保存"}


@router.get("/expert-experiences/{record_id}", summary="专家经验记录详情")
def get_expert_experience(record_id: str):
    records = _load_expert_experiences()
    rec = next((r for r in records if r.get("id") == record_id), None)
    if not rec:
        raise HTTPException(status_code=404, detail=f"经验记录 {record_id} 不存在")
    return rec


@router.delete("/expert-experiences/{record_id}", summary="删除专家经验记录")
def delete_expert_experience(record_id: str):
    records = _load_expert_experiences()
    filtered = [r for r in records if r.get("id") != record_id]
    if len(filtered) == len(records):
        raise HTTPException(status_code=404, detail=f"经验记录 {record_id} 不存在")
    _save_expert_experiences(filtered)
    return {"ok": True, "id": record_id, "message": "记录已删除"}


# ------------------------------------------------------------------
# 元数据 API：从 ISSUE_CODEBOOK / TEMPLATE_META 暴露只读下拉数据源
# ------------------------------------------------------------------

@router.get("/metadata/issue-codes", summary="问题码元数据（只读）")
def get_issue_codes():
    """从 problem_issue_codes.ISSUE_CODEBOOK 序列化，供前端下拉使用."""
    from src.sub_agents.problem_issue_codes import ISSUE_CODEBOOK
    return {
        "issue_codes": [
            {"id": k, **v} for k, v in ISSUE_CODEBOOK.items()
        ]
    }


@router.get("/metadata/strategy-templates", summary="策略模板元数据（只读）")
def get_strategy_templates():
    """从 ControlStrategyAgent.TEMPLATE_META 序列化，供前端下拉使用."""
    from src.sub_agents.control_strategy import ControlStrategyAgent
    return {
        "templates": [
            {"id": k, **v} for k, v in ControlStrategyAgent.TEMPLATE_META.items()
        ]
    }
