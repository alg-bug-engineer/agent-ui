"""单路口优化方案生成算法.

规范化输入：
    - interId
    - phasePlanOfTimeList / parameter_json_str
    - phaseStageInfoList
    - phaseDirInfoDTOList
    - dir8No / turnDirNo
    - turnFlowTotal / laneCount / criticalLaneFlow

规范化输出：
    - isError / data / error
    - planType / intersectionId / cycleTime
    - phasePlanId / phasePlanName
    - phaseStageTimingList / meta

算法说明（v0.7.0）
------------------
求解器采用 SciPy SLSQP 文档模型。
目标基于转向车道级供需强度 I_dir 与目标强度 I_obj 的综合偏差最小化：
    min Σ_dir[(1+(I_dir/I_obj)^3)·abs(I_dir−I_obj)] + λ·std(I_dir) + μ·Σ_dir max(0, (I_dir−I_obj)^3)

其中：
    - dir8No 按 8 方向顺时针编号：北=1，东北=2，东=3，东南=4，南=5，西南=6，西=7，西北=8
    - turnDirNo：掉头=0，左转=1，直行=2，右转=3
    - 转向流量优先使用 criticalLaneFlow；否则用 turnFlowTotal / laneCount 折算为车道级流量
"""

from __future__ import annotations

import json
import sys
from math import floor
from typing import Any

from src.planning.types import empty_plan_meta


DEFAULT_SINGLE_POINT_CONFIG: dict[str, float | int | bool] = {
    "default_cycle_s": 120,
    "target_saturation": 0.8,
    "target_saturation_min": 0.5,
    "target_saturation_max": 0.98,
    "max_cycle_s": 190,
    "min_green_s": 20,
    "green_loss_s": 5,
    "saturation_flow_vph": 1400.0,
    "yellow_s": 3,
    "all_red_s": 2,
    "intensity_std_penalty_weight": 10.0,
    "over_target_penalty_weight": 20.0,
    "solver_multi_start_count": 20,
    "solver_random_seed": 42,
    "solver_max_iterations": 600,
    "solver_ftol": 1e-9,
    "debug_objective_terms": False,
}

ALGORITHM_VERSION = "0.7.0"
DEFAULT_PHASE_PLAN_NAME = "单路口优化默认相位方案"
DIR8_LABELS = {
    1: "北",
    2: "东北",
    3: "东",
    4: "东南",
    5: "南",
    6: "西南",
    7: "西",
    8: "西北",
}
TURN_DIR_LABELS = {
    0: "掉头",
    1: "左转",
    2: "直行",
    3: "右转",
}


def generate_single_point_plan(request: dict[str, Any]) -> dict[str, Any]:
    """生成单路口配时/相位优化方案."""
    constraints = _as_dict(request.get("constraints"))
    strategy_instruction = _as_dict(request.get("strategy_instruction"))
    parameter_payload = _extract_parameter_payload(request)
    obj_intensity = _to_float(request.get("obj_intensity"))
    if obj_intensity is not None and "target_saturation" not in strategy_instruction:
        strategy_instruction = {**strategy_instruction, "target_saturation": obj_intensity}

    config = _build_config(constraints, strategy_instruction)
    stage_defs, stage_context = _normalize_stages(request, config, parameter_payload)
    inter_id = _resolve_inter_id(request, parameter_payload, stage_context)

    if not stage_defs:
        default_cycle_time = int(config["default_cycle_s"])
        empty_stage_outputs: list[dict[str, Any]] = []
        return {
            "isError": False,
            "data": empty_stage_outputs,
            "error": None,
            "planType": "single_point",
            "intersectionId": inter_id or "UNKNOWN",
            "cycleTime": default_cycle_time,
            "phasePlanId": stage_context.get("phasePlanId"),
            "phasePlanName": stage_context.get("phasePlanName", DEFAULT_PHASE_PLAN_NAME),
            "phaseStageTimingList": empty_stage_outputs,
            "meta": empty_plan_meta("single_point_optimizer", ALGORITHM_VERSION)
            | {
                "notes": [
                    "未提供可识别的相位阶段输入，返回默认周期占位方案。",
                    "请求体需包含 phasePlanOfTimeList 或 parameter_json_str。",
                ],
            },
        }

    solution = _solve_stage_timing(stage_defs, config)
    notes = list(solution["notes"])
    if any(stage["used_virtual_flow"] for stage in stage_defs):
        notes.append("已对零流量阶段注入最小绿对应的虚拟流量，避免优化结果丢失服务。")
    if solution["max_stage_saturation"] > config["target_saturation"]:
        notes.append("存在阶段饱和度高于目标值，建议复核流量或放宽周期上限。")

    stage_outputs = [
        {
            "phaseStageId": stage["stage_id"],
            "phaseStageName": stage["stage_name"],
            "splitTime": solution["cycle_s"],
            "greenTime": solution["greens"][idx],
            "yellowTime": stage["yellow_s"],
            "redTime": max(solution["cycle_s"] - solution["greens"][idx] - stage["yellow_s"], 0),
            "allRedTime": stage["all_red_s"],
            "splitRatio": round(solution["greens"][idx] / solution["cycle_s"], 4),
            "phaseSaturation": round(solution["stage_saturation"][idx], 4),
            "phaseDirInfoDTOList": stage["stage_dir_info_list"],
        }
        for idx, stage in enumerate(stage_defs)
    ]

    return {
        "isError": False,
        "data": stage_outputs,
        "error": None,
        "planType": "single_point",
        "intersectionId": inter_id or "UNKNOWN",
        "cycleTime": solution["cycle_s"],
        "phasePlanId": stage_context.get("phasePlanId"),
        "phasePlanName": stage_context.get("phasePlanName", DEFAULT_PHASE_PLAN_NAME),
        "phaseStageTimingList": stage_outputs,
        "meta": empty_plan_meta("single_point_optimizer", ALGORITHM_VERSION)
        | {
            "solver_preference": "scipy_slsqp_document_model",
            "solver_preference_met": solution.get("solver_family") == "scipy",
            "solver": solution["solver"],
            "solver_family": solution["solver_family"],
            "target_saturation": config["target_saturation"],
            "lost_time_total_s": solution["lost_time_total_s"],
            "effective_green_total_s": solution["effective_green_total_s"],
            "max_phase_saturation": round(solution["max_stage_saturation"], 4),
            "notes": notes,
            "direction_intensity_list": solution["direction_intensity_list"],
        },
    }


