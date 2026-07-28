"""方案生成算法与 MCP 工具框架测试."""

import json

from fastapi.testclient import TestClient

from src.api.main import app
from src.planning.corridor import generate_corridor_coordination_plan
from src.planning.single_point import _build_config, generate_single_point_plan
from src.sub_agents.plan_generation import PlanGenerationAgent
from src.support.mcp_tools import (
    MCPToolRegistry,
    corridor_coordination_plan_tool,
    register_plan_generation_mcp_tools,
    single_point_plan_tool,
)


def _normalized_single_point_request(inter_id: str = "INT-001") -> dict:
    return {
        "interId": inter_id,
        "obj_intensity": 0.8,
        "phasePlanOfTimeList": [
            {
                "interId": inter_id,
                "phasePlanId": f"{inter_id}-PLAN-1",
                "phasePlanName": "默认方案",
                "startTime": "00:00",
                "endTime": "24:00",
                "phaseStageInfoList": [
                    {
                        "phaseStageId": "A",
                        "phaseStageName": "A",
                        "phaseDirInfoDTOList": [
                            {"dir8No": 1, "turnDirNo": 2, "turnFlowTotal": 600, "laneCount": 2},
                            {"dir8No": 5, "turnDirNo": 2, "criticalLaneFlow": 280, "laneCount": 1},
                        ],
                    },
                    {
                        "phaseStageId": "B",
                        "phaseStageName": "B",
                        "phaseDirInfoDTOList": [
                            {"dir8No": 3, "turnDirNo": 2, "turnFlowTotal": 420, "laneCount": 2},
                            {"dir8No": 7, "turnDirNo": 2, "criticalLaneFlow": 210, "laneCount": 1},
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
        },
    }


def test_generate_single_point_plan_shape():
    plan = generate_single_point_plan({"interId": "INT-1", "constraints": {"default_cycle_s": 90}})
    assert plan["planType"] == "single_point"
    assert plan["intersectionId"] == "INT-1"
    assert plan["cycleTime"] == 90


def test_generate_single_point_plan_with_phase_plan_of_time_list():
    request = _normalized_single_point_request("INT-NEW")
    request["parameter_json_str"] = json.dumps({"phasePlanOfTimeList": request["phasePlanOfTimeList"]})
    plan = generate_single_point_plan(request)
    assert plan["intersectionId"] == "INT-NEW"
    assert plan["phasePlanId"] == "INT-NEW-PLAN-1"
    assert len(plan["phaseStageTimingList"]) == 2
    assert plan["phaseStageTimingList"][0]["phaseStageName"] == "A"
    assert plan["data"][0]["splitTime"] == plan["cycleTime"]
    assert plan["meta"]["direction_intensity_list"][0]["label"]
    assert plan["meta"]["max_phase_saturation"] <= 0.91


def test_generate_single_point_plan_uses_virtual_flow_for_zero_demand():
    plan = generate_single_point_plan(
        {
            "interId": "INT-3",
            "phasePlanOfTimeList": [
                {
                    "interId": "INT-3",
                    "phasePlanId": "PLAN-3",
                    "phasePlanName": "虚拟流量测试",
                    "phaseStageInfoList": [
                        {
                            "phaseStageId": "A",
                            "phaseStageName": "A",
                            "phaseDirInfoDTOList": [
                                {"dir8No": 1, "turnDirNo": 2, "turnFlowTotal": 0, "laneCount": 2},
                            ],
                        },
                        {
                            "phaseStageId": "B",
                            "phaseStageName": "B",
                            "phaseDirInfoDTOList": [
                                {"dir8No": 3, "turnDirNo": 2, "turnFlowTotal": 300, "laneCount": 1},
                            ],
                        },
                    ],
                }
            ],
        }
    )
    assert plan["phaseStageTimingList"][0]["greenTime"] >= 20
    assert "虚拟流量" in " ".join(plan["meta"]["notes"])


def test_single_point_build_config_exposes_tuning_knobs():
    config = _build_config(
        constraints={
            "default_cycle_s": 95,
            "target_saturation": 0.92,
            "target_saturation_min": 0.6,
            "target_saturation_max": 0.85,
            "solver_multi_start_count": 7,
            "solver_random_seed": 11,
            "solver_max_iterations": 88,
            "solver_ftol": 1e-6,
        },
        strategy_instruction={},
    )
    assert config["default_cycle_s"] == 95
    assert config["target_saturation"] == 0.85
    assert config["target_saturation_min"] == 0.6
    assert config["target_saturation_max"] == 0.85
    assert config["solver_multi_start_count"] == 7
    assert config["solver_random_seed"] == 11
    assert config["solver_max_iterations"] == 88
    assert config["solver_ftol"] == 1e-6


def test_generate_corridor_plan_shape():
    plan = generate_corridor_coordination_plan(
        {
            "corridor_id": "COR-A",
            "intersection_ids": ["A", "B", "C"],
            "constraints": {"design_speed_kmh": 50},
        }
    )
    assert plan["plan_type"] == "corridor_coordination"
    assert plan["corridor_id"] == "COR-A"
    assert len(plan["coordination"]["nodes"]) == 3
    assert plan["coordination"]["design_speed_kmh"] == 50


def test_mcp_tools_invoke_envelope():
    reg = MCPToolRegistry()
    register_plan_generation_mcp_tools(reg)
    r = reg.invoke("single_point_plan_tool", interId="X")
    assert r["ok"] is True
    assert r["isError"] is False
    assert isinstance(r["data"], list)
    assert r["tool"] == "single_point_plan_tool"
    assert r["plan"]["planType"] == "single_point"

    r2 = reg.invoke(
        "corridor_coordination_plan_tool",
        corridor_id="C1",
        intersection_ids=["i1", "i2"],
    )
    assert r2["plan"]["plan_type"] == "corridor_coordination"


def test_plan_agent_uses_mcp_when_registered():
    reg = MCPToolRegistry()
    register_plan_generation_mcp_tools(reg)
    agent = PlanGenerationAgent(mcp_tools=reg)
    out = agent.run(
        {
            "interId": "N1",
            "scope": {"type": "intersection", "ids": ["N1"]},
            "profile": {"supply": {}, "demand": {}, "state": {}},
            "strategy_instruction": {},
        }
    )
    assert out["success"] is True
    assert out["meta"]["mcp_used"] is True
    assert "single_point_plan_tool" in out["meta"]["tools"]
    assert out["plans"][0]["planType"] == "single_point"


def test_plan_agent_corridor_route():
    reg = MCPToolRegistry()
    register_plan_generation_mcp_tools(reg)
    agent = PlanGenerationAgent(mcp_tools=reg)
    out = agent.run(
        {
            "scope": {"type": "corridor", "ids": ["a", "b"]},
            "corridor_id": "COR-1",
            "strategy_instruction": {},
        }
    )
    assert out["plans"][0]["plan_type"] == "corridor_coordination"
    assert out["meta"]["mcp_used"] is True


def test_plan_agent_fallback_without_mcp():
    agent = PlanGenerationAgent()
    out = agent.run({"interId": "Z9", "scope": {"type": "intersection", "ids": ["Z9"]}})
    assert out["meta"]["mcp_used"] is False
    assert out["plans"][0]["planType"] == "single_point"


def test_callable_dict_mcp_tools():
    agent = PlanGenerationAgent(
        mcp_tools={
            "single_point_plan_tool": single_point_plan_tool,
        }
    )
    out = agent.run({"interId": "D1"})
    assert out["meta"]["mcp_used"] is True
    assert out["plans"][0]["intersectionId"] == "D1"


def test_single_point_http_api_accepts_phase_plan_payload():
    client = TestClient(app)
    response = client.post(
        "/v1/planning/single-point",
        json=_normalized_single_point_request("API-NEW-1"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["plan"]["intersectionId"] == "API-NEW-1"
    assert data["plan"]["phasePlanId"] == "API-NEW-1-PLAN-1"
    assert len(data["plan"]["data"]) == 2


def test_single_point_openapi_example_uses_phase_plan_style():
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    req_schema = schema["components"]["schemas"]["SinglePointPlanRequest"]
    example = req_schema["example"]
    assert "phasePlanOfTimeList" in example
    assert "phases" not in req_schema.get("properties", {})
    assert "intersection_id" not in req_schema.get("properties", {})
    assert example["phasePlanOfTimeList"][0]["phaseStageInfoList"][0]["phaseDirInfoDTOList"][0]["dir8No"] == 1


def test_single_point_openapi_response_example_uses_normalized_style():
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    resp_example = (
        schema["paths"]["/v1/planning/single-point"]["post"]["responses"]["200"]["content"]["application/json"]["example"]
    )
    assert resp_example["ok"] is True
    assert resp_example["isError"] is False
    assert resp_example["data"][0]["phaseStageId"] == "A"
    assert resp_example["plan"]["planType"] == "single_point"
    assert "plan_type" not in resp_example["plan"]
    assert resp_example["plan"]["phaseStageTimingList"][0]["phaseDirInfoDTOList"][0]["dir8No"] == 1


def test_corridor_plan_http_api():
    client = TestClient(app)
    response = client.post(
        "/v1/planning/corridor",
        json={
            "corridor_id": "COR-HTTP",
            "intersection_ids": ["a", "b", "c"],
            "constraints": {"design_speed_kmh": 50.0, "default_link_spacing_m": 300.0},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["tool"] == "corridor_coordination_plan_tool"
    plan = data["plan"]
    assert plan["plan_type"] == "corridor_coordination"
    assert plan["corridor_id"] == "COR-HTTP"
    coord = plan["coordination"]
    assert coord["cycle_s"] is not None
    assert len(coord["nodes"]) == 3
    assert coord["nodes"][0]["offset_s"] == 0.0
