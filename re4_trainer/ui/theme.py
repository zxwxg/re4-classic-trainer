"""Colour palettes, fonts and metrics for the trainer UI.

The palette can be switched while the app runs: :data:`COLORS` is a single dict
that every module shares, so :func:`apply_palette` updates the colours in place
and the window only has to rebuild its widgets.
"""

from __future__ import annotations

from typing import Dict

import customtkinter as ctk

# Every palette needs exactly the same keys.
_BASE_KEYS = (
    "bg", "bg_soft", "panel", "panel_alt", "panel_hover", "border", "border_soft",
    "text", "text_dim", "text_faint",
    "accent", "accent_hover", "accent_border", "accent_soft", "nav_active",
    "gold", "green", "green_soft", "amber", "amber_soft", "amber_border",
    "red", "blue", "selected",
)

PALETTES: Dict[str, Dict[str, str]] = {
    # ---------------------------------------------------------------- neon blue
    "neon": {
        "bg": "#05070D",
        "bg_soft": "#0A0E16",
        "panel": "#0E131D",
        "panel_alt": "#141A27",
        "panel_hover": "#1B2434",
        "border": "#1F2838",
        "border_soft": "#171E2B",
        "text": "#F0F4FA",
        "text_dim": "#93A0B4",
        "text_faint": "#5A6577",
        "accent": "#22B8F0",
        "accent_hover": "#3FC8FF",
        "accent_border": "#1791C4",
        "accent_soft": "#0C2734",
        "nav_active": "#0B1A24",
        "gold": "#E8C27A",
        "green": "#41C68C",
        "green_soft": "#12301F",
        "amber": "#E3AC4F",
        "amber_soft": "#2E2611",
        "amber_border": "#6B5323",
        "red": "#E5484D",
        "blue": "#5B8DEF",
        "selected": "#0D1C26",
    },
    # ------------------------------------------------------------- crimson (RE4)
    "crimson": {
        "bg": "#07080B",
        "bg_soft": "#0C0E13",
        "panel": "#111419",
        "panel_alt": "#171B23",
        "panel_hover": "#1F2530",
        "border": "#242C38",
        "border_soft": "#1A202A",
        "text": "#F1F3F7",
        "text_dim": "#96A0B0",
        "text_faint": "#5C6675",
        "accent": "#D93B31",
        "accent_hover": "#EA5049",
        "accent_border": "#B62C25",
        "accent_soft": "#2B1414",
        "nav_active": "#1B1315",
        "gold": "#E8C27A",
        "green": "#41C68C",
        "green_soft": "#12301F",
        "amber": "#E3AC4F",
        "amber_soft": "#2E2611",
        "amber_border": "#6B5323",
        "red": "#E5484D",
        "blue": "#5B8DEF",
        "selected": "#1E1518",
    },
    # ------------------------------------------------------------ violet / purple
    "violet": {
        "bg": "#08060F",
        "bg_soft": "#0E0B1A",
        "panel": "#130F22",
        "panel_alt": "#1A1530",
        "panel_hover": "#231C40",
        "border": "#2A2247",
        "border_soft": "#1E1836",
        "text": "#F2F0FA",
        "text_dim": "#A79FC2",
        "text_faint": "#6A6288",
        "accent": "#8B5CF6",
        "accent_hover": "#A78BFA",
        "accent_border": "#6D3FD6",
        "accent_soft": "#221645",
        "nav_active": "#1B1236",
        "gold": "#E8C27A",
        "green": "#41C68C",
        "green_soft": "#12301F",
        "amber": "#E3AC4F",
        "amber_soft": "#2E2611",
        "amber_border": "#6B5323",
        "red": "#E5484D",
        "blue": "#5B8DEF",
        "selected": "#1E1540",
    },
    # --------------------------------------------------------------- toxic green
    "toxic": {
        "bg": "#04090A",
        "bg_soft": "#081213",
        "panel": "#0B1718",
        "panel_alt": "#112021",
        "panel_hover": "#162A2B",
        "border": "#1C3233",
        "border_soft": "#132526",
        "text": "#EEF7F4",
        "text_dim": "#8FB3AB",
        "text_faint": "#577A73",
        "accent": "#10B981",
        "accent_hover": "#34D399",
        "accent_border": "#0C8C62",
        "accent_soft": "#0A2A20",
        "nav_active": "#08241C",
        "gold": "#E8C27A",
        "green": "#41C68C",
        "green_soft": "#12301F",
        "amber": "#E3AC4F",
        "amber_soft": "#2E2611",
        "amber_border": "#6B5323",
        "red": "#E5484D",
        "blue": "#5B8DEF",
        "selected": "#0B2A21",
    },
    # --------------------------------------------------------------- amber/gold
    "amber": {
        "bg": "#0A0805",
        "bg_soft": "#12100A",
        "panel": "#17140D",
        "panel_alt": "#201B12",
        "panel_hover": "#2A2418",
        "border": "#332B1C",
        "border_soft": "#261F14",
        "text": "#F8F4EC",
        "text_dim": "#B8AC93",
        "text_faint": "#7A7159",
        "accent": "#E0A24C",
        "accent_hover": "#F0B860",
        "accent_border": "#B27F35",
        "accent_soft": "#2E2410",
        "nav_active": "#241C0E",
        "gold": "#E8C27A",
        "green": "#41C68C",
        "green_soft": "#12301F",
        "amber": "#E3AC4F",
        "amber_soft": "#2E2611",
        "amber_border": "#6B5323",
        "red": "#E5484D",
        "blue": "#5B8DEF",
        "selected": "#2A2110",
    },
}

