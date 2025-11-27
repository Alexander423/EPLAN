"""
Custom modern-styled widgets for the GUI.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from .theme import Theme


class ModernEntry(tk.Frame):
    """Custom modern-styled entry widget."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "",
        show: str = "",
        textvariable: Optional[tk.StringVar] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.BG_CARD)

        self._placeholder = placeholder
        self._show_char = show
        self._has_focus = False

        # Container frame with border effect
        self._container = tk.Frame(
            self,
            bg=Theme.BORDER_COLOR,
            padx=1,
            pady=1
        )
        self._container.pack(fill="x", expand=True)

        # Inner frame
        self._inner = tk.Frame(self._container, bg=Theme.BG_INPUT)
        self._inner.pack(fill="x", expand=True)

        # Entry widget
        self._entry = tk.Entry(
            self._inner,
            bg=Theme.BG_INPUT,
            fg=Theme.TEXT_PRIMARY,
            insertbackground=Theme.TEXT_PRIMARY,
            relief="flat",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY),
            textvariable=textvariable,
            show=show,
            **kwargs
        )
        self._entry.pack(fill="x", padx=12, pady=10)

        # Placeholder handling
        if placeholder and textvariable and not textvariable.get():
            self._show_placeholder()

        # Bindings
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self) -> None:
        """Show placeholder text."""
        self._entry.config(fg=Theme.TEXT_MUTED, show="")
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder)

    def _hide_placeholder(self) -> None:
        """Hide placeholder text."""
        self._entry.config(fg=Theme.TEXT_PRIMARY, show=self._show_char)
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")

    def _on_focus_in(self, event: tk.Event) -> None:
        """Handle focus in event."""
        self._has_focus = True
        self._container.config(bg=Theme.BORDER_FOCUS)
        if self._entry.get() == self._placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        """Handle focus out event."""
        self._has_focus = False
        self._container.config(bg=Theme.BORDER_COLOR)
        if not self._entry.get():
            self._show_placeholder()

    def get(self) -> str:
        """Get entry value."""
        value = self._entry.get()
        return "" if value == self._placeholder else value


class ModernButton(tk.Canvas):
    """Custom modern-styled button widget."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        command: Optional[Callable] = None,
        primary: bool = True,
        width: int = 140,
        height: int = 42,
        **kwargs
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=Theme.BG_CARD,
            highlightthickness=0,
            **kwargs
        )

        self._text = text
        self._command = command
        self._primary = primary
        self._width = width
        self._height = height
        self._enabled = True
        self._hovered = False

        # Colors
        if primary:
            self._bg = Theme.BTN_PRIMARY_BG
            self._fg = Theme.BTN_PRIMARY_FG
            self._hover_bg = "#ff6b81"
        else:
            self._bg = Theme.BTN_SECONDARY_BG
            self._fg = Theme.BTN_SECONDARY_FG
            self._hover_bg = "#1a4a7a"

        self._draw()

        # Bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self) -> None:
        """Draw the button."""
        self.delete("all")

        bg = self._bg if self._enabled else Theme.BTN_DISABLED_BG
        fg = self._fg if self._enabled else Theme.BTN_DISABLED_FG

        if self._hovered and self._enabled:
            bg = self._hover_bg

        # Draw rounded rectangle
        radius = 8
        self._round_rectangle(
            2, 2, self._width - 2, self._height - 2,
            radius=radius,
            fill=bg,
            outline=""
        )

        # Draw text
        self.create_text(
            self._width // 2,
            self._height // 2,
            text=self._text,
            fill=fg,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        )

    def _round_rectangle(
        self,
        x1: int, y1: int, x2: int, y2: int,
        radius: int = 10,
        **kwargs
    ) -> int:
        """Draw a rounded rectangle."""
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_enter(self, event: tk.Event) -> None:
        """Handle mouse enter."""
        if self._enabled:
            self._hovered = True
            self._draw()
            self.config(cursor="hand2")

    def _on_leave(self, event: tk.Event) -> None:
        """Handle mouse leave."""
        self._hovered = False
        self._draw()
        self.config(cursor="")

    def _on_click(self, event: tk.Event) -> None:
        """Handle click event."""
        if self._enabled and self._command:
            self._command()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the button."""
        self._enabled = enabled
        self._draw()

    def set_text(self, text: str) -> None:
        """Set button text."""
        self._text = text
        self._draw()


class ModernCheckbox(tk.Frame):
    """Custom modern-styled checkbox widget."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        variable: Optional[tk.BooleanVar] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.BG_CARD)

        self._variable = variable or tk.BooleanVar()
        self._text = text

        # Checkbox canvas
        self._canvas = tk.Canvas(
            self,
            width=20,
            height=20,
            bg=Theme.BG_CARD,
            highlightthickness=0
        )
        self._canvas.pack(side="left", padx=(0, 8))

        # Label
        self._label = tk.Label(
            self,
            text=text,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        )
        self._label.pack(side="left")

        self._draw()

        # Bindings
        self._canvas.bind("<Button-1>", self._toggle)
        self._label.bind("<Button-1>", self._toggle)
        self._variable.trace_add("write", lambda *args: self._draw())

    def _draw(self) -> None:
        """Draw the checkbox."""
        self._canvas.delete("all")

        # Draw box
        self._canvas.create_rectangle(
            2, 2, 18, 18,
            outline=Theme.BORDER_COLOR,
            fill=Theme.BG_INPUT,
            width=2
        )

        # Draw checkmark if checked
        if self._variable.get():
            self._canvas.create_rectangle(
                2, 2, 18, 18,
                outline=Theme.ACCENT_PRIMARY,
                fill=Theme.ACCENT_PRIMARY,
                width=2
            )
            # Checkmark
            self._canvas.create_line(
                6, 10, 9, 14, 14, 6,
                fill="white",
                width=2,
                capstyle="round",
                joinstyle="round"
            )

    def _toggle(self, event: tk.Event) -> None:
        """Toggle the checkbox."""
        self._variable.set(not self._variable.get())
