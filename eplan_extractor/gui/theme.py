"""
Professional color theme with light/dark mode support.
"""

from typing import Dict


# Professional Dark theme - clean, minimal, corporate
DARK_THEME = {
    # Main backgrounds
    "BG_PRIMARY": "#111111",
    "BG_SECONDARY": "#1a1a1a",
    "BG_CARD": "#1e1e1e",
    "BG_INPUT": "#262626",

    # Accent - professional blue
    "ACCENT_PRIMARY": "#2563eb",
    "ACCENT_SECONDARY": "#1d4ed8",
    "ACCENT_SUCCESS": "#22c55e",
    "ACCENT_WARNING": "#f59e0b",
    "ACCENT_ERROR": "#ef4444",

    # Text
    "TEXT_PRIMARY": "#fafafa",
    "TEXT_SECONDARY": "#a3a3a3",
    "TEXT_MUTED": "#737373",

    # Borders
    "BORDER_COLOR": "#2e2e2e",
    "BORDER_FOCUS": "#2563eb",
    "BORDER_ERROR": "#ef4444",
    "BORDER_SUCCESS": "#22c55e",

    # Buttons
    "BTN_PRIMARY_BG": "#2563eb",
    "BTN_PRIMARY_FG": "#ffffff",
    "BTN_PRIMARY_HOVER": "#1d4ed8",
    "BTN_SECONDARY_BG": "#2e2e2e",
    "BTN_SECONDARY_FG": "#fafafa",
    "BTN_SECONDARY_HOVER": "#3d3d3d",
    "BTN_DISABLED_BG": "#1e1e1e",
    "BTN_DISABLED_FG": "#525252",

    # Status
    "STATUS_IDLE": "#737373",
    "STATUS_RUNNING": "#2563eb",
    "STATUS_SUCCESS": "#22c55e",
    "STATUS_ERROR": "#ef4444",

    # Icons
    "ICON_DEFAULT": "#737373",
    "ICON_HOVER": "#fafafa",
    "ICON_ACTIVE": "#2563eb",
}

# Professional Light theme
LIGHT_THEME = {
    # Main backgrounds
    "BG_PRIMARY": "#fafafa",
    "BG_SECONDARY": "#f5f5f5",
    "BG_CARD": "#ffffff",
    "BG_INPUT": "#ffffff",

    # Accent
    "ACCENT_PRIMARY": "#2563eb",
    "ACCENT_SECONDARY": "#1d4ed8",
    "ACCENT_SUCCESS": "#16a34a",
    "ACCENT_WARNING": "#d97706",
    "ACCENT_ERROR": "#dc2626",

    # Text
    "TEXT_PRIMARY": "#171717",
    "TEXT_SECONDARY": "#525252",
    "TEXT_MUTED": "#a3a3a3",

    # Borders
    "BORDER_COLOR": "#e5e5e5",
    "BORDER_FOCUS": "#2563eb",
    "BORDER_ERROR": "#dc2626",
    "BORDER_SUCCESS": "#16a34a",

    # Buttons
    "BTN_PRIMARY_BG": "#2563eb",
    "BTN_PRIMARY_FG": "#ffffff",
    "BTN_PRIMARY_HOVER": "#1d4ed8",
    "BTN_SECONDARY_BG": "#e5e5e5",
    "BTN_SECONDARY_FG": "#171717",
    "BTN_SECONDARY_HOVER": "#d4d4d4",
    "BTN_DISABLED_BG": "#f5f5f5",
    "BTN_DISABLED_FG": "#a3a3a3",

    # Status
    "STATUS_IDLE": "#a3a3a3",
    "STATUS_RUNNING": "#2563eb",
    "STATUS_SUCCESS": "#16a34a",
    "STATUS_ERROR": "#dc2626",

    # Icons
    "ICON_DEFAULT": "#a3a3a3",
    "ICON_HOVER": "#171717",
    "ICON_ACTIVE": "#2563eb",
}


class Theme:
    """Professional theme manager."""

    _is_dark_mode: bool = True
    _colors: Dict[str, str] = DARK_THEME.copy()
    _observers: list = []

    # Clean typography
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_TITLE = 18
    FONT_SIZE_HEADING = 12
    FONT_SIZE_BODY = 10
    FONT_SIZE_SMALL = 9

    @classmethod
    def is_dark_mode(cls) -> bool:
        return cls._is_dark_mode

    @classmethod
    def set_dark_mode(cls, enabled: bool) -> None:
        cls._is_dark_mode = enabled
        cls._colors = DARK_THEME.copy() if enabled else LIGHT_THEME.copy()
        for callback in cls._observers:
            try:
                callback()
            except Exception:
                pass

    @classmethod
    def toggle_mode(cls) -> bool:
        cls.set_dark_mode(not cls._is_dark_mode)
        return cls._is_dark_mode

    @classmethod
    def add_observer(cls, callback) -> None:
        if callback not in cls._observers:
            cls._observers.append(callback)

    @classmethod
    def remove_observer(cls, callback) -> None:
        if callback in cls._observers:
            cls._observers.remove(callback)

    @classmethod
    def get_color(cls, name: str) -> str:
        return cls._colors.get(name, "#000000")

    # Properties for direct access
    @classmethod
    @property
    def BG_PRIMARY(cls) -> str:
        return cls._colors["BG_PRIMARY"]

    @classmethod
    @property
    def BG_SECONDARY(cls) -> str:
        return cls._colors["BG_SECONDARY"]

    @classmethod
    @property
    def BG_CARD(cls) -> str:
        return cls._colors["BG_CARD"]

    @classmethod
    @property
    def BG_INPUT(cls) -> str:
        return cls._colors["BG_INPUT"]

    @classmethod
    @property
    def ACCENT_PRIMARY(cls) -> str:
        return cls._colors["ACCENT_PRIMARY"]

    @classmethod
    @property
    def ACCENT_SUCCESS(cls) -> str:
        return cls._colors["ACCENT_SUCCESS"]

    @classmethod
    @property
    def ACCENT_WARNING(cls) -> str:
        return cls._colors["ACCENT_WARNING"]

    @classmethod
    @property
    def ACCENT_ERROR(cls) -> str:
        return cls._colors["ACCENT_ERROR"]

    @classmethod
    @property
    def TEXT_PRIMARY(cls) -> str:
        return cls._colors["TEXT_PRIMARY"]

    @classmethod
    @property
    def TEXT_SECONDARY(cls) -> str:
        return cls._colors["TEXT_SECONDARY"]

    @classmethod
    @property
    def TEXT_MUTED(cls) -> str:
        return cls._colors["TEXT_MUTED"]

    @classmethod
    @property
    def BORDER_COLOR(cls) -> str:
        return cls._colors["BORDER_COLOR"]

    @classmethod
    @property
    def BORDER_FOCUS(cls) -> str:
        return cls._colors["BORDER_FOCUS"]

    @classmethod
    @property
    def BORDER_ERROR(cls) -> str:
        return cls._colors["BORDER_ERROR"]

    @classmethod
    @property
    def BORDER_SUCCESS(cls) -> str:
        return cls._colors["BORDER_SUCCESS"]

    @classmethod
    @property
    def STATUS_IDLE(cls) -> str:
        return cls._colors["STATUS_IDLE"]

    @classmethod
    @property
    def STATUS_RUNNING(cls) -> str:
        return cls._colors["STATUS_RUNNING"]

    @classmethod
    @property
    def STATUS_SUCCESS(cls) -> str:
        return cls._colors["STATUS_SUCCESS"]

    @classmethod
    @property
    def STATUS_ERROR(cls) -> str:
        return cls._colors["STATUS_ERROR"]
