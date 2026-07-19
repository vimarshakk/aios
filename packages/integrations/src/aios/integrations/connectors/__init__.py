"""Built-in connectors — bind capabilities to concrete integrations.

These are reference implementations demonstrating the Connector contract
(ADR-0019). Each connector drives a backing
:class:`~aios.integrations.base.Integration` and exposes capability bindings.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aios.agents.permissions import Permission
from aios.integrations.composio import ComposioConnector
from aios.integrations.connector import Connector, ConnectorBinding

if TYPE_CHECKING:
    from aios.integrations.base import Integration


class GitHubConnector(Connector):
    """Connector exposing git/github capabilities via a GitHub integration."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="github")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="git.push",
                action="push",
                required_permissions=(Permission.PROCESS_EXEC,),
                description="Push commits to a remote",
            ),
            ConnectorBinding(
                capability="git.commit",
                action="commit",
                required_permissions=(Permission.PROCESS_EXEC,),
                description="Create a commit",
            ),
            ConnectorBinding(
                capability="git.clone",
                action="clone",
                required_permissions=(Permission.NETWORK_HTTP,),
                description="Clone a repository",
            ),
        ]


class SlackConnector(Connector):
    """Connector exposing messaging capabilities via a Slack integration."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="slack")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="slack.send",
                action="send_message",
                required_permissions=(Permission.NETWORK_HTTP,),
                description="Send a Slack message",
            ),
            ConnectorBinding(
                capability="slack.read",
                action="list_messages",
                required_permissions=(Permission.NETWORK_HTTP,),
                description="Read Slack messages",
            ),
        ]


class FilesystemConnector(Connector):
    """Connector exposing filesystem capabilities via a filesystem integration."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="filesystem")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="filesystem.read",
                action="read",
                required_permissions=(Permission.FILESYSTEM_READ,),
                description="Read a file",
            ),
            ConnectorBinding(
                capability="filesystem.write",
                action="write",
                required_permissions=(Permission.FILESYSTEM_WRITE,),
                description="Write a file",
            ),
            ConnectorBinding(
                capability="filesystem.list",
                action="list",
                required_permissions=(Permission.FILESYSTEM_READ,),
                description="List a directory",
            ),
        ]


class GmailConnector(Connector):
    """Connector exposing mail capabilities via a Gmail integration."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="gmail")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="gmail.send",
                action="send_message",
                required_permissions=(Permission.NETWORK_HTTP,),
                description="Send an email",
            ),
            ConnectorBinding(
                capability="gmail.read",
                action="list_messages",
                required_permissions=(Permission.NETWORK_HTTP,),
                description="Read inbox messages",
            ),
            ConnectorBinding(
                capability="gmail.draft",
                action="create_draft",
                required_permissions=(Permission.NETWORK_HTTP,),
                description="Create a draft email",
            ),
        ]


class DockerConnector(Connector):
    """Connector exposing container capabilities via a Docker integration."""

    def __init__(self, integration: Integration) -> None:
        super().__init__(integration, name="docker")

    def bindings(self) -> list[ConnectorBinding]:
        return [
            ConnectorBinding(
                capability="docker.run",
                action="run",
                required_permissions=(Permission.PROCESS_EXEC,),
                description="Run a container",
            ),
            ConnectorBinding(
                capability="docker.build",
                action="build",
                required_permissions=(Permission.PROCESS_EXEC,),
                description="Build an image",
            ),
            ConnectorBinding(
                capability="docker.ps",
                action="list_containers",
                required_permissions=(Permission.PROCESS_EXEC,),
                description="List running containers",
            ),
        ]


def register_builtin_connectors(registry, integrations: dict[str, Integration]) -> None:
    """Register built-in connectors backed by the given integrations.

    Args:
        registry: A :class:`ConnectorRegistry` to populate.
        integrations: Mapping of integration name (``github``/``slack``/
            ``filesystem``/``gmail``/``docker``/``composio``) to its instance.
    """
    if (gh := integrations.get("github")) is not None:
        registry.register(GitHubConnector(gh))
    if (sl := integrations.get("slack")) is not None:
        registry.register(SlackConnector(sl))
    if (fs := integrations.get("filesystem")) is not None:
        registry.register(FilesystemConnector(fs))
    if (gm := integrations.get("gmail")) is not None:
        registry.register(GmailConnector(gm))
    if (dk := integrations.get("docker")) is not None:
        registry.register(DockerConnector(dk))
    if (cx := integrations.get("composio")) is not None:
        registry.register(ComposioConnector(cx))


__all__ = [
    "ComposioConnector",
    "DockerConnector",
    "FilesystemConnector",
    "GitHubConnector",
    "GmailConnector",
    "SlackConnector",
    "register_builtin_connectors",
]
