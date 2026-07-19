# OSS Integration Module Graph

**Date:** 2025-07-17
**Milestone:** M9 — OSS Integration Layer

---

## Module Layout

```
packages/integrations/src/aios/integrations/
├── base.py                    # Integration ABC
├── types.py                   # IntegrationConfig, IntegrationResult, IntegrationStatus, HealthCheckResult
├── connector.py               # Connector ABC, ConnectorBinding, ConnectorRegistry
├── registry.py                # IntegrationRegistry
└── oss/
    ├── __init__.py            # Package exports, ADAPTER_REGISTRY, UPSTREAM_VERSIONS, UPSTREAM_LICENSES
    ├── openjarvis.py          # OpenJarvisIntegration
    ├── openhands.py           # OpenHandsIntegration
    ├── openinterpreter.py     # OpenInterpreterIntegration
    ├── anythingllm.py         # AnythingLLMIntegration
    ├── librechat.py           # LibreChatIntegration
    ├── openwebui.py           # OpenWebUIIntegration
    ├── continue_dev.py        # ContinueIntegration
    ├── jan.py                 # JanIntegration
    └── connectors.py          # OpenJarvisConnector, OpenHandsConnector, etc.
```

## Class Hierarchy

```
Integration (ABC)
├── OpenJarvisIntegration
├── OpenHandsIntegration
├── OpenInterpreterIntegration
├── AnythingLLMIntegration
├── LibreChatIntegration
├── OpenWebUIIntegration
├── ContinueIntegration
└── JanIntegration

Connector (ABC)
├── OpenJarvisConnector
├── OpenHandsConnector
├── OpenInterpreterConnector
├── AnythingLLMConnector
├── LibreChatConnector
├── OpenWebUIConnector
├── ContinueConnector
└── JanConnector
```

## Adapter → Capability Mapping

```
OpenJarvisIntegration
  ├── execute_workflow      → workflow.execute
  ├── schedule_task         → workflow.schedule
  ├── evaluate              → evaluation.run
  ├── reason                → reasoning.invoke
  ├── list_workflows        → workflow.list
  └── list_evaluators       → evaluation.list

OpenHandsIntegration
  ├── run_sandbox           → coding.sandbox
  ├── git_operation         → coding.git
  ├── edit_repository       → coding.edit_repository
  ├── browse_url            → coding.browse
  ├── run_task              → coding.run_task
  └── list_sessions         → coding.list_sessions

OpenInterpreterIntegration
  ├── run_shell             → desktop.shell
  ├── run_python            → desktop.python
  ├── desktop_automate      → desktop.automate
  ├── file_read             → desktop.file_read
  ├── file_write            → desktop.file_write
  ├── file_list             → desktop.file_list
  └── chat                  → desktop.chat

AnythingLLMIntegration
  ├── ingest_document       → rag.ingest
  ├── embed                 → rag.embed
  ├── retrieve              → rag.retrieve
  ├── rag_query             → rag.query
  ├── list_workspaces       → rag.list_workspaces
  ├── list_documents        → rag.list_documents
  ├── delete_document       → rag.delete_document
  └── configure             → rag.configure

LibreChatIntegration
  ├── create_conversation   → conversation.create
  ├── send_message          → conversation.send
  ├── get_conversation      → conversation.get
  ├── list_conversations    → conversation.list
  ├── render_markdown       → conversation.render_markdown
  ├── create_artifact       → artifact.create
  ├── get_artifact          → artifact.get
  ├── list_artifacts        → artifact.list
  ├── create_session        → session.create
  ├── get_session           → session.get
  └── end_session           → session.end

OpenWebUIIntegration
  ├── list_models           → model.list
  ├── get_model             → model.get
  ├── download_model        → model.download
  ├── delete_model          → model.delete
  ├── configure_provider    → provider.configure
  ├── list_providers        → provider.list
  ├── inference             → inference.run
  ├── list_pipelines        → pipeline.list
  └── get_pipeline          → pipeline.get

ContinueIntegration
  ├── index_codebase        → ide.index
  ├── autocomplete          → ide.autocomplete
  ├── chat                  → ide.chat
  ├── edit_code             → ide.edit_code
  ├── get_definitions       → ide.get_definitions
  ├── get_references        → ide.get_references
  ├── run_mcp               → ide.run_mcp
  ├── list_mcp_tools        → ide.list_mcp_tools
  └── get_context           → ide.get_context

JanIntegration
  ├── list_models           → model.list
  ├── get_model             → model.get
  ├── download_model        → model.download
  ├── delete_model          → model.delete
  ├── update_model          → model.update
  ├── start_model           → model.start
  ├── stop_model            → model.stop
  ├── list_engines          → engine.list
  └── configure_engine      → engine.configure
```

## Factory Functions

```
create_oss_integration(name, config?) → Integration
create_oss_connector(name, integration) → Connector
register_all_oss(integration_registry, connector_registry, config_factory?) → dict
```