def solve_single_point_timing(request: dict[str, Any]) -> dict[str, Any]:
    """对外保留的直接调用接口，返回与 MCP/HTTP 一致的配时方案."""
    return generate_single_point_plan(request)


def _build_config(
    constraints: dict[str, Any],
    strategy_instruction: dict[str, Any],
) -> dict[str, float | int | bool]:
    default_cycle_s = int(_first_number(
        constraints.get("default_cycle_s"),
        strategy_instruction.get("default_cycle_s"),
        DEFAULT_SINGLE_POINT_CONFIG["default_cycle_s"],
    ))
    target_saturation = _first_number(
        strategy_instruction.get("target_saturation"),
        constraints.get("target_saturation"),
        constraints.get("goal_saturation"),
        DEFAULT_SINGLE_POINT_CONFIG["target_saturation"],
    )
    target_saturation_min = _first_number(
        strategy_instruction.get("target_saturation_min"),
        constraints.get("target_saturation_min"),
        DEFAULT_SINGLE_POINT_CONFIG["target_saturation_min"],
    )
    target_saturation_max = _first_number(
        strategy_instruction.get("target_saturation_max"),
        constraints.get("target_saturation_max"),
        DEFAULT_SINGLE_POINT_CONFIG["target_saturation_max"],
    )
    max_cycle_s = int(_first_number(
        constraints.get("max_cycle_s"),
        DEFAULT_SINGLE_POINT_CONFIG["max_cycle_s"],
    ))
    min_green_s = int(_first_number(
        constraints.get("min_green_s"),
        constraints.get("ped_min_s"),
        DEFAULT_SINGLE_POINT_CONFIG["min_green_s"],
    ))
    phase_green_loss_s = int(_first_number(
        constraints.get("green_loss_s"),
        DEFAULT_SINGLE_POINT_CONFIG["green_loss_s"],
    ))
    saturation_flow_vph = float(_first_number(
        constraints.get("saturation_flow_vph"),
        DEFAULT_SINGLE_POINT_CONFIG["saturation_flow_vph"],
    ))
    yellow_s = int(_first_number(
        constraints.get("yellow_s"),
        DEFAULT_SINGLE_POINT_CONFIG["yellow_s"],
    ))
    all_red_s = int(_first_number(
        constraints.get("all_red_s"),
        DEFAULT_SINGLE_POINT_CONFIG["all_red_s"],
    ))
    intensity_std_penalty_weight = float(_first_number(
        strategy_instruction.get("intensity_std_penalty_weight"),
        constraints.get("intensity_std_penalty_weight"),
        constraints.get("std_penalty_weight"),
        DEFAULT_SINGLE_POINT_CONFIG["intensity_std_penalty_weight"],
    ))
    over_target_penalty_weight = float(_first_number(
        strategy_instruction.get("over_target_penalty_weight"),
        constraints.get("over_target_penalty_weight"),
        constraints.get("overflow_penalty_weight"),
        DEFAULT_SINGLE_POINT_CONFIG["over_target_penalty_weight"],
    ))
    solver_multi_start_count = int(_first_number(
        strategy_instruction.get("solver_multi_start_count"),
        constraints.get("solver_multi_start_count"),
        constraints.get("multi_start_count"),
        DEFAULT_SINGLE_POINT_CONFIG["solver_multi_start_count"],
    ))
    solver_random_seed = int(_first_number(
        strategy_instruction.get("solver_random_seed"),
        constraints.get("solver_random_seed"),
        constraints.get("random_seed"),
        DEFAULT_SINGLE_POINT_CONFIG["solver_random_seed"],
    ))
    solver_max_iterations = int(_first_number(
        strategy_instruction.get("solver_max_iterations"),
        constraints.get("solver_max_iterations"),
        constraints.get("solver_maxiter"),
        DEFAULT_SINGLE_POINT_CONFIG["solver_max_iterations"],
    ))
    solver_ftol = float(_first_number(
        strategy_instruction.get("solver_ftol"),
        constraints.get("solver_ftol"),
        constraints.get("optimizer_ftol"),
        DEFAULT_SINGLE_POINT_CONFIG["solver_ftol"],
    ))
    debug_objective_terms = _to_bool(
        strategy_instruction.get("debug_objective_terms"),
        constraints.get("debug_objective_terms"),
        DEFAULT_SINGLE_POINT_CONFIG["debug_objective_terms"],
    )
    safe_target_saturation_min = max(0.3, min(float(target_saturation_min), 0.98))
    safe_target_saturation_max = max(
        safe_target_saturation_min,
        min(float(target_saturation_max), 0.99),
    )
    return {
        "default_cycle_s": max(30, default_cycle_s),
        "target_saturation": max(
            safe_target_saturation_min,
            min(float(target_saturation), safe_target_saturation_max),
        ),
        "target_saturation_min": safe_target_saturation_min,
        "target_saturation_max": safe_target_saturation_max,
        "max_cycle_s": max(30, max_cycle_s),
        "min_green_s": max(5, min_green_s),
        "green_loss_s": max(0, phase_green_loss_s),
        "saturation_flow_vph": max(1.0, saturation_flow_vph),
        "yellow_s": max(0, yellow_s),
        "all_red_s": max(0, all_red_s),
        "intensity_std_penalty_weight": max(0.0, intensity_std_penalty_weight),
        "over_target_penalty_weight": max(0.0, over_target_penalty_weight),
        "solver_multi_start_count": max(1, solver_multi_start_count),
        "solver_random_seed": solver_random_seed,
        "solver_max_iterations": max(1, solver_max_iterations),
        "solver_ftol": max(1e-12, solver_ftol),
        "debug_objective_terms": debug_objective_terms,
    }


