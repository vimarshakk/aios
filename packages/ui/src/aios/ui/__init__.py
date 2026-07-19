"""AIOS UI — shared design system tokens and component utilities.

This package provides Python-side design tokens, color palettes, spacing scales,
and type helpers that are consumed by the web frontend via code generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ColorToken:
    """A named color with light and dark variants."""
    name: str
    light: str
    dark: str
    alpha: str = ""


@dataclass(frozen=True)
class SpacingToken:
    """Spacing scale value."""
    name: str
    value: str  # e.g. "4px", "1rem"


@dataclass(frozen=True)
class TypeToken:
    """Typography scale entry."""
    name: str
    font_family: str
    font_size: str
    font_weight: int
    line_height: str
    letter_spacing: str = "0em"


# ---------------------------------------------------------------------------
# Color palette — iOS-inspired clinical design system
# ---------------------------------------------------------------------------

COLORS: list[ColorToken] = [
    ColorToken(name="accent",       light="#007AFF", dark="#0A84FF"),
    ColorToken(name="success",      light="#34C759", dark="#30D158"),
    ColorToken(name="warning",      light="#FF9500", dark="#FF9F0A"),
    ColorToken(name="danger",       light="#FF3B30", dark="#FF453A"),
    ColorToken(name="muted",        light="#8E8E93", dark="#8E8E93"),
    ColorToken(name="surface",      light="#FFFFFF", dark="#1C1C1E"),
    ColorToken(name="background",   light="#F2F2F7", dark="#000000"),
    ColorToken(name="text-primary", light="#1C1C1E", dark="#FFFFFF"),
    ColorToken(name="text-secondary", light="#3C3C43", dark="#EBEBF5"),
]

COLOR_MAP: dict[str, dict[str, str]] = {
    c.name: {"light": c.light, "dark": c.dark} for c in COLORS
}


# ---------------------------------------------------------------------------
# Spacing scale (4px base)
# ---------------------------------------------------------------------------

SPACING: list[SpacingToken] = [
    SpacingToken(name="0",   value="0px"),
    SpacingToken(name="1",   value="4px"),
    SpacingToken(name="2",   value="8px"),
    SpacingToken(name="3",   value="12px"),
    SpacingToken(name="4",   value="16px"),
    SpacingToken(name="5",   value="20px"),
    SpacingToken(name="6",   value="24px"),
    SpacingToken(name="8",   value="32px"),
    SpacingToken(name="10",  value="40px"),
    SpacingToken(name="12",  value="48px"),
    SpacingToken(name="16",  value="64px"),
    SpacingToken(name="20",  value="80px"),
]

SPACING_MAP: dict[str, str] = {s.name: s.value for s in SPACING}


# ---------------------------------------------------------------------------
# Typography scale
# ---------------------------------------------------------------------------

FONT_FAMILY = {
    "sans": "Inter, -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
    "mono": "SF Mono, JetBrains Mono, Consolas, monospace",
}

TYPOGRAPHY: list[TypeToken] = [
    TypeToken("h1", "sans", "34px", 700, "41px", "-0.02em"),
    TypeToken("h2", "sans", "28px", 700, "34px", "-0.01em"),
    TypeToken("h3", "sans", "22px", 600, "28px"),
    TypeToken("body", "sans", "17px", 400, "22px"),
    TypeToken("body-sm", "sans", "15px", 400, "20px"),
    TypeToken("caption", "sans", "13px", 400, "18px"),
    TypeToken("mono", "mono", "14px", 400, "20px"),
]


def export_tokens_json() -> dict[str, Any]:
    """Export all design tokens as a JSON-serializable dict."""
    return {
        "colors": COLOR_MAP,
        "spacing": SPACING_MAP,
        "fontFamilies": FONT_FAMILY,
        "typography": [
            {
                "name": t.name,
                "fontFamily": FONT_FAMILY[t.font_family],
                "fontSize": t.font_size,
                "fontWeight": t.font_weight,
                "lineHeight": t.line_height,
                "letterSpacing": t.letter_spacing,
            }
            for t in TYPOGRAPHY
        ],
    }
