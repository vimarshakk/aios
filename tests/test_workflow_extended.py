"""Comprehensive tests for aios.workflows — events, serial, validator, enhanced executor."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from aios.workflows.approval import ApprovalRequest, ApprovalStep
from aios.workflows.base import StepStatus, Workflow, WorkflowResult, WorkflowStep
from aios.workflows.conditions import Condition, ConditionStep
from aios.workflows.events import (
    WorkflowEvent,
    WorkflowEventBus,
    WorkflowEventType,
)
from aios.workflows.executor import WorkflowExecutor
from aios.workflows.serial import (
    deserialize_result,
    deserialize_state,
    deserialize_step,
    deserialize_workflow,
    from_json_result,
    from_json_state,
    from_json_workflow,
    serialize_result,
    serialize_state,
    serialize_step,
    serialize_workflow,
    to_json,
)
from aios.workflows.state import WorkflowState, WorkflowStatus
from aios.workflows.validator import WorkflowValidator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _noop(step: WorkflowStep, _state: WorkflowState) -> str:
    return f"ok:{step.id}"


async def _echo(step: WorkflowStep, _state: WorkflowState) -> Any:
    return step.config


async def _fail(_step: WorkflowStep, _state: WorkflowState) -> str:
    raise RuntimeError("boom")


async def _slow(step: WorkflowStep, _state: WorkflowState) -> str:
    await asyncio.sleep(0.5)
    return f"slow:{step.id}"


async def _state_aware(step: WorkflowStep, state: WorkflowState) -> dict[str, Any]:
    return {"id": step.id, "prev_results": dict(state.results)}


# ===================================================================
# WorkflowEventBus
# ===================================================================


class TestWorkflowEventBus:
    def test_construction(self) -> None:
        bus = WorkflowEventBus()
        assert bus.history == []

    def test_emit_records_event(self) -> None:
        bus = WorkflowEventBus()
        event = WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_STARTED, workflow_id="w1"
        )
        bus.emit(event)
        assert len(bus.history) == 1
        assert bus.history[0] is event

    def test_handler_called(self) -> None:
        bus = WorkflowEventBus()
        received: list[WorkflowEvent] = []
        bus.on(WorkflowEventType.STEP_STARTED, received.append)
        event = WorkflowEvent(
            event_type=WorkflowEventType.STEP_STARTED,
            workflow_id="w1",
            step_id="s1",
        )
        bus.emit(event)
        assert len(received) == 1
        assert received[0].step_id == "s1"

    def test_handler_not_called_for_other_event(self) -> None:
        bus = WorkflowEventBus()
        received: list[WorkflowEvent] = []
        bus.on(WorkflowEventType.STEP_STARTED, received.append)
        bus.emit(WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_COMPLETED, workflow_id="w1"
        ))
        assert len(received) == 0

    def test_multiple_handlers(self) -> None:
        bus = WorkflowEventBus()
        calls_a: list[str] = []
        calls_b: list[str] = []
        bus.on(WorkflowEventType.STEP_STARTED, lambda e: calls_a.append("a"))
        bus.on(WorkflowEventType.STEP_STARTED, lambda e: calls_b.append("b"))
        bus.emit(WorkflowEvent(
            event_type=WorkflowEventType.STEP_STARTED, workflow_id="w1"
        ))
        assert calls_a == ["a"]
        assert calls_b == ["b"]

    def test_off_removes_handler(self) -> None:
        bus = WorkflowEventBus()

        def handler(_event: WorkflowEvent) -> None:
            pass

        bus.on(WorkflowEventType.STEP_STARTED, handler)
        assert bus.off(WorkflowEventType.STEP_STARTED, handler) is True
        bus.emit(WorkflowEvent(
            event_type=WorkflowEventType.STEP_STARTED, workflow_id="w1"
        ))
        assert len(bus.history) == 1  # Event recorded, handler not called

    def test_off_returns_false_for_missing(self) -> None:
        bus = WorkflowEventBus()

        def handler(_event: WorkflowEvent) -> None:
            pass

        assert bus.off(WorkflowEventType.STEP_STARTED, handler) is False

    def test_clear(self) -> None:
        bus = WorkflowEventBus()
        bus.on(WorkflowEventType.STEP_STARTED, lambda e: None)
        bus.emit(WorkflowEvent(
            event_type=WorkflowEventType.STEP_STARTED, workflow_id="w1"
        ))
        bus.clear()
        assert bus.history == []

    def test_events_for_workflow(self) -> None:
        bus = WorkflowEventBus()
        bus.emit(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_STARTED, workflow_id="w1"))
        bus.emit(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_STARTED, workflow_id="w2"))
        bus.emit(WorkflowEvent(event_type=WorkflowEventType.WORKFLOW_COMPLETED, workflow_id="w1"))
        w1_events = bus.events_for_workflow("w1")
        assert len(w1_events) == 2

    def test_sync_handler_exception_does_not_propagate(self) -> None:
        bus = WorkflowEventBus()

        def bad_handler(_event: WorkflowEvent) -> None:
            raise ValueError("handler error")

        bus.on(WorkflowEventType.STEP_STARTED, bad_handler)
        # Should not raise
        bus.emit(WorkflowEvent(
            event_type=WorkflowEventType.STEP_STARTED, workflow_id="w1"
        ))

    @pytest.mark.asyncio
    async def test_sync_handler_with_future(self) -> None:
        bus = WorkflowEventBus()
        call_count = 0

        def async_like(event: WorkflowEvent) -> asyncio.Future[None]:
            nonlocal call_count
            call_count += 1
            fut: asyncio.Future[None] = asyncio.get_event_loop().create_future()
            fut.set_result(None)
            return fut

        bus.on(WorkflowEventType.STEP_STARTED, async_like)
        bus.emit(WorkflowEvent(
            event_type=WorkflowEventType.STEP_STARTED, workflow_id="w1"
        ))
        # Sync call happens immediately; async task may schedule too
        assert call_count >= 1

    def test_event_frozen(self) -> None:
        event = WorkflowEvent(
            event_type=WorkflowEventType.WORKFLOW_STARTED, workflow_id="w1"
        )
        with pytest.raises(AttributeError):
            event.workflow_id = "w2"  # type: ignore[misc]

    def test_event_data(self) -> None:
        event = WorkflowEvent(
            event_type=WorkflowEventType.STEP_FAILED,
            workflow_id="w1",
            step_id="s1",
            data={"error": "timeout"},
        )
        assert event.data["error"] == "timeout"


# ===================================================================
# Serialization
# ===================================================================


class TestSerializeStep:
    def test_basic_step(self) -> None:
        step = WorkflowStep(id="s1", type="tool_call", config={"x": 1})
        data = serialize_step(step)
        assert data["id"] == "s1"
        assert data["type"] == "tool_call"
        assert data["config"] == {"x": 1}
        assert data["kind"] == "step"

    def test_condition_step(self) -> None:
        cond = Condition(label="flag", target_step_id="s2")
        step = ConditionStep(
            id="c1", conditions=[cond], default_step_id="s3"
        )
        data = serialize_step(step)
        assert data["kind"] == "condition"
        assert len(data["conditions"]) == 1
        assert data["conditions"][0]["label"] == "flag"
        assert data["default_step_id"] == "s3"

    def test_approval_step(self) -> None:
        step = ApprovalStep(id="a1", prompt="Approve?", timeout_seconds=60.0)
        data = serialize_step(step)
        assert data["kind"] == "approval"
        assert data["prompt"] == "Approve?"
        assert data["timeout_seconds"] == 60.0

    def test_round_trip_basic(self) -> None:
        step = WorkflowStep(id="s1", type="tool_call", config={"k": "v"}, dependencies=["s0"])
        data = serialize_step(step)
        restored = deserialize_step(data)
        assert restored.id == "s1"
        assert restored.type == "tool_call"
        assert restored.config == {"k": "v"}
        assert restored.dependencies == ["s0"]

    def test_round_trip_condition(self) -> None:
        cond = Condition(label="x", target_step_id="s2")
        step = ConditionStep(id="c1", conditions=[cond], default_step_id="s3")
        data = serialize_step(step)
        restored = deserialize_step(data)
        assert isinstance(restored, ConditionStep)
        assert restored.id == "c1"
        assert len(restored.conditions) == 1
        assert restored.conditions[0].label == "x"
        assert restored.default_step_id == "s3"

    def test_round_trip_approval(self) -> None:
        step = ApprovalStep(id="a1", prompt="Ok?", timeout_seconds=120.0, require_response=True)
        data = serialize_step(step)
        restored = deserialize_step(data)
        assert isinstance(restored, ApprovalStep)
        assert restored.prompt == "Ok?"
        assert restored.timeout_seconds == 120.0
        assert restored.require_response is True


class TestSerializeWorkflow:
    def test_round_trip(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="agent_call", dependencies=["s1"])
        wf = Workflow(id="w1", name="test", steps=[s1, s2], metadata={"version": 1})
        data = serialize_workflow(wf)
        restored = deserialize_workflow(data)
        assert restored.id == "w1"
        assert restored.name == "test"
        assert len(restored.steps) == 2
        assert restored.steps[1].dependencies == ["s1"]
        assert restored.metadata["version"] == 1

    def test_json_round_trip(self) -> None:
        wf = Workflow(id="w1", name="test", steps=[WorkflowStep(id="s1")])
        json_str = to_json(wf)
        restored = from_json_workflow(json_str)
        assert restored.id == "w1"
        assert len(restored.steps) == 1


class TestSerializeResult:
    def test_round_trip(self) -> None:
        r = WorkflowResult(
            workflow_id="w1",
            status="completed",
            step_results={"s1": "done", "s2": StepStatus.RUNNING},
            error=None,
            started_at=100.0,
            finished_at=105.0,
        )
        data = serialize_result(r)
        restored = deserialize_result(data)
        assert restored.workflow_id == "w1"
        assert restored.status == "completed"
        assert restored.step_results["s1"] == "done"
        assert restored.step_results["s2"] == StepStatus.RUNNING
        assert restored.duration == 5.0

    def test_exception_in_results(self) -> None:
        r = WorkflowResult(
            workflow_id="w1",
            status="failed",
            step_results={"s1": RuntimeError("boom")},
        )
        data = serialize_result(r)
        restored = deserialize_result(data)
        assert isinstance(restored.step_results["s1"], RuntimeError)
        assert str(restored.step_results["s1"]) == "boom"

    def test_json_round_trip(self) -> None:
        r = WorkflowResult(workflow_id="w1", status="completed", started_at=1.0, finished_at=2.0)
        json_str = to_json(r)
        restored = from_json_result(json_str)
        assert restored.workflow_id == "w1"
        assert restored.duration == 1.0


class TestSerializeState:
    def test_round_trip(self) -> None:
        s = WorkflowState(
            status=WorkflowStatus.RUNNING,
            current_step="s1",
            results={"s0": "done"},
            step_status={"s0": "completed", "s1": "running"},
            error=None,
            metadata={"key": "val"},
        )
        data = serialize_state(s)
        restored = deserialize_state(data)
        assert restored.status == WorkflowStatus.RUNNING
        assert restored.current_step == "s1"
        assert restored.results == {"s0": "done"}
        assert restored.step_status == {"s0": "completed", "s1": "running"}

    def test_json_round_trip(self) -> None:
        s = WorkflowState(status=WorkflowStatus.FAILED, error="oops")
        json_str = to_json(s)
        restored = from_json_state(json_str)
        assert restored.status == WorkflowStatus.FAILED
        assert restored.error == "oops"

    def test_to_json_rejects_unknown_type(self) -> None:
        with pytest.raises(TypeError, match="Cannot serialize"):
            to_json("not a workflow object")


# ===================================================================
# WorkflowValidator
# ===================================================================


class TestWorkflowValidator:
    def test_valid_workflow(self) -> None:
        wf = Workflow(
            id="w1",
            name="test",
            steps=[
                WorkflowStep(id="s1", type="tool_call"),
                WorkflowStep(id="s2", type="tool_call", dependencies=["s1"]),
            ],
        )
        v = WorkflowValidator()
        result = v.validate(wf)
        assert result.is_valid
        assert result.error_count == 0

    def test_empty_id(self) -> None:
        wf = Workflow(id="", name="test", steps=[WorkflowStep(id="s1")])
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid

    def test_empty_name(self) -> None:
        wf = Workflow(id="w1", name="", steps=[WorkflowStep(id="s1")])
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid

    def test_empty_steps(self) -> None:
        wf = Workflow(id="w1", name="test", steps=[])
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid

    def test_duplicate_step_ids(self) -> None:
        wf = Workflow(
            id="w1",
            name="test",
            steps=[
                WorkflowStep(id="s1"),
                WorkflowStep(id="s1"),
            ],
        )
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid
        assert any("Duplicate" in e.message for e in result.errors)

    def test_missing_dependency(self) -> None:
        wf = Workflow(
            id="w1",
            name="test",
            steps=[WorkflowStep(id="s1", dependencies=["nonexistent"])],
        )
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid
        assert any("non-existent" in e.message for e in result.errors)

    def test_circular_dependency(self) -> None:
        wf = Workflow(
            id="w1",
            name="test",
            steps=[
                WorkflowStep(id="s1", dependencies=["s2"]),
                WorkflowStep(id="s2", dependencies=["s1"]),
            ],
        )
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid
        assert any("Circular" in e.message for e in result.errors)

    def test_unknown_step_type_warning(self) -> None:
        wf = Workflow(
            id="w1",
            name="test",
            steps=[WorkflowStep(id="s1", type="custom_type")],
        )
        result = WorkflowValidator().validate(wf)
        assert result.is_valid  # Warnings don't make it invalid
        assert result.warning_count == 1

    def test_empty_step_type(self) -> None:
        wf = Workflow(
            id="w1",
            name="test",
            steps=[WorkflowStep(id="s1", type="")],
        )
        result = WorkflowValidator().validate(wf)
        assert not result.is_valid

    def test_long_chain_no_cycle(self) -> None:
        steps = [
            WorkflowStep(id=f"s{i}", dependencies=[f"s{i-1}"] if i > 0 else [])
            for i in range(20)
        ]
        wf = Workflow(id="w1", name="chain", steps=steps)
        result = WorkflowValidator().validate(wf)
        assert result.is_valid


# ===================================================================
# Enhanced Executor — native condition routing
# ===================================================================


class TestExecutorConditions:
    @pytest.mark.asyncio
    async def test_condition_routes_to_branch(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        cond = ConditionStep(
            id="c1",
            conditions=[
                Condition(
                    label="yes",
                    predicate=lambda r: r.get("s1") == "ok",
                    target_step_id="s2",
                ),
            ],
            default_step_id="s3",
        )
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["c1"])
        s3 = WorkflowStep(id="s3", type="tool_call", dependencies=["c1"])
        wf = Workflow(id="w1", steps=[s1, cond, s2, s3])

        async def handler(step: WorkflowStep, _state: WorkflowState) -> str:
            if step.id == "s1":
                return "ok"
            return f"done:{step.id}"

        executor = WorkflowExecutor(handlers={"tool_call": handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        # s2 should have run because condition matched
        assert result.step_results["s2"] == "done:s2"

    @pytest.mark.asyncio
    async def test_condition_routes_to_default(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        cond = ConditionStep(
            id="c1",
            conditions=[
                Condition(
                    label="yes",
                    predicate=lambda r: r.get("s1") == "nope",
                    target_step_id="s2",
                ),
            ],
            default_step_id="s3",
        )
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["c1"])
        s3 = WorkflowStep(id="s3", type="tool_call", dependencies=["c1"])
        wf = Workflow(id="w1", steps=[s1, cond, s2, s3])

        async def handler(step: WorkflowStep, _state: WorkflowState) -> str:
            if step.id == "s1":
                return "not_nope"
            return f"done:{step.id}"

        executor = WorkflowExecutor(handlers={"tool_call": handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["s3"] == "done:s3"


# ===================================================================
# Enhanced Executor — approval handling
# ===================================================================


class TestExecutorApproval:
    @pytest.mark.asyncio
    async def test_approval_auto_approved(self) -> None:
        """Without on_approval callback, approval is auto-approved."""
        s1 = WorkflowStep(id="s1", type="tool_call")
        a1 = ApprovalStep(id="a1", prompt="Deploy?")
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["a1"])
        wf = Workflow(id="w1", steps=[s1, a1, s2])
        executor = WorkflowExecutor(handlers={"tool_call": _noop})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["a1"] is True

    @pytest.mark.asyncio
    async def test_approval_with_callback_approved(self) -> None:
        async def approve(req: ApprovalRequest) -> None:
            req.approve(approver="admin")

        s1 = ApprovalStep(id="a1", prompt="Deploy?")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"tool_call": _noop},
            on_approval=approve,
        )
        result = await executor.run(wf)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_approval_rejected_fails(self) -> None:
        async def reject(req: ApprovalRequest) -> None:
            req.reject(approver="admin", response="No way")

        s1 = ApprovalStep(id="a1", prompt="Deploy?")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"tool_call": _noop},
            on_approval=reject,
        )
        result = await executor.run(wf)
        assert result.status == "failed"
        assert "rejected" in (result.error or "").lower()


# ===================================================================
# Enhanced Executor — workflow timeout
# ===================================================================


class TestExecutorTimeout:
    @pytest.mark.asyncio
    async def test_timeout_fires(self) -> None:
        s1 = WorkflowStep(id="s1", type="slow")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"slow": _slow},
            timeout_seconds=0.1,
        )
        result = await executor.run(wf)
        assert result.status == "failed"
        assert "timed out" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_fast_workflow_within_timeout(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"tool_call": _noop},
            timeout_seconds=10.0,
        )
        result = await executor.run(wf)
        assert result.status == "completed"


# ===================================================================
# Enhanced Executor — event bus integration
# ===================================================================


class TestExecutorEvents:
    @pytest.mark.asyncio
    async def test_events_emitted(self) -> None:
        bus = WorkflowEventBus()
        s1 = WorkflowStep(id="s1", type="tool_call")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"tool_call": _noop},
            event_bus=bus,
        )
        await executor.run(wf)
        types = [e.event_type for e in bus.history]
        assert WorkflowEventType.WORKFLOW_STARTED in types
        assert WorkflowEventType.WORKFLOW_COMPLETED in types
        assert WorkflowEventType.STEP_STARTED in types
        assert WorkflowEventType.STEP_COMPLETED in types

    @pytest.mark.asyncio
    async def test_failure_events_emitted(self) -> None:
        bus = WorkflowEventBus()
        s1 = WorkflowStep(id="s1", type="fail")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"fail": _fail},
            event_bus=bus,
        )
        await executor.run(wf)
        types = [e.event_type for e in bus.history]
        assert WorkflowEventType.WORKFLOW_FAILED in types
        assert WorkflowEventType.STEP_FAILED in types

    @pytest.mark.asyncio
    async def test_timeout_emits_events(self) -> None:
        bus = WorkflowEventBus()
        s1 = WorkflowStep(id="s1", type="slow")
        wf = Workflow(id="w1", steps=[s1])
        executor = WorkflowExecutor(
            handlers={"slow": _slow},
            timeout_seconds=0.1,
            event_bus=bus,
        )
        await executor.run(wf)
        types = [e.event_type for e in bus.history]
        assert WorkflowEventType.WORKFLOW_FAILED in types


# ===================================================================
# Enhanced Executor — retry support
# ===================================================================


class TestExecutorRetry:
    @pytest.mark.asyncio
    async def test_step_retry_eventual_success(self) -> None:
        attempts = 0

        async def flaky(step: WorkflowStep, state: WorkflowState) -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("not yet")
            return "done"

        step = WorkflowStep(
            id="s1",
            type="tool_call",
            config={"retry": {"max_retries": 3, "base_delay": 0.01, "backoff_factor": 1.0}},
        )
        wf = Workflow(id="w1", steps=[step])
        executor = WorkflowExecutor(handlers={"tool_call": flaky})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert attempts == 3

    @pytest.mark.asyncio
    async def test_step_retry_exhaustion(self) -> None:
        step = WorkflowStep(
            id="s1",
            type="tool_call",
            config={"retry": {"max_retries": 1, "base_delay": 0.01}},
        )
        wf = Workflow(id="w1", steps=[step])
        executor = WorkflowExecutor(handlers={"tool_call": _fail})
        result = await executor.run(wf)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_step_retry_emits_event(self) -> None:
        bus = WorkflowEventBus()
        attempts = 0

        async def flaky(step: WorkflowStep, state: WorkflowState) -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RuntimeError("fail")
            return "ok"

        step = WorkflowStep(
            id="s1",
            type="tool_call",
            config={"retry": {"max_retries": 3, "base_delay": 0.01}},
        )
        wf = Workflow(id="w1", steps=[step])
        executor = WorkflowExecutor(handlers={"tool_call": flaky}, event_bus=bus)
        await executor.run(wf)
        retry_events = [e for e in bus.history if e.event_type == WorkflowEventType.STEP_RETRYING]
        assert len(retry_events) == 1


# ===================================================================
# Enhanced Executor — edge cases
# ===================================================================


class TestExecutorEdgeCases:
    @pytest.mark.asyncio
    async def test_resume_after_failure(self) -> None:
        fail_once = {"called": False}

        async def handler(step: WorkflowStep, _state: WorkflowState) -> str:
            if step.id == "s2" and not fail_once["called"]:
                fail_once["called"] = True
                raise RuntimeError("first time fail")
            return f"ok:{step.id}"

        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["s1"])
        wf = Workflow(id="w1", steps=[s1, s2])
        executor = WorkflowExecutor(handlers={"tool_call": handler})
        result = await executor.run(wf)
        assert result.status == "failed"

        result2 = await executor.resume(wf, result)
        assert result2.status == "completed"

    @pytest.mark.asyncio
    async def test_empty_workflow(self) -> None:
        wf = Workflow(id="w1", steps=[])
        executor = WorkflowExecutor()
        result = await executor.run(wf)
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_step_with_no_handler_fails(self) -> None:
        step = WorkflowStep(id="s1", type="nonexistent")
        wf = Workflow(id="w1", steps=[step])
        executor = WorkflowExecutor()
        result = await executor.run(wf)
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_step_result_accessors(self) -> None:
        r = WorkflowResult(workflow_id="w1", status="completed", started_at=10.0)
        assert r.duration is None
        r.finished_at = 12.5
        assert r.duration == 2.5


# ===================================================================
# Integration: full workflow with condition routing
# ===================================================================


class TestFullWorkflow:
    @pytest.mark.asyncio
    async def test_condition_based_branching_full(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        cond = ConditionStep(
            id="c1",
            conditions=[
                Condition(
                    label="high",
                    predicate=lambda r: r.get("s1") == "high",
                    target_step_id="s_high",
                ),
                Condition(
                    label="low",
                    predicate=lambda r: r.get("s1") == "low",
                    target_step_id="s_low",
                ),
            ],
            default_step_id="s_mid",
        )
        s_high = WorkflowStep(id="s_high", type="tool_call", dependencies=["c1"])
        s_low = WorkflowStep(id="s_low", type="tool_call", dependencies=["c1"])
        s_mid = WorkflowStep(id="s_mid", type="tool_call", dependencies=["c1"])
        wf = Workflow(id="w1", steps=[s1, cond, s_high, s_low, s_mid])

        async def handler(step: WorkflowStep, _state: WorkflowState) -> str:
            if step.id == "s1":
                return "low"
            return f"done:{step.id}"

        executor = WorkflowExecutor(handlers={"tool_call": handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["s_low"] == "done:s_low"

    @pytest.mark.asyncio
    async def test_approval_then_continue(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        a1 = ApprovalStep(id="a1", prompt="Proceed?")
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["a1"])
        wf = Workflow(id="w1", steps=[s1, a1, s2])
        executor = WorkflowExecutor(handlers={"tool_call": _noop})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["s1"] == "ok:s1"
        assert result.step_results["s2"] == "ok:s2"

    @pytest.mark.asyncio
    async def test_diamond_with_condition(self) -> None:
        s1 = WorkflowStep(id="s1", type="tool_call")
        s2 = WorkflowStep(id="s2", type="tool_call", dependencies=["s1"])
        s3 = WorkflowStep(id="s3", type="tool_call", dependencies=["s1"])
        cond = ConditionStep(
            id="c1",
            conditions=[
                Condition(
                    label="r",
                    predicate=lambda r: r.get("s2") == "a",
                    target_step_id="s4",
                ),
            ],
            default_step_id="s5",
        )
        s4 = WorkflowStep(id="s4", type="tool_call", dependencies=["s2", "s3", "c1"])
        s5 = WorkflowStep(id="s5", type="tool_call", dependencies=["s2", "s3", "c1"])
        wf = Workflow(id="w1", steps=[s1, s2, s3, cond, s4, s5])

        async def handler(step: WorkflowStep, _state: WorkflowState) -> str:
            if step.id == "s2":
                return "a"
            return f"ok:{step.id}"

        executor = WorkflowExecutor(handlers={"tool_call": handler})
        result = await executor.run(wf)
        assert result.status == "completed"
        assert result.step_results["s4"] == "ok:s4"