def _normalize_stages(
    request: dict[str, Any],
    config: dict[str, float | int],
    parameter_payload: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_stage_defs, stage_context = _extract_raw_stages(request, parameter_payload or {})
    out: list[dict[str, Any]] = []
    max_cycle_s = int(config["max_cycle_s"])
    target_saturation = float(config["target_saturation"])

    for idx, raw in enumerate(raw_stage_defs, start=1):
        if not isinstance(raw, dict):
            continue
        stage_id = str(raw.get("phaseStageId") or f"P{idx}").strip() or f"P{idx}"
        stage_name = str(raw.get("phaseStageName") or stage_id).strip() or stage_id
        flow_vph = 0.0
        saturation_flow_vph = max(
            1.0,
            _first_number(raw.get("saturation_flow_vph"), config["saturation_flow_vph"]),
        )
        min_green_s = int(max(1, _first_number(raw.get("min_green_s"), config["min_green_s"])))
        max_green_val = _to_float(raw.get("max_green_s"))
        max_green_s = int(max_green_val) if max_green_val is not None else None
        yellow_s = int(max(0, _first_number(raw.get("yellow_s"), config["yellow_s"])))
        all_red_s = int(max(0, _first_number(raw.get("all_red_s"), config["all_red_s"])))
        green_loss_s = int(max(0, _first_number(raw.get("green_loss_s"), config["green_loss_s"])))
        stage_dir_info_list = _normalize_stage_dir_info_list(raw, saturation_flow_vph)
        if not stage_dir_info_list:
            continue
        movements = [item["movementKey"] for item in stage_dir_info_list]
        flow_vph = max((item["laneLevelFlow"] for item in stage_dir_info_list), default=0.0)

        virtual_flow_vph = 0.0
        used_virtual_flow = False
        if flow_vph <= 0.0:
            virtual_flow_vph = saturation_flow_vph * min_green_s / max_cycle_s * target_saturation
            flow_for_solver = virtual_flow_vph
            used_virtual_flow = True
        else:
            flow_for_solver = flow_vph

        # movement_flows：内部统一后的逐转向车道级流量结构，供 SQP 求解使用。
        movement_flows: dict[str, Any] = {}
        turn_flow_total_vph = 0.0
        if stage_dir_info_list:
            for item in stage_dir_info_list:
                movement_flows[item["movementKey"]] = {
                    "flow_vph": item["laneLevelFlow"],
                    "saturation_flow_vph": item["saturationFlowVph"],
                    "lanes": item["laneCount"],
                    "dir8No": item["dir8No"],
                    "turnDirNo": item["turnDirNo"],
                    "turnFlowTotal": item["turnFlowTotal"],
                    "criticalLaneFlow": item["criticalLaneFlow"],
                    "laneLevelFlow": item["laneLevelFlow"],
                    "label": item["label"],
                }
                turn_flow_total_vph += item["turnFlowTotal"]
        out.append(
            {
                "stage_id": stage_id,
                "stage_name": stage_name,
                "movements": movements,
                "movement_flows": movement_flows,
                "stage_dir_info_list": stage_dir_info_list,
                "flow_vph": flow_vph,
                "turn_flow_total_vph": turn_flow_total_vph,
                "effective_flow_vph": flow_for_solver,
                "virtual_flow_vph": virtual_flow_vph,
                "used_virtual_flow": used_virtual_flow,
                "saturation_flow_vph": saturation_flow_vph,
                "critical_ratio": flow_for_solver / saturation_flow_vph,
                "min_green_s": min_green_s,
                "max_green_s": max_green_s,
                "yellow_s": yellow_s,
                "all_red_s": all_red_s,
                "green_loss_s": green_loss_s,
            }
        )

    return out, stage_context


def _extract_raw_stages(
    request: dict[str, Any],
    parameter_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    for candidate in (
        request.get("phasePlanOfTimeList"),
        parameter_payload.get("phasePlanOfTimeList"),
    ):
        raw_stage_defs, stage_context = _coerce_raw_stage_bundle(candidate)
        if raw_stage_defs:
            return raw_stage_defs, stage_context
    return [], {}


def _extract_parameter_payload(
    request: dict[str, Any],
) -> dict[str, Any]:
    for candidate in (
        request.get("parameter_json_str"),
        request.get("parameterJsonStr"),
        request.get("parameter_json"),
        request.get("parameterJson"),
    ):
        if isinstance(candidate, dict):
            return candidate
        if isinstance(candidate, str) and candidate.strip():
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                return payload
    return {}


def _resolve_inter_id(
    request: dict[str, Any],
    parameter_payload: dict[str, Any],
    stage_context: dict[str, Any],
) -> str:
    for value in (
        request.get("interId"),
        parameter_payload.get("interId"),
        stage_context.get("interId"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _coerce_raw_stage_bundle(candidate: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if isinstance(candidate, dict):
        if isinstance(candidate.get("phaseStageInfoList"), list):
            return _extract_stage_plan_bundle(candidate)
        return [], {}
    if not isinstance(candidate, list):
        return [], {}
    items = [item for item in candidate if isinstance(item, dict)]
    if not items:
        return [], {}
    plan_candidate = next(
        (item for item in items if isinstance(item.get("phaseStageInfoList"), list)),
        None,
    )
    if plan_candidate is not None:
        return _extract_stage_plan_bundle(plan_candidate)
    return items, {}


def _extract_stage_plan_bundle(plan_candidate: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    phase_stage_info_list = plan_candidate.get("phaseStageInfoList")
    if not isinstance(phase_stage_info_list, list):
        return [], {}
    return (
        [item for item in phase_stage_info_list if isinstance(item, dict)],
        {
            "interId": str(plan_candidate.get("interId") or "").strip() or None,
            "phasePlanId": str(plan_candidate.get("phasePlanId") or "").strip() or None,
            "phasePlanName": str(
                plan_candidate.get("phasePlanName") or DEFAULT_PHASE_PLAN_NAME
            ).strip() or DEFAULT_PHASE_PLAN_NAME,
            "startTime": str(plan_candidate.get("startTime") or "").strip() or None,
            "endTime": str(plan_candidate.get("endTime") or "").strip() or None,
            "controlPlanId": plan_candidate.get("controlPlanId"),
        },
    )


def _normalize_stage_dir_info_list(
    raw: dict[str, Any],
    default_saturation_flow_vph: float,
) -> list[dict[str, Any]]:
    items = raw.get("phaseDirInfoDTOList") or raw.get("phase_dir_info_list") or []
    if not isinstance(items, list):
        return []
    out: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        dir8_no = int(_first_number(item.get("dir8No"), item.get("dir_no"), 0))
        turn_dir_no = int(_first_number(item.get("turnDirNo"), item.get("turn_dir_no"), -1))
        if dir8_no not in DIR8_LABELS or turn_dir_no not in TURN_DIR_LABELS:
            continue
        lane_count = max(1, int(_first_number(
            item.get("laneCount"),
            item.get("laneNum"),
            item.get("lanes"),
            1,
        )))
        turn_flow_total = max(0.0, _first_number(
            item.get("turnFlowTotal"),
            item.get("turnFlowTotalVph"),
            item.get("turn_flow_total_vph"),
            item.get("flowTotal"),
            0.0,
        ))
        critical_lane_flow_raw = _to_float(
            item.get("criticalLaneFlow")
            if item.get("criticalLaneFlow") is not None
            else item.get("criticalLaneFlowVph")
        )
        if critical_lane_flow_raw is None:
            critical_lane_flow_raw = _to_float(item.get("critical_lane_flow_vph"))
        critical_lane_flow = max(
            0.0,
            critical_lane_flow_raw if critical_lane_flow_raw is not None else turn_flow_total / lane_count,
        )
        saturation_flow_vph = max(1.0, _first_number(
            item.get("saturationFlowVph"),
            item.get("saturation_flow_vph"),
            default_saturation_flow_vph,
        ))
        movement_key = _movement_key(dir8_no, turn_dir_no)
        out.append(
            {
                "movementKey": movement_key,
                "dir8No": dir8_no,
                "turnDirNo": turn_dir_no,
                "turnFlowTotal": round(turn_flow_total, 3),
                "laneCount": lane_count,
                "criticalLaneFlow": round(critical_lane_flow, 3),
                "laneLevelFlow": round(critical_lane_flow, 3),
                "saturationFlowVph": saturation_flow_vph,
                "phaseId": item.get("phaseId"),
                "fridList": item.get("fridList"),
                "label": _movement_label(dir8_no, turn_dir_no),
            }
        )
    return out


def _scipy_minimize_available() -> bool:
    try:
        from scipy.optimize import minimize  # noqa: F401

        return True
    except Exception:
        return False


def _has_positive_movement_flow(stage_defs: list[dict[str, Any]]) -> bool:
    return any(
        float(mdata.get("flow_vph") or 0) > 0
        for p in stage_defs
        for mdata in (p.get("movement_flows") or {}).values()
    )


def _solve_stage_timing(
    stage_defs: list[dict[str, Any]],
    config: dict[str, float | int],
) -> dict[str, Any]:
    if not _scipy_minimize_available():
        raise RuntimeError(
            "单点配时按设计优选 SciPy SLSQP 文档模型，但当前解释器无法导入 scipy。"
            f"请在已安装项目依赖的环境中运行（例如 `.venv/bin/python -m uvicorn src.api.main:app`）。"
            f" 当前 sys.executable={sys.executable!r}"
        )
    if not _has_positive_movement_flow(stage_defs):
        raise RuntimeError(
            "SciPy 文档 SQP 需要至少一个 phaseDirInfoDTOList 转向在折算后车道级流量大于 0；"
            "请检查 turnFlowTotal/laneCount 或 criticalLaneFlow。"
        )
    result = _solve_stage_timing_document_sqp(stage_defs, config)
    if result is not None:
        return result
    raise RuntimeError(
        "SciPy SLSQP 文档模型在可行域内未得到可用解，请检查 min_green_s / max_green_s、"
        "max_cycle_s 与流量是否自洽，或暂时放宽周期与绿灯上下限。"
    )


def _solve_stage_timing_document_sqp(
    stage_defs: list[dict[str, Any]],
    config: dict[str, float | int],
) -> dict[str, Any] | None:
    """文档定义的 SQP 模型：最小化各方向交通供需强度与目标强度的综合偏差。

    数学模型（来自设计文档）
    -------------------------
    决策变量：g_j  —— 第 j 个阶段（相位）的绿灯显示时长（s）

    目标函数：
        min  Σ_dir [ (1 + (I_dir/I_obj)³) · abs(I_dir − I_obj) ]
             + λ·std(I_dir) + μ·Σ_dir max(0, (I_dir − I_obj)³)

    其中：
        I_dir = vol_dir / s_dir · cycle / (t_dir − loss_dir)
        t_dir = Σ_{j: dir ∈ stage_j}  g_j          （B 矩阵 × g 向量）
        cycle = Σ_j g_j + L_intergreen               （总周期 = 有效绿 + 全红黄灯时间）
        vol_dir = max(vol_dir_raw, vol_virtual)
        vol_virtual(cycle) = (max_j(min_green_j) − loss_dir) / cycle · s_dir · I_obj
                     （动态虚拟流量：无流量方向在当前周期下的最小绿服务恰好达到目标强度 I_obj）

    约束：
        g_j ∈ [min_green_j, max_green_j]
        Σ_j g_j + L_intergreen ∈ [min_cycle, max_cycle]

    求解：SciPy SLSQP，20 次随机多初值，取目标最小解。
    """
    try:
        from scipy.optimize import minimize
        import random as _random
    except Exception:
        return None

    I_obj = float(config["target_saturation"])
    std_penalty_weight = float(config["intensity_std_penalty_weight"])
    over_target_penalty_weight = float(config["over_target_penalty_weight"])
    debug_objective_terms = bool(config.get("debug_objective_terms", False))
    max_cycle_s = int(config["max_cycle_s"])
    s_default = float(config["saturation_flow_vph"])
    solver_multi_start_count = int(config["solver_multi_start_count"])
    solver_random_seed = int(config["solver_random_seed"])
    solver_max_iterations = int(config["solver_max_iterations"])
    solver_ftol = float(config["solver_ftol"])
    eps = 1e-6
    n = len(stage_defs)

    # ── 常量预计算 ──────────────────────────────────────────────
    # 总插入间隔（黄灯 + 全红）：不是决策变量，但影响 cycle 计算
    L_intergreen = sum(
        float(p.get("yellow_s", 3)) + float(p.get("all_red_s", 0))
        for p in stage_defs
    )
    min_green = [float(p["min_green_s"]) for p in stage_defs]
    max_green = [
        float(p["max_green_s"]) if p["max_green_s"] is not None else float(max_cycle_s)
        for p in stage_defs
    ]
    loss_stage = [float(p["green_loss_s"]) for p in stage_defs]
    min_cycle_s = sum(min_green) + L_intergreen
    max_cycle_eff = max(min_cycle_s, float(max_cycle_s))  # 实际用的最大周期

    # ── 守卫：要求至少一个方向有真实流量数据 ──────────────────
    # 若全部方向均为虚拟流量，优化器缺乏有效约束，结果不可信。
    has_real_mvt_flow = any(
        float(mdata.get("flow_vph") or 0) > 0
        for p in stage_defs
        for mdata in (p.get("movement_flows") or {}).values()
    )
    if not has_real_mvt_flow:
        return None

    # ── 提取各方向（dir）数据 ────────────────────────────────────
    # 每个方向 = 一个转向车流，可同时出现在多个阶段（共享绿灯）
    directions: list[dict[str, Any]] = []
    mvt_seen: dict[str, int] = {}  # mvt -> index in directions

    # 所有阶段最小绿的最大值，用于虚拟流量计算
    max_min_green = max(min_green) if min_green else 20.0

    for stage_idx, stage in enumerate(stage_defs):
        mvt_flows = stage.get("movement_flows") or {}
        for mvt in stage.get("movements", []):
            mdata = mvt_flows.get(mvt) or {}
            vol_raw = float(mdata.get("flow_vph") or 0.0)
            s_dir = float(mdata.get("saturation_flow_vph") or s_default)
            dir8_no = int(mdata.get("dir8No"))
            turn_dir_no = int(mdata.get("turnDirNo"))
            label = str(mdata.get("label") or _movement_label(dir8_no, turn_dir_no))

            # 虚拟流量（零需求方向）改为在 compute_I 中按当前周期动态计算。
            # 这里仅保留真实流量与动态虚拟流量所需的参数。
            loss_for_virtual = loss_stage[stage_idx]

            if mvt in mvt_seen:
                # 该方向已在其他阶段出现，追加该阶段索引（共享绿灯）
                d = directions[mvt_seen[mvt]]
                d["stages"].append(stage_idx)
                d["vol_raw"] = max(d["vol_raw"], vol_raw)
                d["virtual_loss_dir"] = min(d["virtual_loss_dir"], loss_for_virtual)
            else:
                mvt_seen[mvt] = len(directions)
                directions.append({
                    "mvt": mvt,
                    "stages": [stage_idx],
                    "vol_raw": vol_raw,
                    "s_dir": s_dir,
                    "loss_dir": loss_stage[stage_idx],
                    "virtual_loss_dir": loss_for_virtual,
                    "dir8No": dir8_no,
                    "turnDirNo": turn_dir_no,
                    "label": label or mvt,
                })

    if not directions:
        return None

    # ── 目标函数 ─────────────────────────────────────────────────
    def compute_I(g: list[float]) -> list[float]:
        cycle = sum(g) + L_intergreen
        result_I = []
        for d in directions:
            g_dir = sum(g[j] for j in d["stages"])
            eff = max(g_dir - d["loss_dir"], eps)
            vol_virtual = (
                max(0.0, max_min_green - d["virtual_loss_dir"]) / max(cycle, eps) * d["s_dir"] * I_obj
            )
            vol_dir = max(d["vol_raw"], vol_virtual)
            I = vol_dir / d["s_dir"] * cycle / eff
            result_I.append(I)
        return result_I

    def evaluate_objective_terms(
        g: list[float],
    ) -> tuple[float, float, float, float, list[tuple[str, float, float, float, float]]]:
        intensities = compute_I(g)
        base_total = 0.0
        over_target_total = 0.0
        term_details: list[tuple[str, float, float, float, float]] = []
        for idx, I in enumerate(intensities):
            overflow = max(0.0, (I - I_obj) ** 3)
            w = 1.0 + (I / I_obj) ** 3
            term_value = abs(I - I_obj)
            base_total += term_value
            over_target_total += overflow
            term_details.append((directions[idx]["mvt"], I, w, term_value, overflow))
        mean_I = sum(intensities) / max(len(intensities), 1)
        variance = sum((I - mean_I) ** 2 for I in intensities) / max(len(intensities), 1)
        std_penalty = std_penalty_weight * (variance + 1e-12) ** 0.5
        overflow_penalty = over_target_penalty_weight * over_target_total
        total = base_total + std_penalty + overflow_penalty
        return total, base_total, std_penalty, overflow_penalty, term_details

    def print_objective_terms(tag: str, g: list[float]) -> None:
        total, base_total, std_penalty, overflow_penalty, term_details = evaluate_objective_terms(g)
        cycle = sum(g) + L_intergreen
        greens_fmt = ", ".join(f"{value:.3f}" for value in g)
        print(f"[objective:{tag}] cycle={cycle:.3f}, greens=[{greens_fmt}]")
        for mvt, I, w, term_value, overflow in term_details:
            print(
                f"  term[{mvt}]: I={I:.6f}, weight={w:.6f}, "
                f"weighted_abs_error={term_value:.6f}, overflow={overflow:.6f}"
            )
        print(
            f"  base_total={base_total:.6f}, "
            f"std_penalty: weight={std_penalty_weight:.6f}, "
            f"std={std_penalty / max(std_penalty_weight, 1e-12):.6f}, "
            f"value={std_penalty:.6f}"
        )
        print(
            f"  overflow_penalty: weight={over_target_penalty_weight:.6f}, "
            f"sum_overflow_cubed={overflow_penalty / max(over_target_penalty_weight, 1e-12):.6f}, "
            f"value={overflow_penalty:.6f}"
        )
        print(f"  objective_total={total:.6f}")

    def objective(g: list[float]) -> float:
        total, _, _, _, _ = evaluate_objective_terms(g)
        return total

    # ── 约束 & 边界 ─────────────────────────────────────────────
    g_sum_min = max(0.0, min_cycle_s - L_intergreen)
    g_sum_max = max(g_sum_min, max_cycle_eff - L_intergreen)

    constraints = [
        {"type": "ineq", "fun": lambda g: sum(g) - g_sum_min},   # Σg ≥ g_sum_min
        {"type": "ineq", "fun": lambda g: g_sum_max - sum(g)},   # Σg ≤ g_sum_max
    ]
    bounds = [(min_green[j], max_green[j]) for j in range(n)]

    # ── 多初值（参考实现：每相位在可行域内独立均匀随机采样）────────
    rng = _random.Random(solver_random_seed)

    def make_random_init() -> list[float]:
        # 每相位在 [min_green_j, max_green_j] 内独立均匀随机，与其他相位无关
        return [
            min_green[j] + rng.random() * (max_green[j] - min_green[j])
            for j in range(n)
        ]

    initial_points: list[list[float]] = [
        [min_green[j] for j in range(n)],  # 第 0 次：全最小绿（确定性起点）
        *[make_random_init() for _ in range(max(0, solver_multi_start_count - 1))],
    ]

    best_success_result: Any = None
    best_success_value: float | None = None
    best_fallback_result: Any = None
    best_fallback_value: float | None = None

    for idx, init in enumerate(initial_points):
        try:
            res = minimize(
                objective, init,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": solver_max_iterations, "ftol": solver_ftol, "disp": False},
            )
        except Exception:
            continue
        val = float(getattr(res, "fun", objective(list(res.x))))
        if val < 0:
            continue
        if debug_objective_terms:
            print(
                f"[minimize:{idx}] success={bool(getattr(res, 'success', False))}, "
                f"status={getattr(res, 'status', 'NA')}, "
                f"fun={val:.6f}, message={getattr(res, 'message', '')}"
            )
            print_objective_terms(f"minimize_{idx}", [float(x) for x in res.x])
        if bool(getattr(res, "success", False)):
            if best_success_value is None or val < best_success_value:
                best_success_result = res
                best_success_value = val
        if best_fallback_value is None or val < best_fallback_value:
            best_fallback_result = res
            best_fallback_value = val

    best_result = best_success_result if best_success_result is not None else best_fallback_result
    if best_result is None:
        return None
    if debug_objective_terms:
        selected_mode = "success_preferred"
        selected_value = best_success_value
        if best_success_result is None:
            selected_mode = "fallback_min_fun"
            selected_value = best_fallback_value
        print(
            f"[minimize:selected] mode={selected_mode}, "
            f"fun={(selected_value if selected_value is not None else float('nan')):.6f}, "
            f"success={bool(getattr(best_result, 'success', False))}, "
            f"status={getattr(best_result, 'status', 'NA')}, "
            f"message={getattr(best_result, 'message', '')}"
        )

    # ── 整数化并输出 ──────────────────────────────────────────────
    greens = _round_greens_to_ints(stage_defs, [float(x) for x in best_result.x], int(g_sum_max))
    cycle_s = int(round(sum(greens) + L_intergreen))
    G_eff = sum(greens)

    # 最终各方向供需强度
    final_I = compute_I([float(g) for g in greens])
    dir_intensity_list = [
        {
            "movementKey": d["mvt"],
            "label": d.get("label") or d["mvt"],
            "dir8No": d.get("dir8No"),
            "turnDirNo": d.get("turnDirNo"),
            "intensity": round(final_I[i], 4),
        }
        for i, d in enumerate(directions)
    ]

    # 各相位饱和度：取该阶段所有方向中最大供需强度
    stage_saturation: list[float] = []
    for stage_idx, stage in enumerate(stage_defs):
        stage_I = [
            final_I[mvt_seen[m]]
            for m in stage.get("movements", [])
            if m in mvt_seen
        ]
        stage_saturation.append(max(stage_I) if stage_I else 0.0)

    return {
        "solver": "scipy_slsqp_document_model",
        "solver_family": "scipy",
        "cycle_s": cycle_s,
        "greens": greens,
        "lost_time_total_s": int(round(L_intergreen)),
        "effective_green_total_s": G_eff,
        "stage_saturation": stage_saturation,
        "max_stage_saturation": max(stage_saturation, default=0.0),
        "direction_intensity_list": dir_intensity_list,
        "notes": [
            (
                f"使用文档 SQP 模型（{solver_multi_start_count}次多初值，"
                f"seed={solver_random_seed}）：各方向供需强度 I_dir 与目标强度 I_obj 综合偏差最小。"
            ),
            (
                "目标函数：min Σ[(1+(I/I_obj)³)·abs(I−I_obj)]"
                f" + {std_penalty_weight:.3f}·std(I)"
                f" + {over_target_penalty_weight:.3f}·Σmax(0,(I−I_obj)³)，共 {len(directions)} 个方向。"
            ),
        ],
    }


def _round_greens_to_ints(
    stage_defs: list[dict[str, Any]],
    greens: list[float],
    max_effective_green_s: int,
) -> list[int]:
    rounded: list[int] = []
    fractions: list[float] = []
    for idx, stage in enumerate(stage_defs):
        raw = float(greens[idx])
        lower = int(stage["min_green_s"])
        upper = int(stage["max_green_s"]) if stage["max_green_s"] is not None else max_effective_green_s
        clipped = min(max(raw, lower), upper)
        integer = int(floor(clipped))
        rounded.append(max(lower, integer))
        fractions.append(clipped - floor(clipped))

    while sum(rounded) > max_effective_green_s:
        candidates = [idx for idx, stage in enumerate(stage_defs) if rounded[idx] > int(stage["min_green_s"])]
        if not candidates:
            break
        candidate = min(
            candidates,
            key=lambda idx: (
                stage_defs[idx]["critical_ratio"],
                -rounded[idx],
                idx,
            ),
        )
        rounded[candidate] -= 1

    target_total = min(
        max_effective_green_s,
        max(sum(rounded), int(round(sum(greens)))),
    )
    while sum(rounded) < target_total:
        candidates = [
            idx
            for idx, stage in enumerate(stage_defs)
            if stage["max_green_s"] is None or rounded[idx] < int(stage["max_green_s"])
        ]
        if not candidates:
            break
        candidate = max(
            candidates,
            key=lambda idx: (
                fractions[idx],
                stage_defs[idx]["critical_ratio"],
                stage_defs[idx]["effective_flow_vph"],
            ),
        )
        rounded[candidate] += 1
        fractions[candidate] = 0.0

    return rounded


def _movement_key(dir8_no: int, turn_dir_no: int) -> str:
    return f"d{dir8_no}_t{turn_dir_no}"


def _movement_label(dir8_no: int, turn_dir_no: int) -> str:
    return f"{DIR8_LABELS.get(dir8_no, dir8_no)}-{TURN_DIR_LABELS.get(turn_dir_no, turn_dir_no)}"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _first_number(*values: Any) -> float:
    for value in values:
        parsed = _to_float(value)
        if parsed is not None:
            return parsed
    return 0.0


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_bool(*values: Any) -> bool:
    for value in values:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on"}:
                return True
            if normalized in {"0", "false", "no", "n", "off", ""}:
                return False
    return False
