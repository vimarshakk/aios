"""Tests for the plugin system — manifest, loader, runtime, sandbox."""

from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from aios.plugins.loader import PluginLoadError, load_plugin
from aios.plugins.manifest import PluginManifest, ToolSpec
from aios.plugins.runtime import (
    PluginAlreadyInstalledError,
    PluginNotFoundError,
    PluginRuntime,
    PluginStatus,
)
from aios.plugins.sandbox import PluginSandbox, SandboxConfig

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# PluginManifest
# ---------------------------------------------------------------------------


class TestPluginManifest:
    def test_from_yaml_minimal(self) -> None:
        yaml_text = textwrap.dedent("""\
            name: hello
        """)
        m = PluginManifest.from_yaml(yaml_text)
        assert m.name == "hello"
        assert m.version == "0.0.0"
        assert m.permissions == ()
        assert m.tools == ()

    def test_from_yaml_full(self) -> None:
        yaml_text = textwrap.dedent("""\
            name: github
            version: 1.2.3
            description: GitHub integration
            author: aios
            permissions:
              - network.http
            tools:
              - name: create_issue
                description: Create a GitHub issue
                parameters:
                  repo: { type: string, required: true }
              - name: create_pr
                description: Create a pull request
            events:
              - GitHubWebhook
            skills:
              - code_review
            entry_point: github_plugin
            enabled: false
        """)
        m = PluginManifest.from_yaml(yaml_text)
        assert m.name == "github"
        assert m.version == "1.2.3"
        assert m.author == "aios"
        assert m.permissions == ("network.http",)
        assert len(m.tools) == 2
        assert m.tools[0].name == "create_issue"
        assert m.tools[0].parameters == {"repo": {"type": "string", "required": True}}
        assert m.tools[1].name == "create_pr"
        assert m.events == ("GitHubWebhook",)
        assert m.skills == ("code_review",)
        assert m.entry_point == "github_plugin"
        assert m.enabled is False

    def test_from_yaml_invalid(self) -> None:
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            PluginManifest.from_yaml("- just a list")

    def test_from_yaml_no_name(self) -> None:
        with pytest.raises(KeyError):
            PluginManifest.from_yaml("version: 1.0.0")

    def test_from_file(self, tmp_path: Path) -> None:
        p = tmp_path / "plugin.yaml"
        p.write_text("name: from_file\nversion: 2.0.0\n")
        m = PluginManifest.from_file(p)
        assert m.name == "from_file"
        assert m.version == "2.0.0"

    def test_from_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            PluginManifest.from_file(tmp_path / "nonexistent.yaml")

    def test_tool_spec(self) -> None:
        t = ToolSpec(name="calc", description="Calculator", parameters={"x": {}})
        assert t.name == "calc"
        assert t.description == "Calculator"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestPluginLoader:
    def test_load_plugin(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "myplugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: myplugin\nversion: 1.0.0\n")

        loaded = load_plugin(plugin_dir)
        assert loaded.manifest.name == "myplugin"
        assert loaded.module is None
        assert loaded.path == plugin_dir

    def test_load_plugin_with_entry_point(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "py_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            "name: py_plugin\nentry_point: main\n"
        )
        (plugin_dir / "main.py").write_text("VALUE = 42\n")

        loaded = load_plugin(plugin_dir)
        assert loaded.module is not None
        assert loaded.module.VALUE == 42  # type: ignore[attr-defined]

    def test_load_plugin_no_manifest(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(PluginLoadError, match=r"No plugin\.yaml"):
            load_plugin(empty_dir)

    def test_load_plugin_bad_entry_point(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "bad_ep"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            "name: bad_ep\nentry_point: nonexistent_module\n"
        )
        with pytest.raises(PluginLoadError, match="Cannot find module"):
            load_plugin(plugin_dir)

    def test_load_plugin_bad_manifest(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "bad_yaml"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("- just a list")
        with pytest.raises(PluginLoadError, match="Failed to parse manifest"):
            load_plugin(plugin_dir)


# ---------------------------------------------------------------------------
# PluginRuntime
# ---------------------------------------------------------------------------


class TestPluginRuntime:
    def test_install(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            "name: rt_plugin\nversion: 1.0.0\ndescription: Test\npermissions:\n  - network.http\n"
        )
        rt = PluginRuntime()
        plugin = rt.install(plugin_dir)
        assert plugin.manifest.name == "rt_plugin"
        assert plugin.status == PluginStatus.ENABLED

    def test_install_disabled(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_disabled"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: rt_disabled\nenabled: false\n")
        rt = PluginRuntime()
        plugin = rt.install(plugin_dir)
        assert plugin.status == PluginStatus.DISABLED

    def test_install_duplicate_raises(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_dup"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: rt_dup\n")
        rt = PluginRuntime()
        rt.install(plugin_dir)
        with pytest.raises(PluginAlreadyInstalledError):
            rt.install(plugin_dir)

    def test_enable_disable(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_toggle"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: rt_toggle\n")
        rt = PluginRuntime()
        rt.install(plugin_dir)
        rt.disable("rt_toggle")
        assert rt.get("rt_toggle").status == PluginStatus.DISABLED
        rt.enable("rt_toggle")
        assert rt.get("rt_toggle").status == PluginStatus.ENABLED

    def test_uninstall(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_rm"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: rt_rm\n")
        rt = PluginRuntime()
        rt.install(plugin_dir)
        rt.uninstall("rt_rm")
        assert rt.is_installed("rt_rm") is False

    def test_uninstall_not_found(self) -> None:
        rt = PluginRuntime()
        with pytest.raises(PluginNotFoundError):
            rt.uninstall("ghost")

    def test_get_not_found(self) -> None:
        rt = PluginRuntime()
        with pytest.raises(PluginNotFoundError):
            rt.get("ghost")

    def test_list_installed(self, tmp_path: Path) -> None:
        for _i, name in enumerate(("a", "b", "c")):
            d = tmp_path / name
            d.mkdir()
            (d / "plugin.yaml").write_text(f"name: {name}\n")

        rt = PluginRuntime()
        rt.install(tmp_path / "a")
        rt.install(tmp_path / "b")
        rt.install(tmp_path / "c")
        assert len(rt.list_installed()) == 3

    def test_get_tools(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_tools"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text(
            textwrap.dedent("""\
                name: rt_tools
                tools:
                  - name: calc
                    description: Calculator
                    parameters: { x: { type: number } }
            """)
        )
        rt = PluginRuntime()
        rt.install(plugin_dir)
        tools = rt.get_tools("rt_tools")
        assert len(tools) == 1
        assert tools[0]["name"] == "calc"
        assert tools[0]["parameters"] == {"x": {"type": "number"}}

    def test_mark_error(self, tmp_path: Path) -> None:
        plugin_dir = tmp_path / "rt_err"
        plugin_dir.mkdir()
        (plugin_dir / "plugin.yaml").write_text("name: rt_err\n")
        rt = PluginRuntime()
        rt.install(plugin_dir)
        rt.mark_error("rt_err", "something broke")
        assert rt.get("rt_err").status == PluginStatus.ERROR
        assert rt.get("rt_err").error == "something broke"


# ---------------------------------------------------------------------------
# PluginSandbox
# ---------------------------------------------------------------------------


class TestPluginSandbox:
    def test_no_config_allows_all(self) -> None:
        sb = PluginSandbox()
        assert sb.check_permission("filesystem.read") is True
        assert sb.check_permission("network.http") is True

    def test_configured_permissions(self) -> None:
        sb = PluginSandbox(SandboxConfig(allowed_permissions=("a", "b")))
        assert sb.check_permission("a") is True
        assert sb.check_permission("c") is False

    def test_filter_permissions(self) -> None:
        sb = PluginSandbox(SandboxConfig(allowed_permissions=("a", "b")))
        allowed, blocked = sb.filter_permissions(["a", "b", "c", "d"])
        assert allowed == ["a", "b"]
        assert blocked == ["c", "d"]

    def test_empty_filter(self) -> None:
        sb = PluginSandbox(SandboxConfig())
        allowed, blocked = sb.filter_permissions(["x", "y"])
        assert allowed == ["x", "y"]
        assert blocked == []
