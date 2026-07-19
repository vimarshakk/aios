"""AIOS Developer Platform runtime.

Composes the M4 foundation packages into a single runtime surface that the
gateway/service layer can wire into the :class:`~aios.orchestrator.main.Orchestrator`.

Layering (ADR-0019)::

    Agent → Skill → Capability (catalog) → Permission (frozen)
          ← Connector → Integration → MCP (transport)

The platform:

* indexes agent capabilities into the :class:`CapabilityCatalog` (single source
  of truth) instead of leaving them as bare strings;
* gates sensitive actions through the :class:`PolicyEngine` (built on the
  frozen permission layer);
* plans and executes skills with scoped :class:`Workspace` secrets;
* holds the connector / MCP registries and secret store.

It does NOT modify frozen interfaces and does NOT duplicate the orchestrator's
routing logic — it augments registration and authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from aios.agents.capability_catalog import CapabilityCatalog, CapabilityNode
from aios.integrations.connector import ConnectorRegistry
from aios.mcp.client import MCPRegistry
from aios.orchestrator.main import Orchestrator
from aios.platform.resolver import CapabilityResolver, ProviderKind, Resolution
from aios.prompts import PromptLibrary, default_library
from aios.secrets import MemoryBackend, SecretStore
from aios.security.encryption import VaultEncryptor
from aios.security.policy import ApprovalDecision, PolicyEngine
from aios.skills.executor import ExecutionRecord, SkillExecutor
from aios.skills.planner import SkillPlan, SkillPlanner
from aios.skills.registry import SkillRegistry
from aios.workspaces import Workspace, WorkspaceConfig, WorkspaceManager

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from aios.agents.base import BaseAgent
    from aios.skills.base import Skill


@dataclass
class AgentRegistration:
    """Result of registering an agent with the platform."""

    name: str
    capabilities: list[CapabilityNode]
    catalog_size: int


class DeveloperPlatform:
    """Runtime composition root for the AI Developer Platform.

    Args:
        orchestrator: The routing orchestrator (created internally if omitted).
        catalog: Capability catalog (created internally if omitted).
        policy: Approval policy engine (created internally if omitted).
        secrets: Secret store (created internally if omitted).
        encryptor_password: Master password for the default secret vault.
            In production this must come from a secret manager, not a literal.
    """

    def __init__(
        self,
        orchestrator: Orchestrator | None = None,
        catalog: CapabilityCatalog | None = None,
        policy: PolicyEngine | None = None,
        secrets: SecretStore | None = None,
        encryptor_password: str | None = None,
        granted_permissions: Sequence[str] | None = None,
    ) -> None:
        self.orchestrator = orchestrator or Orchestrator()
        self.catalog = catalog or CapabilityCatalog()
        self.policy = policy or PolicyEngine(catalog=self.catalog)
        self.secrets = secrets or SecretStore(
            VaultEncryptor.from_password(encryptor_password or "dev-platform"),
            backend=MemoryBackend(),
        )
        self.skills = SkillRegistry()
        self.executor = SkillExecutor(
            catalog=self.catalog,
            granted_permissions=list(granted_permissions or []),
        )
        self.planner = SkillPlanner(self.skills)
        self.workspaces = WorkspaceManager()
        self.connectors = ConnectorRegistry()
        self.mcp = MCPRegistry()
        self.prompts: PromptLibrary = default_library()
        self.resolver = CapabilityResolver(skills=self.skills)
        self._agent_caps: dict[str, list[str]] = {}

    # ------------------------------------------------------------------ agents

    def register_agent(
        self,
        name: str,
        agent: BaseAgent,
        capability_ids: Iterable[str] | None = None,
    ) -> AgentRegistration:
        """Register an agent and index its capabilities into the catalog.

        Capability ids that are unknown to the catalog are still accepted by
        the orchestrator pool but are not catalog-backed (best-effort).
        """
        caps = list(capability_ids or [])
        self.orchestrator.register_agent(name, agent, capabilities=set(caps))
        nodes = [self.catalog.get(c) for c in caps if self.catalog.has(c)]
        self._agent_caps[name] = caps
        return AgentRegistration(
            name=name, capabilities=nodes, catalog_size=len(self.catalog.all())
        )

    def list_agent_capabilities(self, name: str) -> list[str]:
        """Return the capability ids registered for an agent."""
        return list(self._agent_caps.get(name, []))

    # ----------------------------------------------------------------- policy

    def capabilities_for_skill(self, skill_name: str) -> list[str]:
        """Return capability ids declared by a registered skill's manifest.

        Returns an empty list for unknown skills (best-effort) so callers can
        decide on a no-capability / deny basis.
        """
        skill = self.skills.get(skill_name)
        if skill is None:
            return []
        try:
            return list(skill.manifest.capabilities)
        except Exception:  # manifest may be uninitialized
            return []

    # ------------------------------------------------------------- resolution

    def resolve(self, capability: str) -> Resolution:
        """Resolve a logical capability to the best available provider.

        Native AIOS skills are preferred (offline-capable); optional providers
        (Composio connectors, MCP servers) are used only when no native skill
        exists and the provider is connected. See ``CapabilityResolver``.
        """
        return self.resolver.resolve(capability)

    def register_provider(
        self,
        capability: str,
        provider_id: str,
        kind: ProviderKind,
        is_available: Any | None = None,
    ) -> None:
        """Register an optional provider for a capability in the resolver."""
        self.resolver.register_provider(capability, provider_id, kind, is_available)

    def authorize(
        self,
        capabilities: Sequence[str] | None = None,
        permissions: Sequence[str] | None = None,
        manifest_approval: str | None = None,
    ) -> ApprovalDecision:
        """Evaluate an approval decision for an action."""
        return self.policy.evaluate(
            capabilities=list(capabilities or []),
            permissions=list(permissions or []),
            manifest_approval=manifest_approval,
        )

    # ------------------------------------------------------------- skills/plan

    def plan(self, goal: str, capabilities: Sequence[str] | None = None) -> SkillPlan:
        """Plan a sequence of skills to satisfy a goal."""
        return self.planner.plan(goal, list(capabilities or []))

    def register_skill(self, skill: Skill) -> None:
        """Register a skill with the platform's skill registry."""
        self.skills.register(skill)

    async def execute_skill(
        self,
        name: str,
        inputs: dict[str, Any] | None = None,
        workspace_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a registered skill, optionally inside a scoped workspace.

        Returns the :class:`SkillResult`. The skill runs with the workspace's
        scoped secrets resolved into ``metadata["workspace_secrets"]`` when a
        workspace is provided.
        """
        skill = self.skills.get(name)
        if skill is None:
            from aios.skills.base import SkillResult, SkillStatus

            return SkillResult(
                status=SkillStatus.FAILED, error=f"Unknown skill: {name}"
            )
        if workspace_id:
            ws = self.workspaces.get(workspace_id)
            if ws is not None:
                meta = dict(metadata or {})
                secrets_view = {
                    k: ws.scoped_secret(k) for k in ws.assigned_skill_names
                }
                meta.setdefault("workspace_secrets", secrets_view)
                metadata = meta
        return await self.executor.execute(skill, inputs=inputs, metadata=metadata)

    @property
    def execution_history(self) -> list[ExecutionRecord]:
        """Skill execution history."""
        return self.executor.history

    # -------------------------------------------------------------- workspaces

    def create_workspace(
        self,
        workspace_id: str,
        root: str = ".",
        skill_names: Iterable[str] = (),
        secret_prefix: str = "WS_",  # noqa: S107  (prefix, not a secret)
    ) -> Workspace:
        """Create a scoped workspace bound to the platform's skills/secrets."""
        return self.workspaces.create(
            WorkspaceConfig(
                id=workspace_id,
                root=root,
                skill_names=tuple(skill_names),
                secret_prefix=secret_prefix,
            ),
            skills=self.skills,
            secrets=self.secrets,
        )

    # -------------------------------------------------------------------- misc

    def bootstrap(self) -> None:
        """Seed builtins: register builtin + native desktop skills and the
        capability resolver's native providers.

        Connectors require integration instances (see
        :func:`aios.integrations.connectors.register_builtin_connectors`)
        and are registered separately by the integrating service. Optional
        providers (Composio, MCP) register into the resolver when connected.
        """
        from aios.skills.builtin import register_builtins
        from aios.skills.native import register_native_skills

        register_builtins(self.skills)
        register_native_skills(self.skills, self.resolver)
        self._grant_native_permissions()
        # Prompts are already seeded via default_library() in __init__.

    def _grant_native_permissions(self) -> None:
        """Grant the permissions declared by AIOS-native desktop skills.

        Native skills implement capabilities the AI OS owns and runs offline
        (local git/docker/filesystem/notes/notify/terminal). The executor gates
        every skill on its declared permissions, so without this grant the
        platform could resolve a capability but never execute it — a silent
        runtime failure. External/optional providers remain ungated-by-default
        and must be approved through the policy engine.
        """
        native_perms: set[str] = set()
        for skill in self.skills._skills.values():
            native_perms.update(getattr(skill.manifest, "permissions", ()) or ())
        if native_perms:
            self.executor._granted |= native_perms


__all__ = ["AgentRegistration", "DeveloperPlatform"]
