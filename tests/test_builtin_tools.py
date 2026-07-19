"""Tests for built-in tools."""

import pytest

from aios.tools.builtin import CalculatorTool, DateTimeTool


class TestCalculatorTool:
    @pytest.fixture
    def calc(self):
        return CalculatorTool()

    @pytest.mark.asyncio
    async def test_basic_addition(self, calc):
        result = await calc.execute(expression="2+3")
        assert result.success is True
        assert result.content == "5"

    @pytest.mark.asyncio
    async def test_complex_expression(self, calc):
        result = await calc.execute(expression="sqrt(16) + pi")
        assert result.success is True
        assert result.content.startswith("7.14")

    @pytest.mark.asyncio
    async def test_trig_functions(self, calc):
        result = await calc.execute(expression="sin(0)")
        assert result.success is True
        assert result.content == "0.0"

    @pytest.mark.asyncio
    async def test_empty_expression(self, calc):
        result = await calc.execute(expression="")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_expression(self, calc):
        result = await calc.execute(expression="import os")
        assert result.success is False

    def test_spec(self):
        calc = CalculatorTool()
        assert calc.spec.name == "calculator"
        assert "expression" in calc.spec.parameters


class TestDateTimeTool:
    @pytest.fixture
    def dt(self):
        return DateTimeTool()

    @pytest.mark.asyncio
    async def test_now(self, dt):
        result = await dt.execute(action="now")
        assert result.success is True
        assert "T" in result.content  # ISO format contains T

    @pytest.mark.asyncio
    async def test_format(self, dt):
        result = await dt.execute(action="format", format="%Y")
        assert result.success is True
        assert len(result.content) == 4  # year is 4 digits

    @pytest.mark.asyncio
    async def test_unknown_action(self, dt):
        result = await dt.execute(action="unknown")
        assert result.success is False

    def test_spec(self):
        dt = DateTimeTool()
        assert dt.spec.name == "datetime"
        assert "action" in dt.spec.parameters
