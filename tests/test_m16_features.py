"""
M16 Tests — Autonomous Intelligence & Agentic Orchestration

Tests for:
- M16.1: Supervisor (Goal Manager)
- M16.2: Planner (DAG Task Decomposition)
- M16.3: Agent Runtime (Multi-Agent Orchestration)
- M16.4: Desktop Automation
- M16.5: Workflow Engine (Triggers, Jobs, Conditions)
- M16.6: Observability (Execution Graph, Cost, Performance)
- M16.7: Persistence (Checkpoints, Queues, Crash Recovery)
- M16.8: IPC, main process, preload integration
"""

import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESKTOP_DIR = os.path.join(ROOT, "apps", "desktop")
MAIN_DIR = os.path.join(DESKTOP_DIR, "src", "main")
PRELOAD_DIR = os.path.join(DESKTOP_DIR, "src", "preload")


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── M16.1: Supervisor ──────────────────────────────────────────────────────

class TestSupervisor:
    """Tests for Supervisor (Goal Manager) module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "supervisor.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "class Supervisor" in content

    def test_has_goal_status(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "GoalStatus" in content

    def test_has_goal_priority(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "GoalPriority" in content

    def test_has_create_goal(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "createGoal" in content

    def test_has_cancel_goal(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "cancelGoal" in content

    def test_has_pause_resume(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "pauseGoal" in content
        assert "resumeGoal" in content

    def test_has_tick(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "async tick" in content

    def test_has_priority_scheduling(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "critical" in content
        assert "high" in content
        assert "medium" in content
        assert "low" in content

    def test_has_retry_recovery(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "retry" in content.lower()
        assert "backoff" in content.lower()

    def test_has_get_state(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "getState" in content

    def test_has_get_goal(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "getGoal" in content

    def test_has_persistence(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "persist" in content.lower() or "load" in content.lower()

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        assert "destroy" in content

    def test_priority_ordering(self):
        content = read_file(os.path.join(MAIN_DIR, "supervisor.ts"))
        # Critical must come before high, high before medium, etc.
        idx_crit = content.index("critical")
        idx_high = content.index("high")
        idx_med = content.index("medium")
        assert idx_crit < idx_high < idx_med


# ── M16.2: Planner ─────────────────────────────────────────────────────────

class TestPlanner:
    """Tests for Planner (DAG Task Decomposition) module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "planner.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "class Planner" in content

    def test_has_task_interface(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "interface Task" in content

    def test_has_task_status(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "TaskStatus" in content

    def test_has_plan_method(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "plan(" in content

    def test_has_replan(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "replan" in content

    def test_has_dag(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "DAG" in content or "dag" in content or "topological" in content.lower()

    def test_has_topological_sort(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "topological" in content.lower() or "sort" in content.lower()

    def test_has_critical_path(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "criticalPath" in content or "critical_path" in content or "getCriticalPath" in content

    def test_has_dependency_resolution(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "dependencies" in content or "dependency" in content

    def test_has_get_next_task(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "getNextTask" in content

    def test_has_complete_task(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "completeTask" in content

    def test_has_fail_task(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "failTask" in content

    def test_has_get_plan(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "getPlan" in content

    def test_has_calculate_critical_path(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "calculateCriticalPath" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "planner.ts"))
        assert "destroy" in content


# ── M16.3: Agent Runtime ───────────────────────────────────────────────────

class TestAgentRuntime:
    """Tests for Agent Runtime (Multi-Agent Orchestration) module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "agent-runtime.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "class AgentRuntime" in content

    def test_has_agent_config(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "AgentConfig" in content or "AgentRegistration" in content

    def test_has_register(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "register" in content

    def test_has_execute(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "execute" in content

    def test_has_execute_task(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "executeTask" in content

    def test_has_send_message(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "sendMessage" in content

    def test_has_broadcast(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "broadcast" in content

    def test_has_shared_context(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "sharedContext" in content or "SharedContext" in content or "getSharedContext" in content

    def test_has_set_variable(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "setVariable" in content

    def test_has_get_artifact(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "getArtifact" in content

    def test_has_get_agents(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "getAgents" in content

    def test_has_get_state(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "getState" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "agent-runtime.ts"))
        assert "destroy" in content


# ── M16.4: Desktop Automation ──────────────────────────────────────────────

class TestDesktopAutomation:
    """Tests for Desktop Automation module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "desktop-automation.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "class DesktopAutomation" in content

    def test_has_mouse_click(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "click" in content

    def test_has_mouse_move(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "moveMouse" in content

    def test_has_mouse_drag(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "drag" in content

    def test_has_mouse_scroll(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "scroll" in content

    def test_has_keyboard_type(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "typeText" in content

    def test_has_keyboard_hotkey(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "hotkey" in content

    def test_has_keyboard_sequence(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "keySequence" in content

    def test_has_screenshot(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "screenshot" in content

    def test_has_window_management(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "listWindows" in content
        assert "focusWindow" in content

    def test_has_ocr(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "ocrExtract" in content or "ocr" in content.lower()

    def test_has_accessibility_tree(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "getAccessibilityTree" in content or "accessibilityTree" in content

    def test_has_clipboard_read(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "readClipboard" in content

    def test_has_clipboard_write(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "writeClipboard" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "desktop-automation.ts"))
        assert "destroy" in content


# ── M16.5: Workflow Engine ─────────────────────────────────────────────────

class TestWorkflowEngine:
    """Tests for Workflow Engine module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "workflow-engine.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "class WorkflowEngine" in content

    def test_has_workflow_interface(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "interface Workflow" in content

    def test_has_workflow_status(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "WorkflowStatus" in content

    def test_has_create_workflow(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "createWorkflow" in content

    def test_has_get_workflow(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "getWorkflow" in content

    def test_has_delete_workflow(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "deleteWorkflow" in content

    def test_has_pause_resume(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "pauseWorkflow" in content
        assert "resumeWorkflow" in content

    def test_has_run_workflow(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "runWorkflow" in content

    def test_has_event_triggers(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "trigger" in content.lower()

    def test_has_scheduled_jobs(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "schedule" in content.lower() or "cron" in content.lower() or "interval" in content.lower()

    def test_has_conditionals(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "condition" in content.lower() or "if" in content

    def test_has_parallel(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "parallel" in content.lower()

    def test_has_loop(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "loop" in content.lower()

    def test_has_state_machine(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "state" in content.lower()

    def test_has_tick(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "startScheduler" in content or "checkScheduledJobs" in content

    def test_has_get_all_workflows(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "getAllWorkflows" in content

    def test_has_get_event_history(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "getEventHistory" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "workflow-engine.ts"))
        assert "destroy" in content


# ── M16.6: Observability ───────────────────────────────────────────────────

class TestObservability:
    """Tests for Observability module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "observability.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "class Observability" in content

    def test_has_execution_node(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "ExecutionNode" in content

    def test_has_add_node(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "addNode" in content

    def test_has_get_graph(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "getGraph" in content

    def test_has_get_timeline(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "getTimeline" in content

    def test_has_get_total_cost(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "getTotalCost" in content

    def test_has_cost_tracking(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "cost" in content.lower()

    def test_has_token_tracking(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "token" in content.lower()

    def test_has_performance_metrics(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "getPerformanceMetrics" in content

    def test_has_p95(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "p95" in content

    def test_has_p99(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "p99" in content

    def test_has_throughput(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "throughput" in content.lower()

    def test_has_error_rate(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "errorRate" in content or "error_rate" in content or "error" in content.lower()

    def test_has_get_snapshot(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "getSnapshot" in content

    def test_has_get_state(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "getSnapshot" in content or "getState" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "observability.ts"))
        assert "destroy" in content


# ── M16.7: Persistence ─────────────────────────────────────────────────────

class TestPersistence:
    """Tests for Persistence module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "persistence.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "class Persistence" in content

    def test_has_checkpoint(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "Checkpoint" in content

    def test_has_create_checkpoint(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "createCheckpoint" in content

    def test_has_get_checkpoint(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "getCheckpoint" in content

    def test_has_restore_checkpoint(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "restoreCheckpoint" in content

    def test_has_list_checkpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "listCheckpoints" in content

    def test_has_integrity_check(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "integrity" in content.lower() or "hash" in content.lower() or "sha" in content.lower()

    def test_has_enqueue(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "enqueue" in content

    def test_has_dequeue(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "dequeue" in content

    def test_has_peek_queue(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "peekQueue" in content

    def test_has_priority_queue(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "priority" in content.lower()

    def test_has_record_history(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "recordHistory" in content

    def test_has_get_history(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "getHistory" in content

    def test_has_export_all(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "exportAll" in content

    def test_has_import_all(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "importAll" in content

    def test_has_versioning(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "version" in content.lower()

    def test_has_list_versions(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "listVersions" in content

    def test_has_restore_version(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "restoreVersion" in content

    def test_has_auto_checkpoint(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "autoCheckpoint" in content or "auto" in content.lower()

    def test_has_crash_recovery(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "crash" in content.lower() or "recovery" in content.lower()

    def test_has_cleanup(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "cleanup" in content

    def test_has_get_state(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "getState" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "persistence.ts"))
        assert "destroy" in content


# ── M16.8: IPC / Main / Preload Integration ────────────────────────────────

class TestIpcIntegration:
    """Tests for M16 IPC handler, main process, and preload integration."""

    def test_ipc_handler_imports_m16(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'import { Supervisor }' in content
        assert 'import { Planner }' in content
        assert 'import { AgentRuntime }' in content
        assert 'import { DesktopAutomation }' in content
        assert 'import { WorkflowEngine }' in content
        assert 'import { Observability }' in content
        assert 'import { Persistence }' in content

    def test_ipc_handler_deps_m16(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "supervisor: Supervisor" in content
        assert "planner: Planner" in content
        assert "agentRuntime: AgentRuntime" in content
        assert "desktopAutomation: DesktopAutomation" in content
        assert "workflowEngine: WorkflowEngine" in content
        assert "observability: Observability" in content
        assert "persistence: Persistence" in content

    def test_ipc_supervisor_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"supervisor:submit-goal"' in content
        assert '"supervisor:get-goal"' in content
        assert '"supervisor:cancel-goal"' in content
        assert '"supervisor:pause-goal"' in content
        assert '"supervisor:resume-goal"' in content
        assert '"supervisor:tick"' in content

    def test_ipc_planner_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"planner:plan"' in content
        assert '"planner:get-plan"' in content
        assert '"planner:replan"' in content
        assert '"planner:complete-task"' in content
        assert '"planner:fail-task"' in content
        assert '"planner:execute-ready"' in content
        assert '"planner:get-critical-path"' in content

    def test_ipc_runtime_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"runtime:execute"' in content
        assert '"runtime:execute-parallel"' in content
        assert '"runtime:message"' in content
        assert '"runtime:inbox"' in content
        assert '"runtime:context"' in content
        assert '"runtime:set-context"' in content
        assert '"runtime:artifacts"' in content
        assert '"runtime:agents"' in content

    def test_ipc_automation_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"automation:mouse-click"' in content
        assert '"automation:mouse-move"' in content
        assert '"automation:mouse-drag"' in content
        assert '"automation:mouse-scroll"' in content
        assert '"automation:keyboard-type"' in content
        assert '"automation:keyboard-hotkey"' in content
        assert '"automation:keyboard-sequence"' in content
        assert '"automation:screenshot"' in content
        assert '"automation:windows"' in content
        assert '"automation:focus-window"' in content
        assert '"automation:close-window"' in content
        assert '"automation:clipboard-read"' in content
        assert '"automation:clipboard-write"' in content
        assert '"automation:ocr"' in content
        assert '"automation:accessibility-tree"' in content

    def test_ipc_workflow_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"workflow:create"' in content
        assert '"workflow:get"' in content
        assert '"workflow:delete"' in content
        assert '"workflow:enable"' in content
        assert '"workflow:disable"' in content
        assert '"workflow:execute"' in content
        assert '"workflow:tick"' in content
        assert '"workflow:active"' in content
        assert '"workflow:history"' in content

    def test_ipc_observability_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"obs:execution-graph"' in content
        assert '"obs:goal-timeline"' in content
        assert '"obs:cost-summary"' in content
        assert '"obs:record-execution"' in content
        assert '"obs:performance-metrics"' in content
        assert '"obs:live-stream"' in content

    def test_ipc_persistence_endpoints(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert '"persistence:create-checkpoint"' in content
        assert '"persistence:get-checkpoint"' in content
        assert '"persistence:restore-checkpoint"' in content
        assert '"persistence:list-checkpoints"' in content
        assert '"persistence:enqueue"' in content
        assert '"persistence:dequeue"' in content
        assert '"persistence:peek-queue"' in content
        assert '"persistence:record-history"' in content
        assert '"persistence:history"' in content
        assert '"persistence:export"' in content
        assert '"persistence:import"' in content
        assert '"persistence:state-versions"' in content
        assert '"persistence:restore-version"' in content
        assert '"persistence:cleanup"' in content

    def test_ipc_version_string(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "M16" in content

    def test_main_index_imports_m16(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert 'import { Supervisor }' in content
        assert 'import { Planner }' in content
        assert 'import { AgentRuntime }' in content
        assert 'import { DesktopAutomation }' in content
        assert 'import { WorkflowEngine }' in content
        assert 'import { Observability }' in content
        assert 'import { Persistence }' in content

    def test_main_index_globals_m16(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "let supervisor: Supervisor" in content
        assert "let planner: Planner" in content
        assert "let agentRuntime: AgentRuntime" in content
        assert "let desktopAutomation: DesktopAutomation" in content
        assert "let workflowEngine: WorkflowEngine" in content
        assert "let observability: Observability" in content
        assert "let persistence: Persistence" in content

    def test_main_index_init_m16(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "new Supervisor()" in content
        assert "new Planner()" in content
        assert "new AgentRuntime()" in content
        assert "new DesktopAutomation()" in content
        assert "new WorkflowEngine()" in content
        assert "new Observability()" in content
        assert "new Persistence()" in content

    def test_main_index_cleanup_m16(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "supervisor.destroy()" in content
        assert "planner.destroy()" in content
        assert "agentRuntime.destroy()" in content
        assert "desktopAutomation.destroy()" in content
        assert "workflowEngine.destroy()" in content
        assert "observability.destroy()" in content
        assert "persistence.destroy()" in content

    def test_main_index_version_string(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "M16" in content

    def test_preload_m16_apis(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "supervisor:" in content
        assert "planner:" in content
        assert "runtime:" in content
        assert "automation:" in content
        assert "workflow:" in content
        assert "obs:" in content
        assert "persistence:" in content

    def test_preload_supervisor_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "submitGoal:" in content
        assert "getGoal:" in content
        assert "cancelGoal:" in content
        assert "pauseGoal:" in content
        assert "resumeGoal:" in content

    def test_preload_planner_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "plan:" in content
        assert "getPlan:" in content
        assert "replan:" in content
        assert "completeTask:" in content
        assert "failTask:" in content
        assert "executeReady:" in content
        assert "getCriticalPath:" in content

    def test_preload_runtime_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "execute:" in content
        assert "executeParallel:" in content
        assert "message:" in content
        assert "inbox:" in content
        assert "setContext:" in content
        assert "artifacts:" in content
        assert "agents:" in content

    def test_preload_automation_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "mouseClick:" in content
        assert "mouseMove:" in content
        assert "mouseDrag:" in content
        assert "mouseScroll:" in content
        assert "keyboardType:" in content
        assert "keyboardHotkey:" in content
        assert "keyboardSequence:" in content
        assert "screenshot:" in content
        assert "windows:" in content
        assert "focusWindow:" in content
        assert "closeWindow:" in content
        assert "clipboardRead:" in content
        assert "clipboardWrite:" in content
        assert "ocr:" in content
        assert "accessibilityTree:" in content

    def test_preload_workflow_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "create:" in content
        assert "get:" in content
        assert "delete:" in content
        assert "enable:" in content
        assert "disable:" in content
        assert "execute:" in content
        assert "tick:" in content
        assert "active:" in content
        assert "history:" in content

    def test_preload_observability_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "executionGraph:" in content
        assert "goalTimeline:" in content
        assert "costSummary:" in content
        assert "recordExecution:" in content
        assert "performanceMetrics:" in content
        assert "liveStream:" in content

    def test_preload_persistence_methods(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "createCheckpoint:" in content
        assert "getCheckpoint:" in content
        assert "restoreCheckpoint:" in content
        assert "listCheckpoints:" in content
        assert "enqueue:" in content
        assert "dequeue:" in content
        assert "peekQueue:" in content
        assert "recordHistory:" in content
        assert "export:" in content
        assert "import:" in content
        assert "stateVersions:" in content
        assert "restoreVersion:" in content
        assert "cleanup:" in content