PALETTE_LABELS: Dict[str, str] = {
    "neon": "Neon blue",
    "crimson": "Crimson red",
    "violet": "Violet",
    "toxic": "Toxic green",
    "amber": "Amber gold",
}

DEFAULT_PALETTE = "neon"

COLORS: Dict[str, str] = dict(PALETTES[DEFAULT_PALETTE])


def apply_palette(name: str) -> str:
    """Switch the shared colour dict in place. Returns the palette actually used."""
    key = name if name in PALETTES else DEFAULT_PALETTE
    payload = PALETTES[key]
    for field in _BASE_KEYS:
        COLORS[field] = payload[field]
    return key


RADIUS = 14
RADIUS_SM = 9
PAD = 18
GAP = 12

FONT_FAMILY = "Segoe UI"
FONT_SEMI = "Segoe UI Semibold"
FONT_GLYPHS = "Segoe UI Symbol"
# Windows ships these icon fonts; "Segoe Fluent Icons" is the Windows 11 set and
# "Segoe MDL2 Assets" is the Windows 10 set (same code points for our icons).
ICON_FONT = "Segoe Fluent Icons"
ICON_FONT_FALLBACK = "Segoe MDL2 Assets"

WINDOW_TITLE = "RE4 Classic Trainer  ·  DULE SERVER"
WINDOW_SIZE = "1180x840"

# Segoe MDL2 / Fluent icon code points.
ICONS = {
    "home": "\uE80F",
    "skins": "\uE716",
    "save": "\uE74E",
    "bolt": "\uE945",
    "shield": "\uEA18",
    "heart": "\uEB51",
    "folder": "\uE8B7",
    "reload": "\uE72C",
    "check": "\uE73E",
    "cross": "\uE711",
    "dot": "\uEA3B",
    "brush": "\uE790",
    "people": "\uE716",
    "download": "\uE896",
    "chevron": "\uE76C",
    "settings": "\uE713",
    "info": "\uE946",
    "warning": "\uE7BA",
    "error": "\uE783",
    "delete": "\uE74D",
    "edit": "\uE70F",
    "add": "\uE710",
    "play": "\uE768",
    "power": "\uE7E8",
    "lock": "\uE72E",
    "globe": "\uE774",
    "clock": "\uE823",
    "star": "\uE735",
    "zoom": "\uE8A3",
    "game": "\uE7FC",
}


def font(size: int = 13, weight: str = "normal", family: str = FONT_FAMILY) -> ctk.CTkFont:
    return ctk.CTkFont(family=family, size=size, weight=weight)


FONT_H1 = lambda: font(23, "bold", FONT_SEMI)        # noqa: E731  page title
FONT_H2 = lambda: font(15, "bold", FONT_SEMI)        # noqa: E731  card title
FONT_BODY = lambda: font(13)                          # noqa: E731
FONT_BODY_BOLD = lambda: font(13, "bold")             # noqa: E731
FONT_SMALL = lambda: font(11)                         # noqa: E731
FONT_SMALL_BOLD = lambda: font(11, "bold")            # noqa: E731
FONT_TINY = lambda: font(10)                          # noqa: E731
FONT_MONO = lambda: ctk.CTkFont(family="Consolas", size=11)  # noqa: E731
FONT_NUM = lambda: font(21, "bold", FONT_SEMI)        # noqa: E731
FONT_GLYPH = lambda: font(13, "normal", ICON_FONT)    # noqa: E731
FONT_GLYPH_BIG = lambda: font(17, "normal", ICON_FONT)  # noqa: E731
FONT_GLYPH_NAV = lambda: font(16, "normal", ICON_FONT)  # noqa: E731


def apply_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
