"""
Modern color theme for the application with light/dark mode support.
"""

from typing import Dict


class ThemeColors:
    """Color definitions for a theme."""

    def __init__(self, colors: Dict[str, str]) -> None:
        for key, value in colors.items():
            setattr(self, key, value)


# Dark theme colors
DARK_THEME = {
    # Main colors
    "BG_PRIMARY": "#1a1a2e",      # Dark blue background
    "BG_SECONDARY": "#16213e",    # Slightly lighter background
    "BG_CARD": "#0f3460",         # Card background
    "BG_INPUT": "#1a1a2e",        # Input field background

    # Accent colors
    "ACCENT_PRIMARY": "#e94560",   # Red/Pink accent
    "ACCENT_SECONDARY": "#0f3460", # Blue accent
    "ACCENT_SUCCESS": "#00d9a5",   # Green for success
    "ACCENT_WARNING": "#ffc107",   # Yellow for warnings
    "ACCENT_ERROR": "#ff4757",     # Red for errors

    # Text colors
    "TEXT_PRIMARY": "#ffffff",     # White text
    "TEXT_SECONDARY": "#a0a0a0",   # Gray text
    "TEXT_MUTED": "#6c757d",       # Muted text

    # Border colors
    "BORDER_COLOR": "#2d3748",     # Border color
    "BORDER_FOCUS": "#e94560",     # Border on focus
    "BORDER_ERROR": "#ff4757",     # Border on error
    "BORDER_SUCCESS": "#00d9a5",   # Border on success

    # Button colors
    "BTN_PRIMARY_BG": "#e94560",
    "BTN_PRIMARY_FG": "#ffffff",
    "BTN_PRIMARY_HOVER": "#ff6b81",
    "BTN_SECONDARY_BG": "#0f3460",
    "BTN_SECONDARY_FG": "#ffffff",
    "BTN_SECONDARY_HOVER": "#1a4a7a",
    "BTN_DISABLED_BG": "#4a5568",
    "BTN_DISABLED_FG": "#718096",

    # Status colors
    "STATUS_IDLE": "#6c757d",
    "STATUS_RUNNING": "#0ea5e9",
    "STATUS_SUCCESS": "#00d9a5",
    "STATUS_ERROR": "#ff4757",

    # Icon colors
    "ICON_DEFAULT": "#6c757d",
    "ICON_HOVER": "#ffffff",
    "ICON_ACTIVE": "#e94560",
}

# Light theme colors
LIGHT_THEME = {
    # Main colors
    "BG_PRIMARY": "#f5f7fa",      # Light gray background
    "BG_SECONDARY": "#ffffff",    # White background
    "BG_CARD": "#ffffff",         # Card background
    "BG_INPUT": "#f8f9fa",        # Input field background

    # Accent colors
    "ACCENT_PRIMARY": "#e94560",   # Red/Pink accent
    "ACCENT_SECONDARY": "#3b82f6", # Blue accent
    "ACCENT_SUCCESS": "#10b981",   # Green for success
    "ACCENT_WARNING": "#f59e0b",   # Yellow for warnings
    "ACCENT_ERROR": "#ef4444",     # Red for errors

    # Text colors
    "TEXT_PRIMARY": "#1f2937",     # Dark gray text
    "TEXT_SECONDARY": "#6b7280",   # Medium gray text
    "TEXT_MUTED": "#9ca3af",       # Light gray text

    # Border colors
    "BORDER_COLOR": "#e5e7eb",     # Border color
    "BORDER_FOCUS": "#e94560",     # Border on focus
    "BORDER_ERROR": "#ef4444",     # Border on error
    "BORDER_SUCCESS": "#10b981",   # Border on success

    # Button colors
    "BTN_PRIMARY_BG": "#e94560",
    "BTN_PRIMARY_FG": "#ffffff",
    "BTN_PRIMARY_HOVER": "#ff6b81",
    "BTN_SECONDARY_BG": "#e5e7eb",
    "BTN_SECONDARY_FG": "#374151",
    "BTN_SECONDARY_HOVER": "#d1d5db",
    "BTN_DISABLED_BG": "#e5e7eb",
    "BTN_DISABLED_FG": "#9ca3af",

    # Status colors
    "STATUS_IDLE": "#9ca3af",
    "STATUS_RUNNING": "#3b82f6",
    "STATUS_SUCCESS": "#10b981",
    "STATUS_ERROR": "#ef4444",

    # Icon colors
    "ICON_DEFAULT": "#9ca3af",
    "ICON_HOVER": "#374151",
    "ICON_ACTIVE": "#e94560",
}


