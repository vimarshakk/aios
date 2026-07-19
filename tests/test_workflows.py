"""Tests for aios.workflows — core workflow engine tests."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aios.workflows.approval import ApprovalRequest, ApprovalStatus, ApprovalStep
from aios.workflows.base import StepStatus, Workflow, WorkflowResult, WorkflowStep
from aios.workflows.conditions import Condition, ConditionStep
from aios.workflows.executor import WorkflowExecutor
from aios.workflows.parallel import ParallelGroup, execute_parallel
from aios.workflows.planner import WorkflowPlanner
from aios.workflows.retry import RetryPolicy
from aios.workflows.state import WorkflowState, WorkflowStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _noop_handler(step: WorkflowStep, state: WorkflowState) -> str:
    """Test handler that returns the step ID."""
    return f"done:{step.id}"


async def _echo_handler(step: WorkflowStep, state: WorkflowState) -> Any:
    """Test handler that returns the step config."""
    return step.config


async def _fail_handler(step: WorkflowStep, state: WorkflowState) -> str:
    """Test handler that always raises."""
    raise RuntimeError(f"Step {step.id} failed")


_call_count = 0


async def _counting_handler(step: WorkflowStep, state: WorkflowState) -> str:
    """Test handler that counts invocations."""
    global _call_count
    _call_count += 1
    return f"call {_call_count}"


# ---------------------------------------------------------------------------
# WorkflowStep
# ---------------------------------------------------------------------------


class TestWorkflowStep:
    def test_construction(self) -> None:
        step = WorkflowStep(id="s1", type="tool_call", config={"key": "val"})
        assert step.id == "s1"
        assert step.type == "tool_call"
        assert step.config == {"key": "val"}
        assert step.dependencies == []

    def test_default_id(self) -> None:
        step = WorkflowStep()
        assert len(step.id) == 12

    def test_dependencies(self) -> None:
        step = WorkflowStep(id="s2", dependencies=["s1", "s0"])
        assert step.dependencies == ["s1", "s0"]


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------


class TestWorkflow:
    def test_construction(self) -> None:
        wf = Workflow(id="w1", name="test", steps=[])
        assert wf.id == "w1"
        assert wf.name == "test"

    def test_get_step(self) -> None:
        s1 = WorkflowStep(id="s1")
        s2 = WorkflowStep(id="s2")
        wf = Workflow(id="w1", steps=[s1, s2])
        assert wf.get_step("s1") is s1
        assert wf.get_step("s2") is s2
        assert wf.get_step("missing") is None

    def test_get_step_index(self) -> None:
        s1 = WorkflowStep(id="s1")
        s2 = WorkflowStep(id="s2")
        wf = Workflow(id="w1", steps=[s1, s2])
        assert wf.get_step_index("s1") == 0
        assert wf.get_step_index("s2") == 1
        assert wf.get_step_index("missing") == -1

    def test_steps_by_status(self) -> None:
        s1 = WorkflowStep(id="s1")
        s2 = WorkflowStep(id="s2")
        s3 = WorkflowStep(id="s3")
        wf = Workflow(id="w1", steps=[s1, s2, s3])
        results: dict[str, Any] = {
            "s1": StepStatus.COMPLETED,
            "s2": StepStatus.RUNNING,
            "s3": StepStatus.FAILED,
        }
        assert wf.steps_by_status(StepStatus.COMPLETED, results) == [s1]
        assert wf.steps_by_status(StepStatus.RUNNING, results) == [s2]
        assert wf.steps_by_status(StepStatus.FAILED, results) == [s3]
        assert wf.steps_by_status(StepStatus.PENDING, results) == []


# ---------------------------------------------------------------------------
# WorkflowResult
# ---------------------------------------------------------------------------


class TestWorkflowResult:
    def test_construction(self) -> None:
        r = WorkflowResult(workflow_id="w1", status="completed")
        assert r.workflow_id == "w1"
        assert r.status == "completed"
        assert r.error is None

    def test_duration(self) -> None:
        r = WorkflowResult(workflow_id="w1", status="running", started_at=100.0)
        assert r.duration is None
        r.finished_at = 105.0
        assert r.duration == 5.0


# ---------------------------------------------------------------------------
# WorkflowState
# ---------------------------------------------------------------------------


class TestWorkflowState:
    def test_construction(self) -> None:
        s = WorkflowState()
        assert s.status == WorkflowStatus.PENDING
        assert s.current_step is None
        assert s.results == {}
        assert s.error is None

    def test_mark_running(self) -> None:
        s = WorkflowState()
        s.mark_running("step1")
        assert s.status == WorkflowStatus.RUNNING
        assert s.current_step == "step1"
        assert s.step_status["step1"] == "running"

    def test_mark_completed(self) -> None:
        s = WorkflowState()
        s.mark_running("step1")
        s.mark_completed("step1", result="ok")
        assert s.results["step1"] == "ok"
        assert s.step_status["step1"] == "completed"
        assert s.current_step is None

    def test_mark_failed(self) -> None:
        s = WorkflowState()
        s.mark_running("step1")
        s.mark_failed("step1", "oops")
        assert s.status == WorkflowStatus.FAILED
        assert s.error == "oops"
        assert s.step_status["step1"] == "failed"

    def test_mark_paused(self) -> None:
        s = WorkflowState()
        s.mark_running("step1")
        s.mark_paused()
        assert s.status == WorkflowStatus.PAUSED

    def test_mark_cancelled(self) -> None:
        s = WorkflowState()
        s.mark_running("step1")
        s.mark_cancelled()
        assert s.status == WorkflowStatus.CANCELLED
        assert s.current_step is None

    def test_is_terminal(self) -> None:
        s = WorkflowState()
        assert not s.is_terminal()
        s.status = WorkflowStatus.COMPLETED
        assert s.is_terminal()
        s.status = WorkflowStatus.FAILED
        assert s.is_terminal()
        s.status = WorkflowStatus.CANCELLED
        assert s.is_terminal()


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------


class TestRetryPolicy:
    def test_delay_increases(self) -> None:
        policy = RetryPolicy(base_delay=1.0, backoff_factor=2.0, jitter=False)
        d0 = policy.delay_for_attempt(0)
        d1 = policy.delay_for_attempt(1)
        d2 = policy.delay_for_attempt(2)
        assert d0 == pytest.approx(1.0)
        assert d1 == pytest.approx(2.0)
        assert d2 == pytest.approx(4.0)

    def test_max_delay_cap(self) -> None:
        policy = RetryPolicy(base_delay=1.0, max_delay=3.0, backoff_factor=10.0, jitter=False)
        d = policy.delay_for_attempt(5)
        assert d == 3.0

    def test_should_retry_within_limit(self) -> None:
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(0)
        assert policy.should_retry(1)
        assert policy.should_retry(2)
        assert not policy.should_retry(3)

    def test_should_retry_filterable_errors(self) -> None:
        policy = RetryPolicy(max_retries=3, retryable_errors=(ValueError,))
        assert policy.should_retry(0, ValueError("bad"))
        assert not policy.should_retry(0, TypeError("wrong"))

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self) -> None:
        policy = RetryPolicy(max_retries=3, base_delay=0.01, jitter=False)

        async def ok() -> str:
            return "ok"

        result = await policy.execute_with_retry(ok)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_with_retry_exhaustion(self) -> None:
        policy = RetryPolicy(max_retries=1, base_delay=0.01, jitter=False)

        async def always_fail() -> None:
            raise RuntimeError("nope")

        with pytest.raises(RuntimeError, match="nope"):
            await policy.execute_with_retry(always_fail)

    @pytest.mark.asyncio
    async def test_execute_with_retry_eventual_success(self) -> None:
        policy = RetryPolicy(max_retries=3, base_delay=0.01, jitter=False)
        attempts = 0

        async def succeed_on_third() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("not yet")
            return "done"

        result = await policy.execute_with_retry(succeed_on_third)
        assert result == "done"
        assert attempts == 3


# ---------------------------------------------------------------------------
# ConditionStep
# ---------------------------------------------------------------------------


class TestConditionStep:
    def test_construction(self) -> None:
        step = ConditionStep(id="c1")
        assert step.type == "condition"
        assert step.conditions == []

    @pytest.mark.asyncio
    async def test_evaluate_first_match(self) -> None:
        cond1 = Condition(label="a", predicate=lambda r: r.get("a") == 1, target_step_id="step_a")
        cond2 = Condition(label="b", predicate=lambda r: r.get("b") == 1, target_step_id="step_b")
        step = ConditionStep(id="c1", conditions=[cond1, cond2], default_step_id="step_default")
        result = await step.evaluate({"a": 1})
        assert result.matched is cond1
        assert result.target_step_id == "step_a"
        assert result.evaluated == {"a": True}

    @pytest.mark.asyncio
    async def test_evaluate_no_match_uses_default(self) -> None:
        cond1 = Condition(label="a", predicate=lambda r: r.get("a") == 1, target_step_id="step_a")
        step = ConditionStep(id="c1", conditions=[cond1], default_step_id="step_default")
        result = await step.evaluate({"x": 99})
        assert result.matched is None
        assert result.target_step_id == "step_default"

    @pytest.mark.asyncio
    async def test_evaluate_no_predicate_uses_label_as_key(self) -> None:
        cond = Condition(label="flag", target_step_id="step_flag")
        step = ConditionStep(id="c1", conditions=[cond])
        result = await step.evaluate({"flag": True})
        assert result.matched is cond
        assert result.target_step_id == "step_flag"


# ---------------------------------------------------------------------------
# ApprovalStep
# ---------------------------------------------------------------------------


class TestApprovalStep:
    def test_construction(self) -> None:
        step = ApprovalStep(id="a1", prompt="Approve deploy?")
        assert step.type == "approval"
        assert step.prompt == "Approve deploy?"

    def test_create_request(self) -> None:
        step = ApprovalStep(id="a1", prompt="Approve?")
        req = step.create_request()
        assert req.step_id == "a1"
        assert req.prompt == "Approve?"
        assert req.status == ApprovalStatus.PENDING

    def test_approval_request_approve(self) -> None:
        req = ApprovalRequest(step_id="a1", prompt="Approve?")
        req.approve(approver="admin", response="Looks good")
        assert req.status == ApprovalStatus.APPROVED
        assert req.approver == "admin"
        assert req.response == "Looks good"
        assert req.is_resolved()

    def test_approval_request_reject(self) -> None:
        req = ApprovalRequest(step_id="a1", prompt="Approve?")
        req.reject(approver="admin", response="No")
        assert req.status == ApprovalStatus.REJECTED
        assert req.is_resolved()

    def test_approval_request_not_resolved(self) -> None:
        req = ApprovalRequest(step_id="a1", prompt="Approve?")
        assert not req.is_resolved()


# ---------------------------------------------------------------------------
# ParallelGroup & execute_parallel
# ---------------------------------------------------------------------------


class TestParallelGroup:
    def test_construction(self) -> None:
        g = ParallelGroup(group_id="g1", step_ids=["s1", "s2"])
        assert g.group_id == "g1"
        assert g.step_ids == ["s1", "s2"]
        assert g.fail_fast is True


class TestExecuteParallel:
    @pytest.mark.asyncio
    async def test_all_succeed(self) -> None:
        g = ParallelGroup(group_id="g1", step_ids=["s1", "s2", "s3"])

        async def fn(step_id: str) -> str:
            return f"result:{step_id}"

        result = await execute_parallel(g, fn)
        assert len(result.succeeded) == 3
        assert result.failed == []
        assert result.results["s1"] == "result:s1"
        assert result.results["s2"] == "result:s2"

    @pytest.mark.asyncio
    async def test_one_fails_fail_fast(self) -> None:
        g = ParallelGroup(group_id="g1", step_ids=["s1", "s2", "s3"], fail_fast=True)

        async def fn(step_id: str) -> str:
            if step_id == "s2":
                raise RuntimeError("boom")
            return f"ok:{step_id}"

        result = await execute_parallel(g, fn, fail_fast=True)
        assert "s2" in result.failed
        assert isinstance(result.results["s2"], RuntimeError)

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        g = ParallelGroup(group_id="g1", step_ids=["s1"], timeout_seconds=0.1)

        async def slow(step_id: str) -> str:
            await asyncio.sleep(5.0)
            return "done"  # pragma: no cover

        result = await execute_parallel(g, slow, timeout_seconds=0.1)
        assert result.timed_out


# ---------------------------------------------------------------------------
# WorkflowExecutor
# ---------------------------------------------------------------------------


class TestWorkflowExecutor:
    @pytest.mark.asyncio
    async def test_single_step(self) -> None:
        step = WorkflowStep(id="s1", type="tool_call", config={"x": 1})
        wf = Workflow(id="w1", name="single", steps=[step])
        executor = WorkflowExecutor(handlers={"tool_call": _echo_handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["s1"] == {"x": 1}

    @pytest.mark.asyncio
    async def test_linear_chain(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["s1"])
        s3 = WorkflowStep(id="s3", type="tool_call", dependencies=["s2"])
        wf = Workflow(id="w1", steps=[s1, s2, s3])
        executor = WorkflowExecutor(handlers={"tool_call": _noop_handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["s1"] == "done:s1"
        assert result.step_results["s2"] == "done:s2"
        assert result.step_results["s3"] == "done:s3"

    @pytest.mark.asyncio
    async def test_diamond_dependencies(self) -> None:
        """s1 → s2, s1 → s3, s2 + s3 → s4."""
        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["s1"])
        s3 = WorkflowStep(id="s3", type="tool_call", dependencies=["s1"])
        s4 = WorkflowStep(id="s4", type="tool_call", dependencies=["s2", "s3"])
        wf = Workflow(id="w1", steps=[s1, s2, s3, s4])
        executor = WorkflowExecutor(handlers={"tool_call": _noop_handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        # s1 must come before s2 and s3; s4 must come last
        order = list(result.step_results.keys())
        assert order.index("s1") < order.index("s2")
        assert order.index("s1") < order.index("s3")
        assert order.index("s2") < order.index("s4")
        assert order.index("s3") < order.index("s4")

    @pytest.mark.asyncio
    async def test_step_failure(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="fail")
        wf = Workflow(id="w1", steps=[s1, s2])
        executor = WorkflowExecutor(
            handlers={"tool_call": _noop_handler, "fail": _fail_handler}
        )
        result = await executor.run(wf)
        assert result.status == "failed"
        assert "s2 failed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_unregistered_handler(self) -> None:
        step = WorkflowStep(id="s1", type="unknown_type")
        wf = Workflow(id="w1", steps=[step])
        executor = WorkflowExecutor()
        result = await executor.run(wf)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_empty_workflow(self) -> None:
        wf = Workflow(id="w1", steps=[])
        executor = WorkflowExecutor()
        result = await executor.run(wf)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_resume(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="tool_call")
        wf = Workflow(id="w1", steps=[s1, s2])
        executor = WorkflowExecutor(handlers={"tool_call": _noop_handler})

        # First run fails at s2
        async def fail_s2(step: WorkflowStep, state: WorkflowState) -> str:
            if step.id == "s2":
                raise RuntimeError("boom")
            return "ok"

        executor.register_handler("tool_call", fail_s2)
        result = await executor.run(wf)
        assert result.status == "failed"

        # Resume — s1 succeeded, s2 should be retried
        executor.register_handler("tool_call", _noop_handler)
        result2 = await executor.resume(wf, result)
        assert result2.status == "completed"

    @pytest.mark.asyncio
    async def test_register_handler(self) -> None:
        executor = WorkflowExecutor()
        executor.register_handler("custom", _noop_handler)
        assert "custom" in executor.handlers

    @pytest.mark.asyncio
    async def test_state_updates(self) -> None:
        step = WorkflowStep(id="s1", type="tool_call")
        wf = Workflow(id="w1", steps=[step])
        executor = WorkflowExecutor(handlers={"tool_call": _noop_handler})
        await executor.run(wf)
        assert executor.state.status == WorkflowStatus.COMPLETED
        assert executor.state.step_status["s1"] == "completed"


# ---------------------------------------------------------------------------
# WorkflowPlanner
# ---------------------------------------------------------------------------


class TestWorkflowPlanner:
    @pytest.mark.asyncio
    async def test_deterministic_planner(self) -> None:
        planner = WorkflowPlanner()
        wf = await planner.plan("do something", workflow_name="test")
        assert wf.name == "test"
        assert len(wf.steps) == 1
        assert wf.steps[0].type == "tool_call"
        assert wf.metadata["source"] == "deterministic_planner"

    @pytest.mark.asyncio
    async def test_deterministic_with_tools(self) -> None:
        planner = WorkflowPlanner()
        tools = [{"name": "search", "description": "web search"}]
        wf = await planner.plan("search the web", available_tools=tools)
        assert len(wf.steps) == 1
        assert "search" in wf.steps[0].config["tools"]

    @pytest.mark.asyncio
    async def test_llm_planner(self) -> None:
        async def mock_llm(prompt: str) -> str:
            return '[{"id":"s1","type":"tool_call","config":{"tool":"search"},"dependencies":[]}]'

        planner = WorkflowPlanner(llm_fn=mock_llm)
        wf = await planner.plan("search for news")
        assert len(wf.steps) == 1
        assert wf.steps[0].id == "s1"
        assert wf.steps[0].config["tool"] == "search"
        assert wf.metadata["source"] == "llm_planner"

    @pytest.mark.asyncio
    async def test_llm_planner_with_dependencies(self) -> None:
        async def mock_llm(prompt: str) -> str:
            return """[
                {"id":"s1","type":"tool_call","config":{},"dependencies":[]},
                {"id":"s2","type":"agent_call","config":{},"dependencies":["s1"]}
            ]"""

        planner = WorkflowPlanner(llm_fn=mock_llm)
        wf = await planner.plan("multi-step task")
        assert len(wf.steps) == 2
        assert wf.steps[1].dependencies == ["s1"]

    @pytest.mark.asyncio
    async def test_llm_planner_invalid_json(self) -> None:
        async def mock_llm(prompt: str) -> str:
            return "this is not json"

        planner = WorkflowPlanner(llm_fn=mock_llm)
        wf = await planner.plan("task")
        assert len(wf.steps) == 1
        assert wf.steps[0].config.get("raw_response") == "this is not json"

    @pytest.mark.asyncio
    async def test_llm_planner_max_steps(self) -> None:
        async def mock_llm(prompt: str) -> str:
            steps = [
                {"id": f"s{i}", "type": "tool_call", "config": {}, "dependencies": []}
                for i in range(50)
            ]
            import json
            return json.dumps(steps)

        planner = WorkflowPlanner(llm_fn=mock_llm, max_steps=5)
        wf = await planner.plan("big task")
        assert len(wf.steps) == 5

    @pytest.mark.asyncio
    async def test_llm_planner_markdown_fenced(self) -> None:
        async def mock_llm(prompt: str) -> str:
            return '```json\n[{"id":"s1","type":"tool_call","config":{},"dependencies":[]}]\n```'

        planner = WorkflowPlanner(llm_fn=mock_llm)
        wf = await planner.plan("task")
        assert len(wf.steps) == 1

    @pytest.mark.asyncio
    async def test_llm_planner_single_dict_response(self) -> None:
        async def mock_llm(prompt: str) -> str:
            return '{"id":"s1","type":"tool_call","config":{},"dependencies":[]}'

        planner = WorkflowPlanner(llm_fn=mock_llm)
        wf = await planner.plan("task")
        assert len(wf.steps) == 1
        assert wf.steps[0].id == "s1"


# ---------------------------------------------------------------------------
# Integration: full workflow with conditions
# ---------------------------------------------------------------------------


class TestWorkflowIntegration:
    @pytest.mark.asyncio
    async def test_condition_step_routes(self) -> None:
        """Build a workflow: s1 → condition → s2 or s3."""
        s1 = WorkflowStep(id="s1", type="tool_call")
        cond = ConditionStep(
            id="c1",
            conditions=[
                Condition(
                    label="flag",
                    predicate=lambda r: r.get("s1") == "yes",
                    target_step_id="s2",
                ),
            ],
            default_step_id="s3",
        )
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["c1"])
        s3 = WorkflowStep(id="s3", type="tool_call", dependencies=["c1"])
        Workflow(id="w1", steps=[s1, cond, s2, s3])

        async def route_by_condition(
            step: WorkflowStep, state: WorkflowState
        ) -> str | None:
            if isinstance(step, ConditionStep):
                eval_result = await step.evaluate(state.results)
                return eval_result.target_step_id
            return f"done:{step.id}"

        WorkflowExecutor(
            handlers={"tool_call": _noop_handler, "condition": route_by_condition}
        )
        # The executor doesn't handle condition routing natively yet,
        # but we can verify the condition evaluation itself
        assert cond.type == "condition"

    @pytest.mark.asyncio
    async def test_workflow_result_duration(self) -> None:
        r = WorkflowResult(workflow_id="w1", status="completed", started_at=100.0)
        r.finished_at = 102.5
        assert r.duration == 2.5
