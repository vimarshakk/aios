"""Tests for RegistryBase, typed registries, Capability, and CapabilityRegistry."""

import pytest

from aios.agents.registry import (
    AgentRegistry,
    Capability,
    CapabilityRegistry,
    ModelRegistry,
    PluginRegistry,
    PromptRegistry,
    ProviderRegistry,
    RegistryBase,
    SkillRegistry,
    ToolRegistry,
    WorkflowRegistry,
)

# ---------------------------------------------------------------------------
# RegistryBase
# ---------------------------------------------------------------------------


class TestRegistryBase:
    def test_register_decorator(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        MyRegistry.register("hello")("world")
        assert MyRegistry.get("hello") == "world"

    def test_register_duplicate_raises(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        MyRegistry.register("hello")("world")
        with pytest.raises(ValueError, match="already has an entry"):
            MyRegistry.register("hello")("again")

    def test_get_missing_raises(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        with pytest.raises(KeyError, match="does not have an entry"):
            MyRegistry.get("missing")

    def test_register_value(self):
        class MyRegistry(RegistryBase[int]):
            pass

        MyRegistry.clear()
        MyRegistry.register_value("count", 42)
        assert MyRegistry.get("count") == 42

    def test_items(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        MyRegistry.register("a")("alpha")
        MyRegistry.register("b")("bravo")
        items = MyRegistry.items()
        assert len(items) == 2
        assert ("a", "alpha") in items

    def test_keys(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        MyRegistry.register("x")("x-ray")
        MyRegistry.register("y")("yankee")
        assert set(MyRegistry.keys()) == {"x", "y"}

    def test_contains(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        MyRegistry.register("yes")("!")
        assert MyRegistry.contains("yes") is True
        assert MyRegistry.contains("no") is False

    def test_clear(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.register("a")("1")
        MyRegistry.register("b")("2")
        MyRegistry.clear()
        assert len(MyRegistry.items()) == 0

    def test_create(self):
        class MyRegistry(RegistryBase):
            pass

        MyRegistry.clear()
        MyRegistry.register("factory")(lambda x: x * 2)
        result = MyRegistry.create("factory", 5)
        assert result == 10

    def test_create_not_callable(self):
        class MyRegistry(RegistryBase[str]):
            pass

        MyRegistry.clear()
        MyRegistry.register("val")("not_callable")
        with pytest.raises(TypeError, match="is not callable"):
            MyRegistry.create("val")

    def test_typed_registries_are_isolated(self):
        ModelRegistry.clear()
        AgentRegistry.clear()
        ModelRegistry.register("model1")("spec")
        AgentRegistry.register("agent1")("impl")
        assert ModelRegistry.contains("model1") is True
        assert AgentRegistry.contains("model1") is False
        assert AgentRegistry.contains("agent1") is True
        assert ModelRegistry.contains("agent1") is False


# ---------------------------------------------------------------------------
# New typed registries
# ---------------------------------------------------------------------------


class TestNewTypedRegistries:
    def test_plugin_registry(self):
        PluginRegistry.clear()
        PluginRegistry.register_value("github", {"name": "github"})
        assert PluginRegistry.get("github") == {"name": "github"}

    def test_prompt_registry(self):
        PromptRegistry.clear()
        PromptRegistry.register_value("summarize", "Summarize this:")
        assert PromptRegistry.get("summarize") == "Summarize this:"

    def test_workflow_registry(self):
        WorkflowRegistry.clear()
        WorkflowRegistry.register_value("deploy", {"steps": ["build", "ship"]})
        assert WorkflowRegistry.get("deploy") == {"steps": ["build", "ship"]}

    def test_provider_registry(self):
        ProviderRegistry.clear()
        ProviderRegistry.register_value("ollama", "OllamaEngine")
        assert ProviderRegistry.get("ollama") == "OllamaEngine"


# ---------------------------------------------------------------------------
# Capability dataclass
# ---------------------------------------------------------------------------


class TestCapability:
    def test_construction(self):
        cap = Capability(name="calc", capability_type="tool")
        assert cap.name == "calc"
        assert cap.capability_type == "tool"
        assert cap.version == "0.0.0"
        assert cap.description == ""
        assert cap.permissions == ()
        assert cap.tags == ()
        assert cap.entry_point is None

    def test_full_construction(self):
        cap = Capability(
            name="web",
            capability_type="tool",
            version="1.2.0",
            description="Fetch web pages",
            permissions=("network.http",),
            tags=("web", "fetch"),
            entry_point="WebFetchTool",
        )
        assert cap.version == "1.2.0"
        assert cap.permissions == ("network.http",)
        assert cap.tags == ("web", "fetch")
        assert cap.entry_point == "WebFetchTool"

    def test_frozen(self):
        cap = Capability(name="x", capability_type="tool")
        with pytest.raises(AttributeError):
            cap.name = "y"  # type: ignore[misc]

    def test_equality(self):
        a = Capability(name="a", capability_type="tool")
        b = Capability(name="a", capability_type="tool")
        assert a == b


# ---------------------------------------------------------------------------
# CapabilityRegistry
# ---------------------------------------------------------------------------


class TestCapabilityRegistry:
    def setup_method(self):
        CapabilityRegistry.clear()
        PluginRegistry.clear()
        ToolRegistry.clear()
        AgentRegistry.clear()
        PromptRegistry.clear()
        WorkflowRegistry.clear()
        ProviderRegistry.clear()
        SkillRegistry.clear()

    def test_register_and_get(self):
        cap = CapabilityRegistry.register(
            "calculator",
            "tool",
            entry_point="CalcTool",
            version="1.0.0",
            description="Performs calculations",
            permissions=("process.exec",),
            tags=("math", "utility"),
        )
        assert cap.name == "calculator"
        assert cap.version == "1.0.0"
        assert cap.permissions == ("process.exec",)
        assert cap.tags == ("math", "utility")

        fetched = CapabilityRegistry.get("calculator")
        assert fetched is cap

    def test_register_invalid_type_raises(self):
        with pytest.raises(ValueError, match="Unknown capability type"):
            CapabilityRegistry.register("bad", "invalid_type")

    def test_discover(self):
        CapabilityRegistry.register("alpha", "tool", description="First")
        CapabilityRegistry.register("beta", "agent", description="Second")
        CapabilityRegistry.register("gamma", "plugin")

        caps = CapabilityRegistry.discover()
        names = {c.name for c in caps}
        assert names == {"alpha", "beta", "gamma"}

    def test_find_by_query(self):
        CapabilityRegistry.register("web_fetch", "tool", description="Fetch web pages")
        CapabilityRegistry.register("web_search", "tool", description="Search the web")
        CapabilityRegistry.register("calc", "tool", description="Calculator")

        results = CapabilityRegistry.find("web")
        assert len(results) == 2
        names = {c.name for c in results}
        assert names == {"web_fetch", "web_search"}

    def test_find_by_type(self):
        CapabilityRegistry.register("a", "tool")
        CapabilityRegistry.register("b", "agent")
        CapabilityRegistry.register("c", "tool")

        results = CapabilityRegistry.find(capability_type="tool")
        assert len(results) == 2
        assert {c.name for c in results} == {"a", "c"}

    def test_find_by_tag(self):
        CapabilityRegistry.register("x", "tool", tags=("fast", "utility"))
        CapabilityRegistry.register("y", "tool", tags=("slow",))
        CapabilityRegistry.register("z", "tool", tags=("fast", "safe"))

        results = CapabilityRegistry.find(tag="fast")
        assert len(results) == 2
        assert {c.name for c in results} == {"x", "z"}

    def test_find_combined_filters(self):
        CapabilityRegistry.register("a", "tool", tags=("fast",), description="Alpha")
        CapabilityRegistry.register("b", "agent", tags=("fast",), description="Beta")
        CapabilityRegistry.register("c", "tool", tags=("slow",), description="Gamma")

        results = CapabilityRegistry.find("a", capability_type="tool", tag="fast")
        assert len(results) == 1
        assert results[0].name == "a"

    def test_find_sorted_by_name(self):
        CapabilityRegistry.register("zulu", "tool")
        CapabilityRegistry.register("alpha", "tool")
        CapabilityRegistry.register("mike", "tool")

        results = CapabilityRegistry.find(capability_type="tool")
        names = [c.name for c in results]
        assert names == ["alpha", "mike", "zulu"]

    def test_find_no_results(self):
        CapabilityRegistry.register("only", "tool")
        results = CapabilityRegistry.find("nonexistent")
        assert results == []

    def test_get_missing_raises(self):
        with pytest.raises(KeyError, match="No capability registered"):
            CapabilityRegistry.get("ghost")

    def test_get_entry(self):
        CapabilityRegistry.register("mytool", "tool", entry_point="MyToolClass")
        assert CapabilityRegistry.get_entry("mytool") == "MyToolClass"

    def test_clear(self):
        CapabilityRegistry.register("a", "tool")
        CapabilityRegistry.register("b", "agent")
        CapabilityRegistry.clear()
        assert CapabilityRegistry.discover() == []

    def test_register_multiple_types(self):
        CapabilityRegistry.register("x1", "tool")
        CapabilityRegistry.register("x2", "agent")
        CapabilityRegistry.register("x3", "plugin")
        CapabilityRegistry.register("x4", "prompt")
        CapabilityRegistry.register("x5", "workflow")
        CapabilityRegistry.register("x6", "provider")
        CapabilityRegistry.register("x7", "skill")

        assert len(CapabilityRegistry.discover()) == 7

    def test_permissions_as_list(self):
        cap = CapabilityRegistry.register(
            "net",
            "tool",
            permissions=["network.http", "filesystem.read"],
        )
        assert cap.permissions == ("network.http", "filesystem.read")

    def test_duplicate_register_raises(self):
        CapabilityRegistry.register("dup", "tool")
        with pytest.raises(ValueError, match="already has an entry"):
            CapabilityRegistry.register("dup", "tool")

    def test_find_case_insensitive(self):
        CapabilityRegistry.register("MyTool", "tool", description="A tool")
        results = CapabilityRegistry.find("mytool")
        assert len(results) == 1
        results_desc = CapabilityRegistry.find("a tool")
        assert len(results_desc) == 1
