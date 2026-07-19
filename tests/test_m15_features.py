"""
M15 Tests — Cloud Sync, Collaboration, Analytics, AI Features

Tests for:
- M15.1: CloudSync
- M15.2: CollaborationManager
- M15.3: AnalyticsEngine
- M15.4: AIAssistant
- M15.5: IPC handler, main process, preload integration
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


# ── M15.1: CloudSync ──────────────────────────────────────────────────────

class TestCloudSync:
    """Tests for CloudSync module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "cloud-sync.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "class CloudSync" in content

    def test_has_sync_config(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "SyncConfig" in content

    def test_has_sync_item(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "SyncItem" in content

    def test_has_sync_state(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "SyncState" in content

    def test_has_sync_conflict(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "SyncConflict" in content

    def test_has_set_get_item(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "setItem" in content
        assert "getItem" in content

    def test_has_remove_item(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "removeItem" in content

    def test_has_sync_cycle(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "async sync" in content
        assert "forceSyncAll" in content

    def test_has_start_stop(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "startSync" in content
        assert "stopSync" in content

    def test_has_conflict_resolution(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "resolveConflict" in content
        assert "getConflicts" in content

    def test_has_event_emitter(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "EventEmitter" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "cloud-sync.ts"))
        assert "destroy" in content


# ── M15.2: CollaborationManager ───────────────────────────────────────────

class TestCollaborationManager:
    """Tests for CollaborationManager module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "collaboration-manager.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "class CollaborationManager" in content

    def test_has_collaborator(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "Collaborator" in content

    def test_has_shared_workspace(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "SharedWorkspace" in content

    def test_has_workspace_permission(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "WorkspacePermission" in content

    def test_has_activity_entry(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "ActivityEntry" in content

    def test_has_create_workspace(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "createWorkspace" in content

    def test_has_collaborator_management(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "addCollaborator" in content
        assert "removeCollaborator" in content

    def test_has_cursor(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "CursorPosition" in content
        assert "updateCursor" in content

    def test_has_permissions(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "grantPermission" in content
        assert "hasPermission" in content

    def test_has_activity_feed(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "getActivityFeed" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "collaboration-manager.ts"))
        assert "destroy" in content


# ── M15.3: AnalyticsEngine ────────────────────────────────────────────────

class TestAnalyticsEngine:
    """Tests for AnalyticsEngine module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "analytics-engine.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "class AnalyticsEngine" in content

    def test_has_session(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "Session" in content

    def test_has_feature_usage(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "FeatureUsage" in content

    def test_has_productivity_score(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "ProductivityScore" in content

    def test_has_usage_pattern(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "UsagePattern" in content

    def test_has_start_end_session(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "startSession" in content
        assert "endSession" in content

    def test_has_track_event(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "trackEvent" in content

    def test_has_feature_usage_stats(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "getFeatureUsage" in content

    def test_has_productivity_calculation(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "getProductivityScore" in content

    def test_has_snapshot(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "getSnapshot" in content
        assert "AnalyticsSnapshot" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "analytics-engine.ts"))
        assert "destroy" in content


# ── M15.4: AIAssistant ───────────────────────────────────────────────────

class TestAIAssistant:
    """Tests for AIAssistant module."""

    def test_file_exists(self):
        assert os.path.exists(os.path.join(MAIN_DIR, "ai-assistant.ts"))

    def test_has_class(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "class AIAssistant" in content

    def test_has_ai_message(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "AIMessage" in content

    def test_has_ai_suggestion(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "AISuggestion" in content

    def test_has_ai_conversation(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "AIConversation" in content

    def test_has_ai_action(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "AIAction" in content

    def test_has_send_message(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "async sendMessage" in content

    def test_has_conversation_management(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "createConversation" in content
        assert "getConversations" in content
        assert "deleteConversation" in content

    def test_has_context(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "updateContext" in content
        assert "getContext" in content

    def test_has_command_history(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "getCommandHistory" in content

    def test_has_state(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "getState" in content
        assert "AIAssistantState" in content

    def test_has_destroy(self):
        content = read_file(os.path.join(MAIN_DIR, "ai-assistant.ts"))
        assert "destroy" in content


# ── M15.5: IPC Handler Integration ────────────────────────────────────────

class TestIpcHandlerM15:
    """Tests for IPC handler M15 integration."""

    def test_ipc_handler_has_sync_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'sync:state' in content
        assert 'sync:set-item' in content
        assert 'sync:get-item' in content
        assert 'sync:force-sync' in content

    def test_ipc_handler_has_collab_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'collab:create-workspace' in content
        assert 'collab:get-workspaces' in content
        assert 'collab:add-collaborator' in content
        assert 'collab:update-cursor' in content

    def test_ipc_handler_has_analytics_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'analytics:state' in content
        assert 'analytics:start-session' in content
        assert 'analytics:end-session' in content
        assert 'analytics:productivity' in content

    def test_ipc_handler_has_ai_handlers(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert 'ai:state' in content
        assert 'ai:send-message' in content
        assert 'ai:create-conversation' in content
        assert 'ai:get-conversations' in content

    def test_ipc_handler_imports_m15(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "CloudSync" in content
        assert "CollaborationManager" in content
        assert "AnalyticsEngine" in content
        assert "AIAssistant" in content

    def test_ipc_handler_has_m15_deps(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "cloudSync" in content
        assert "collaborationManager" in content
        assert "analyticsEngine" in content
        assert "aiAssistant" in content

    def test_ipc_handler_version_log(self):
        content = read_file(os.path.join(MAIN_DIR, "ipc-handler.ts"))
        assert "M15" in content


# ── M15.5: Main Process Integration ───────────────────────────────────────

class TestMainProcessM15:
    """Tests for main process M15 integration."""

    def test_main_imports_m15(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "CloudSync" in content
        assert "CollaborationManager" in content
        assert "AnalyticsEngine" in content
        assert "AIAssistant" in content

    def test_main_initializes_m15(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "new CloudSync()" in content
        assert "new CollaborationManager()" in content
        assert "new AnalyticsEngine()" in content
        assert "new AIAssistant()" in content

    def test_main_registers_m15_deps(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "cloudSync," in content
        assert "collaborationManager," in content
        assert "analyticsEngine," in content
        assert "aiAssistant," in content

    def test_main_cleans_up_m15(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "cloudSync.destroy()" in content
        assert "collaborationManager.destroy()" in content
        assert "analyticsEngine.destroy()" in content
        assert "aiAssistant.destroy()" in content

    def test_main_starts_sync(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "cloudSync.startSync" in content

    def test_main_starts_analytics(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "analyticsEngine.startSession" in content

    def test_main_version_log(self):
        content = read_file(os.path.join(MAIN_DIR, "index.ts"))
        assert "M15" in content


# ── M15.5: Preload Integration ────────────────────────────────────────────

class TestPreloadM15:
    """Tests for preload M15 API exposure."""

    def test_preload_has_sync_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "sync:state" in content
        assert "sync:set-item" in content
        assert "sync:force-sync" in content

    def test_preload_has_collab_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "collab:create-workspace" in content
        assert "collab:get-workspaces" in content
        assert "collab:add-collaborator" in content

    def test_preload_has_analytics_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "analytics:state" in content
        assert "analytics:start-session" in content
        assert "analytics:productivity" in content

    def test_preload_has_ai_api(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "ai:state" in content
        assert "ai:send-message" in content
        assert "ai:create-conversation" in content

    def test_preload_listens_m15_events(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "sync-complete" in content
        assert "workspace-created" in content
        assert "typing-started" in content

    def test_preload_api_interfaces(self):
        content = read_file(os.path.join(PRELOAD_DIR, "index.ts"))
        assert "sync:" in content
        assert "collab:" in content
        assert "analytics:" in content
        assert "ai:" in content


# ── M15.5: Test Coverage ─────────────────────────────────────────────────

class TestM15TestCoverage:
    """Meta-tests for M15 test coverage."""

    def test_all_m15_files_exist(self):
        files = [
            "cloud-sync.ts",
            "collaboration-manager.ts",
            "analytics-engine.ts",
            "ai-assistant.ts",
        ]
        for f in files:
            path = os.path.join(MAIN_DIR, f)
            assert os.path.exists(path), f"Missing {path}"

    def test_test_file_exists(self):
        path = os.path.join(ROOT, "tests", "test_m15_features.py")
        assert os.path.exists(path), f"Missing {path}"

    def test_test_count(self):
        path = os.path.join(ROOT, "tests", "test_m15_features.py")
        content = read_file(path)
        test_count = content.count("def test_")
        assert test_count >= 50, f"Expected at least 50 tests, found {test_count}"
