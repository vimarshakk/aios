"""
M17 Tests — AIOS Developer Mode

Tests for:
- M17.1: WorkforceManager (Worker lifecycle, capability routing, health monitoring)
- M17.2: CLIController (CLI process management, adapter registry)
- M17.3: ReviewPipeline (Review lifecycle, multi-round fixes, verdicts)
- M17.4: Frontend DevMode components (types, store, workspaces)
- M17.5: IPC wiring and integration
"""

import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DESKTOP_DIR = os.path.join(ROOT, "apps", "desktop")
MAIN_DIR = os.path.join(DESKTOP_DIR, "src", "main")
WEB_DIR = os.path.join(ROOT, "apps", "web", "src", "desktop")
GATEWAY_DIR = os.path.join(ROOT, "services", "gateway", "src", "aios", "gateway")


def read_file(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


# ── M17.1: WorkforceManager ──────────────────────────────────────────────────


class TestWorkforceManager:
    """Tests for WorkforceManager backend module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "workforce-manager.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "class WorkforceManager" in content

    def test_has_worker_types(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "WorkerStatus" in content
        assert "WorkerRole" in content
        assert "WorkerCapability" in content

    def test_has_worker_interface(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "interface Worker" in content or "export interface Worker" in content

    def test_has_register_worker(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "registerWorker" in content

    def test_has_unregister_worker(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "unregisterWorker" in content

    def test_has_assign_task(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "assignTask" in content

    def test_has_complete_task(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "completeTask" in content

    def test_has_fail_task(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "failTask" in content

    def test_has_get_workers(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "getWorkers" in content

    def test_has_get_worker(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "getWorker" in content

    def test_has_find_by_capability(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "getWorkersByCapability" in content or "routeToWorker" in content

    def test_has_health_check(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "startHealthCheck" in content or "stopHealthCheck" in content

    def test_has_persistent_state(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "saveState" in content or "loadState" in content

    def test_has_default_workers(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "architect" in content
        assert "backend" in content
        assert "frontend" in content
        assert "qa" in content
        assert "reviewer" in content

    def test_has_event_emitter(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert "EventEmitter" in content

    def test_has_worker_roles_enum(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert '"architect"' in content
        assert '"backend"' in content
        assert '"frontend"' in content
        assert '"qa"' in content
        assert '"devops"' in content
        assert '"researcher"' in content
        assert '"designer"' in content
        assert '"reviewer"' in content

    def test_worker_status_values(self):
        content = read_file(os.path.join(MAIN_DIR, "workforce-manager.ts"))
        assert '"idle"' in content
        assert '"running"' in content
        assert '"paused"' in content
        assert '"error"' in content
        assert '"offline"' in content


# ── M17.2: CLIController ─────────────────────────────────────────────────────


class TestCLIController:
    """Tests for CLIController backend module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "cli-controller.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "class CLIController" in content

    def test_has_spawn_cli(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "spawnCLI" in content or "spawn" in content

    def test_has_stop_cli(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "stopCLI" in content or "stop" in content

    def test_has_interrupt(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "interrupt" in content

    def test_has_get_output(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "getOutput" in content or "get_output" in content

    def test_has_cli_adapter(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "CLIAdapter" in content or "adapter" in content

    def test_has_builtin_adapters(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "claude-code" in content
        assert "opencode" in content
        assert "gemini-cli" in content
        assert "codex-cli" in content

    def test_has_concurrency_limit(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "maxConcurrent" in content or "max_concurrent" in content or "MAX" in content

    def test_has_process_management(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "child_process" in content or "spawn" in content

    def test_has_output_streaming(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "stdout" in content or "onData" in content

    def test_has_cleanup(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "cleanup" in content or "destroy" in content

    def test_has_is_running_check(self):
        content = read_file(os.path.join(MAIN_DIR, "cli-controller.ts"))
        assert "getActiveProcesses" in content or "getProcess" in content


# ── M17.3: ReviewPipeline ────────────────────────────────────────────────────


class TestReviewPipeline:
    """Tests for ReviewPipeline backend module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "review-pipeline.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "class ReviewPipeline" in content

    def test_has_review_status(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "ReviewStatus" in content or "review_status" in content

    def test_has_submit_review(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "submitReview" in content or "submit" in content

    def test_has_approve_review(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "approve" in content

    def test_has_reject_review(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "reject" in content

    def test_has_request_changes(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "requestChanges" in content or "changes" in content

    def test_has_fix_cycle(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "fixCycle" in content or "fix" in content

    def test_has_max_rounds(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "maxFixRounds" in content or "maxFixRounds" in content

    def test_has_get_review(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "getReview" in content or "get_review" in content

    def test_has_list_reviews(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "getAllReviews" in content or "getActiveReviews" in content

    def test_has_review_notes(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "notes" in content or "Notes" in content

    def test_has_verdict(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "verdict" in content

    def test_has_persistence(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "saveState" in content or "loadState" in content or "persist" in content

    def test_has_event_emitter(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert "EventEmitter" in content

    def test_review_status_values(self):
        content = read_file(os.path.join(MAIN_DIR, "review-pipeline.ts"))
        assert '"pending"' in content or "'pending'" in content
        assert '"approved"' in content or "'approved'" in content
        assert '"rejected"' in content or "'rejected'" in content


# ── M17.4: Frontend Types & Store ────────────────────────────────────────────


class TestDevModeTypes:
    """Tests for DevMode frontend types and store."""

    def test_types_file_exists(self):
        assert os.path.exists(os.path.join(WEB_DIR, "types.ts"))

    def test_has_worker_type(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "Worker" in content

    def test_has_worker_status(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "WorkerStatus" in content

    def test_has_worker_role(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "WorkerRole" in content

    def test_has_task_node(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "TaskNode" in content

    def test_has_review_request(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "ReviewRequest" in content

    def test_has_build_artifact(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "BuildArtifact" in content

    def test_has_dev_mode_state(self):
        content = read_file(os.path.join(WEB_DIR, "types.ts"))
        assert "DevModeState" in content


class TestWorkspaceStore:
    """Tests for workspace store with DevMode support."""

    def test_store_file_exists(self):
        assert os.path.exists(os.path.join(WEB_DIR, "state", "workspace.ts"))

    def test_has_dev_mode(self):
        content = read_file(os.path.join(WEB_DIR, "state", "workspace.ts"))
        assert "devMode" in content or "dev_mode" in content

    def test_has_toggle_dev_mode(self):
        content = read_file(os.path.join(WEB_DIR, "state", "workspace.ts"))
        assert "toggleDevMode" in content or "toggle_dev_mode" in content

    def test_has_dev_mode_tab(self):
        content = read_file(os.path.join(WEB_DIR, "state", "workspace.ts"))
        assert "devModeTab" in content or "dev_mode_tab" in content


class TestDevModeWorkspace:
    """Tests for M17.2 dedicated Dev Mode workspace components.

    M17.2 breaks the monolithic DevModeWorkspace into 4 dedicated workspace
    components, each with its own dock entry (dev-workforce, dev-repositories,
    dev-consoles, dev-reviews).
    """

    def test_workforce_workspace_exists(self):
        assert os.path.exists(os.path.join(WEB_DIR, "workspaces", "WorkforceWorkspace.tsx"))

    def test_repositories_workspace_exists(self):
        assert os.path.exists(os.path.join(WEB_DIR, "workspaces", "RepositoriesWorkspace.tsx"))

    def test_consoles_workspace_exists(self):
        assert os.path.exists(os.path.join(WEB_DIR, "workspaces", "ConsolesWorkspace.tsx"))

    def test_reviews_workspace_exists(self):
        assert os.path.exists(os.path.join(WEB_DIR, "workspaces", "ReviewsWorkspace.tsx"))

    def test_has_workforce_panel(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "WorkforceWorkspace.tsx"))
        assert "worker" in content.lower() or "workforce" in content.lower()

    def test_has_task_graph(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "WorkforceWorkspace.tsx"))
        assert "task" in content.lower()

    def test_has_live_console(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "ConsolesWorkspace.tsx"))
        assert "console" in content.lower()

    def test_has_review_panel(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "ReviewsWorkspace.tsx"))
        assert "review" in content.lower()

    def test_registry_wires_dedicated_workspaces(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "registry.tsx"))
        assert "dev-workforce" in content
        assert "dev-repositories" in content
        assert "dev-consoles" in content
        assert "dev-reviews" in content


# ── M17.5: IPC Wiring ───────────────────────────────────────────────────────


class TestIPCWiring:
    """Tests for IPC channel registration."""

    def test_ipc_handler_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "ipc-handler.ts"))

    def test_has_workforce_channels(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "workforce:" in content

    def test_has_cli_channels(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "cli:" in content

    def test_has_review_channels(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "review:" in content

    def test_main_imports_workforce(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "WorkforceManager" in content or "workforce-manager" in content

    def test_main_imports_cli_controller(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "CLIController" in content or "cli-controller" in content

    def test_main_imports_review_pipeline(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "ReviewPipeline" in content or "review-pipeline" in content

    def test_registry_includes_devmode(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "registry.tsx"))
        # M17.2: dedicated workspace components replace the monolithic DevModeWorkspace
        assert "WorkforceWorkspace" in content or "dev-workforce" in content

    def test_registry_has_shortcut(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "registry.tsx"))
        assert "shortcut" in content or "Shortcut" in content or "⌘" in content


# ---------------------------------------------------------------------------
# Test 76+: Gateway M17 API Endpoints
# ---------------------------------------------------------------------------


class TestGatewayWorkforceEndpoints:
    """Tests for the FastAPI workforce/CLI/review endpoints in main.py."""

    def test_main_has_workforce_routes(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "/workforce/workers" in content
        assert "/workforce/assign" in content
        assert "/workforce/complete" in content
        assert "/workforce/state" in content

    def test_main_has_cli_routes(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "/cli/active" in content
        assert "/cli/spawn" in content

    def test_main_has_review_routes(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "/review/active" in content
        assert "/review/create" in content
        assert "/review/{review_id}/verdict" in content
        assert "/review/state" in content

    def test_workforce_list_workers_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def workforce_list_workers" in content

    def test_workforce_assign_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def workforce_assign_task" in content

    def test_workforce_complete_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def workforce_complete_task" in content

    def test_workforce_state_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def workforce_state" in content

    def test_cli_spawn_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def cli_spawn" in content

    def test_review_create_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def review_create" in content

    def test_review_verdict_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def review_submit_verdict" in content

    def test_review_state_handler_exists(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert "def review_state" in content

    def test_default_workforce_count(self):
        content = read_file(os.path.join(GATEWAY_DIR, "main.py"))
        assert '"architect"' in content
        assert '"backend"' in content
        assert '"frontend"' in content
        assert '"qa"' in content
        assert '"devops"' in content
        assert '"researcher"' in content
        assert '"designer"' in content
        assert '"reviewer"' in content


class TestFrontendAPIWorkforce:
    """Tests for the new workforce/review/CLI API client methods."""

    def test_api_has_workforce_section(self):
        api_path = os.path.join(ROOT, "apps", "web", "src", "lib", "api.ts")
        content = read_file(api_path)
        assert "workforce" in content
        assert "listWorkers" in content
        assert "findByCapability" in content

    def test_api_has_cli_section(self):
        api_path = os.path.join(ROOT, "apps", "web", "src", "lib", "api.ts")
        content = read_file(api_path)
        assert "cli" in content
        assert "activeProcesses" in content

    def test_api_has_reviews_section(self):
        api_path = os.path.join(ROOT, "apps", "web", "src", "lib", "api.ts")
        content = read_file(api_path)
        assert "reviews" in content
        assert "listActive" in content
        assert "create" in content
        assert "verdict" in content

    def test_api_workforce_assigns_task(self):
        api_path = os.path.join(ROOT, "apps", "web", "src", "lib", "api.ts")
        content = read_file(api_path)
        assert "assignTask" in content
        assert "/workforce/assign" in content

    def test_api_reviews_verdict(self):
        api_path = os.path.join(ROOT, "apps", "web", "src", "lib", "api.ts")
        content = read_file(api_path)
        assert "/review/" in content
        assert "verdict" in content

    def test_devmode_uses_api(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "WorkforceWorkspace.tsx"))
        assert "api.workforce" in content or "api.workforce.listWorkers" in content

    def test_devmode_no_mock_workers(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "WorkforceWorkspace.tsx"))
        assert "MOCK_WORKERS" not in content

    def test_devmode_has_fetch(self):
        content = read_file(os.path.join(WEB_DIR, "workspaces", "WorkforceWorkspace.tsx"))
        assert "fetchWorkforce" in content or "fetchWorkers" in content or "useEffect" in content

    def test_appshell_has_devmode_shortcut(self):
        content = read_file(os.path.join(ROOT, "apps", "web", "src", "desktop", "layout", "AppShell.tsx"))
        assert "toggleDevMode" in content
        assert '"d"' in content or "'d'" in content

    def test_appshell_shortcut_is_shift_d(self):
        content = read_file(os.path.join(ROOT, "apps", "web", "src", "desktop", "layout", "AppShell.tsx"))
        assert "shiftKey" in content
        assert "toggleDevMode" in content
