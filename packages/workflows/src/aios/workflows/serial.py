"""Workflow serialization — JSON-based persistence for workflows and results."""

from __future__ import annotations

import json
from typing import Any

from aios.workflows.approval import ApprovalStep
from aios.workflows.base import StepStatus, Workflow, WorkflowResult, WorkflowStep
from aios.workflows.conditions import Condition, ConditionStep
from aios.workflows.state import WorkflowState, WorkflowStatus


def serialize_step(step: WorkflowStep) -> dict[str, Any]:
    """Serialize a WorkflowStep to a JSON-safe dict.

    ConditionStep and ApprovalStep are serialized with their extra fields.
    """
    data: dict[str, Any] = {
        "id": step.id,
        "type": step.type,
        "config": _make_json_safe(step.config),
        "dependencies": list(step.dependencies),
    }
    if isinstance(step, ConditionStep):
        data["kind"] = "condition"
        data["conditions"] = [
            {"label": c.label, "target_step_id": c.target_step_id}
            for c in step.conditions
        ]
        data["default_step_id"] = step.default_step_id
    elif isinstance(step, ApprovalStep):
        data["kind"] = "approval"
        data["prompt"] = step.prompt
        data["timeout_seconds"] = step.timeout_seconds
        data["require_response"] = step.require_response
    else:
        data["kind"] = "step"
    return data


def deserialize_step(data: dict[str, Any]) -> WorkflowStep:
    """Deserialize a dict into the appropriate WorkflowStep subclass."""
    kind = data.get("kind", "step")
    if kind == "condition":
        conditions = [
            Condition(
                label=c["label"],
                target_step_id=c.get("target_step_id"),
            )
            for c in data.get("conditions", [])
        ]
        return ConditionStep(
            id=data["id"],
            conditions=conditions,
            default_step_id=data.get("default_step_id"),
            config=data.get("config", {}),
            dependencies=data.get("dependencies", []),
        )
    if kind == "approval":
        return ApprovalStep(
            id=data["id"],
            prompt=data.get("prompt", ""),
            timeout_seconds=data.get("timeout_seconds", 300.0),
            require_response=data.get("require_response", False),
            config=data.get("config", {}),
            dependencies=data.get("dependencies", []),
        )
    return WorkflowStep(
        id=data["id"],
        type=data.get("type", "tool_call"),
        config=data.get("config", {}),
        dependencies=data.get("dependencies", []),
    )


def serialize_workflow(workflow: Workflow) -> dict[str, Any]:
    """Serialize a full Workflow to JSON-safe dict."""
    return {
        "id": workflow.id,
        "name": workflow.name,
        "steps": [serialize_step(s) for s in workflow.steps],
        "metadata": _make_json_safe(workflow.metadata),
    }


def deserialize_workflow(data: dict[str, Any]) -> Workflow:
    """Deserialize a dict into a Workflow object."""
    return Workflow(
        id=data["id"],
        name=data.get("name", "unnamed"),
        steps=[deserialize_step(s) for s in data.get("steps", [])],
        metadata=data.get("metadata", {}),
    )


def serialize_result(result: WorkflowResult) -> dict[str, Any]:
    """Serialize a WorkflowResult to JSON-safe dict."""
    return {
        "workflow_id": result.workflow_id,
        "status": result.status,
        "step_results": {
            k: _serialize_step_result_value(v)
            for k, v in result.step_results.items()
        },
        "error": result.error,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


def _serialize_step_result_value(value: Any) -> Any:
    """Serialize a single step result value."""
    if isinstance(value, StepStatus):
        return {"_type": "StepStatus", "value": str(value)}
    if isinstance(value, Exception):
        return {"_type": "Exception", "value": str(value)}
    return value


def deserialize_result(data: dict[str, Any]) -> WorkflowResult:
    """Deserialize a dict into a WorkflowResult."""
    step_results: dict[str, Any] = {}
    for k, v in data.get("step_results", {}).items():
        if isinstance(v, dict) and "_type" in v:
            if v["_type"] == "StepStatus":
                step_results[k] = StepStatus(v["value"])
            elif v["_type"] == "Exception":
                step_results[k] = RuntimeError(v["value"])
            else:
                step_results[k] = v
        else:
            step_results[k] = v
    return WorkflowResult(
        workflow_id=data["workflow_id"],
        status=data["status"],
        step_results=step_results,
        error=data.get("error"),
        started_at=data.get("started_at", 0.0),
        finished_at=data.get("finished_at"),
    )


def serialize_state(state: WorkflowState) -> dict[str, Any]:
    """Serialize a WorkflowState to JSON-safe dict."""
    return {
        "status": str(state.status),
        "current_step": state.current_step,
        "results": _make_json_safe(state.results),
        "step_status": dict(state.step_status),
        "error": state.error,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "metadata": _make_json_safe(state.metadata),
    }


def deserialize_state(data: dict[str, Any]) -> WorkflowState:
    """Deserialize a dict into a WorkflowState."""
    return WorkflowState(
        status=WorkflowStatus(data["status"]),
        current_step=data.get("current_step"),
        results=data.get("results", {}),
        step_status=data.get("step_status", {}),
        error=data.get("error"),
        created_at=data.get("created_at", 0.0),
        updated_at=data.get("updated_at", 0.0),
        metadata=data.get("metadata", {}),
    )


def to_json(obj: Any) -> str:
    """Serialize any workflow object to a JSON string."""
    if isinstance(obj, Workflow):
        return json.dumps(serialize_workflow(obj), indent=2)
    if isinstance(obj, WorkflowResult):
        return json.dumps(serialize_result(obj), indent=2)
    if isinstance(obj, WorkflowState):
        return json.dumps(serialize_state(obj), indent=2)
    if isinstance(obj, WorkflowStep):
        return json.dumps(serialize_step(obj), indent=2)
    raise TypeError(f"Cannot serialize {type(obj).__name__}")


def from_json_workflow(json_str: str) -> Workflow:
    """Deserialize a JSON string into a Workflow."""
    return deserialize_workflow(json.loads(json_str))


def from_json_result(json_str: str) -> WorkflowResult:
    """Deserialize a JSON string into a WorkflowResult."""
    return deserialize_result(json.loads(json_str))


def from_json_state(json_str: str) -> WorkflowState:
    """Deserialize a JSON string into a WorkflowState."""
    return deserialize_state(json.loads(json_str))


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert non-serializable values to strings."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(i) for i in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)