class Theme:
    """Modern color theme with light/dark mode support."""

    # Current theme mode
    _is_dark_mode: bool = True
    _colors: Dict[str, str] = DARK_THEME.copy()
    _observers: list = []

    # Font settings (constant across themes)
    FONT_FAMILY = "Segoe UI"
    FONT_SIZE_TITLE = 24
    FONT_SIZE_HEADING = 14
    FONT_SIZE_BODY = 11
    FONT_SIZE_SMALL = 9

    # Dynamic color properties
    @classmethod
    def _get_color(cls, name: str) -> str:
        return cls._colors.get(name, "#000000")

    # Main colors
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

    # Accent colors
    @classmethod
    @property
    def ACCENT_PRIMARY(cls) -> str:
        return cls._colors["ACCENT_PRIMARY"]

    @classmethod
    @property
    def ACCENT_SECONDARY(cls) -> str:
        return cls._colors["ACCENT_SECONDARY"]

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

    # Text colors
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

    # Border colors
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

    # Button colors
    @classmethod
    @property
    def BTN_PRIMARY_BG(cls) -> str:
        return cls._colors["BTN_PRIMARY_BG"]

    @classmethod
    @property
    def BTN_PRIMARY_FG(cls) -> str:
        return cls._colors["BTN_PRIMARY_FG"]

    @classmethod
    @property
    def BTN_PRIMARY_HOVER(cls) -> str:
        return cls._colors["BTN_PRIMARY_HOVER"]

    @classmethod
    @property
    def BTN_SECONDARY_BG(cls) -> str:
        return cls._colors["BTN_SECONDARY_BG"]

    @classmethod
    @property
    def BTN_SECONDARY_FG(cls) -> str:
        return cls._colors["BTN_SECONDARY_FG"]

    @classmethod
    @property
    def BTN_SECONDARY_HOVER(cls) -> str:
        return cls._colors["BTN_SECONDARY_HOVER"]

    @classmethod
    @property
    def BTN_DISABLED_BG(cls) -> str:
        return cls._colors["BTN_DISABLED_BG"]

    @classmethod
    @property
    def BTN_DISABLED_FG(cls) -> str:
        return cls._colors["BTN_DISABLED_FG"]

    # Status colors
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

    # Icon colors
    @classmethod
    @property
    def ICON_DEFAULT(cls) -> str:
        return cls._colors["ICON_DEFAULT"]

    @classmethod
    @property
    def ICON_HOVER(cls) -> str:
        return cls._colors["ICON_HOVER"]

    @classmethod
    @property
    def ICON_ACTIVE(cls) -> str:
        return cls._colors["ICON_ACTIVE"]

    @classmethod
    def is_dark_mode(cls) -> bool:
        """Check if dark mode is enabled."""
        return cls._is_dark_mode

    @classmethod
    def set_dark_mode(cls, enabled: bool) -> None:
        """Set dark or light mode."""
        cls._is_dark_mode = enabled
        cls._colors = DARK_THEME.copy() if enabled else LIGHT_THEME.copy()
        # Notify observers
        for callback in cls._observers:
            try:
                callback()
            except Exception:
                pass

    @classmethod
    def toggle_mode(cls) -> bool:
        """Toggle between dark and light mode. Returns new state."""
        cls.set_dark_mode(not cls._is_dark_mode)
        return cls._is_dark_mode

    @classmethod
    def add_observer(cls, callback) -> None:
        """Add a callback to be notified when theme changes."""
        if callback not in cls._observers:
            cls._observers.append(callback)

    @classmethod
    def remove_observer(cls, callback) -> None:
        """Remove a theme change observer."""
        if callback in cls._observers:
            cls._observers.remove(callback)

    @classmethod
    def get_color(cls, name: str) -> str:
        """Get a color by name."""
        return cls._colors.get(name, "#000000")
