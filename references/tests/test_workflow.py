"""五环节闭环与主智能体基础测试."""

import pytest

from src.common.models import LoopPhase, TaskType
from src.master_agent import MasterAgent
from src.sub_agents import (
    SceneCognitionAgent,
    ProblemDiagnosisAgent,
    ControlStrategyAgent,
    PlanGenerationAgent,
    EvaluationFeedbackAgent,
)
from src.workflow.loop import run_loop_once


def test_loop_phases_exist():
    """五环节枚举完整."""
    assert LoopPhase.SCENE_COGNITION.value == "scene_cognition"
    assert LoopPhase.EVALUATION_FEEDBACK.value == "evaluation_feedback"


def test_master_agent_dispatch_returns_task_id():
    """主智能体分发任务返回 task_id."""
    master = MasterAgent()
    task_id = master.dispatch_task(TaskType.GLOBAL_OPTIMIZE, {"region_id": "R1"})
    assert isinstance(task_id, str)
    assert len(task_id) > 0


def test_run_loop_once_returns_phases():
    """单轮闭环返回五环节结果."""
    result = run_loop_once({"region_id": "test"})
    assert "loop_id" in result
    assert "phases" in result
    assert len(result["phases"]) == 5
    assert result["phases"][0]["phase"] == "scene_cognition"
    assert result["phases"][4]["phase"] == "evaluation_feedback"
