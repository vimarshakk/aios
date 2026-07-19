"""Tests for aios.prompts — composable prompt templates."""

from __future__ import annotations

import pytest

from aios.prompts import (
    PromptLibrary,
    PromptPart,
    PromptRole,
    PromptTemplate,
    PromptVersion,
    coder_prompt,
    default_library,
    planner_prompt,
    research_prompt,
    reviewer_prompt,
    system_prompt,
)


class TestPromptTemplate:
    def test_render_substitutes(self) -> None:
        tpl = PromptTemplate(
            name="t",
            parts=(PromptPart(name="p", body="Hello {name}, you are {role}."),),
            variables=("name", "role"),
        )
        out = tpl.render(name="Ada", role="engineer")
        assert out == "Hello Ada, you are engineer."

    def test_missing_variable_raises(self) -> None:
        tpl = PromptTemplate(
            name="t",
            parts=(PromptPart(name="p", body="{x}"),),
            variables=("x",),
        )
        with pytest.raises(KeyError, match="x"):
            tpl.render()

    def test_render_map(self) -> None:
        tpl = PromptTemplate(
            name="t",
            parts=(PromptPart(name="p", body="{a}-{b}"),),
            variables=("a", "b"),
        )
        assert tpl.render_map({"a": "1", "b": "2"}) == "1-2"


class TestPromptLibrary:
    def test_build_and_render(self) -> None:
        lib = PromptLibrary()
        lib.register_part(PromptPart(name="role", body="You are {role}."))
        tpl = lib.build("task", ["role"], variables=["role"])
        assert lib.get_template("task") is tpl
        out = lib.render("task", role="helper")
        assert out == "You are helper."

    def test_unknown_part_raises(self) -> None:
        lib = PromptLibrary()
        with pytest.raises(KeyError, match="missing"):
            lib.build("x", ["missing"])

    def test_unknown_template_render_raises(self) -> None:
        lib = PromptLibrary()
        with pytest.raises(KeyError, match="nope"):
            lib.render("nope", foo="bar")


class TestDefaultLibrary:
    def test_agent_task(self) -> None:
        lib = default_library()
        out = lib.render(
            "agent_task",
            role="a planner",
            objective="Plan the migration",
            context="Legacy system on-prem.",
            constraints="Minimize downtime.",
            format="Markdown checklist.",
        )
        assert "You are a planner." in out
        assert "Objective: Plan the migration" in out
        assert "Constraints:" in out

    def test_code_review(self) -> None:
        lib = default_library()
        out = lib.render(
            "code_review",
            language="Python",
            code="def f(x): return x + 1",
        )
        assert "senior Python code reviewer" in out
        assert "def f(x)" in out

    def test_has_builtins(self) -> None:
        lib = default_library()
        assert "agent_task" in lib.template_names
        assert "code_review" in lib.template_names


class TestPromptRoleTemplates:
    @pytest.mark.parametrize(
        ("builder", "var"),
        [
            (planner_prompt, "goal"),
            (coder_prompt, "task"),
            (reviewer_prompt, "diff"),
            (research_prompt, "question"),
            (system_prompt, "agent_name"),
        ],
    )
    def test_role_template_registered_and_renders(self, builder, var) -> None:
        lib = default_library()
        tpl = builder()
        assert lib.get_template(tpl.name) is not None
        assert tpl.name.startswith("role_")
        values = {var: "sample", "context": "c", "sources": "s", "rules": "r"}
        out = tpl.render(**values)
        assert out  # non-empty

    def test_planner_role_output(self) -> None:
        out = planner_prompt().render(goal="Ship feature X")
        assert "feature X" in out
        assert "planner" in out

    def test_all_roles_present_in_enum(self) -> None:
        assert {r.value for r in PromptRole} == {
            "planner",
            "coder",
            "reviewer",
            "research",
            "system",
        }


class TestPromptVersion:
    def test_semver_ordering(self) -> None:
        assert PromptVersion("1.0.0") < PromptVersion("1.0.1")
        assert PromptVersion("1.9.0") < PromptVersion("2.0.0")

    def test_equality_by_value(self) -> None:
        assert PromptVersion("1.0.0") == PromptVersion("1.0.0")

    def test_changelog_field(self) -> None:
        v = PromptVersion("2.1.0", changelog="added constraints part")
        assert v.changelog == "added constraints part"
