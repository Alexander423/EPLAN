"""
Custom modern-styled widgets for the GUI.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from .theme import Theme


class Tooltip:
    """Creates a tooltip for a given widget."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tooltip_window: Optional[tk.Toplevel] = None
        self._schedule_id: Optional[str] = None

        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, event: tk.Event) -> None:
        """Schedule tooltip display."""
        self._schedule_id = self.widget.after(self.delay, self._show_tooltip)

    def _on_leave(self, event: tk.Event = None) -> None:
        """Cancel scheduled tooltip and hide if visible."""
        if self._schedule_id:
            self.widget.after_cancel(self._schedule_id)
            self._schedule_id = None
        self._hide_tooltip()

    def _show_tooltip(self) -> None:
        """Display the tooltip."""
        if self._tooltip_window:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self._tooltip_window = tk.Toplevel(self.widget)
        self._tooltip_window.wm_overrideredirect(True)
        self._tooltip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self._tooltip_window,
            text=self.text,
            bg="#333333",
            fg="#ffffff",
            relief="solid",
            borderwidth=1,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            padx=8,
            pady=4
        )
        label.pack()

    def _hide_tooltip(self) -> None:
        """Hide the tooltip."""
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None

    def update_text(self, text: str) -> None:
        """Update tooltip text."""
        self.text = text


class ModernEntry(tk.Frame):
    """Custom modern-styled entry widget with validation support."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "",
        show: str = "",
        textvariable: Optional[tk.StringVar] = None,
        tooltip: str = "",
        validate_func: Optional[Callable[[str], bool]] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._placeholder = placeholder
        self._show_char = show
        self._has_focus = False
        self._validate_func = validate_func
        self._is_valid: Optional[bool] = None
        self._textvariable = textvariable

        # Container frame with border effect
        self._container = tk.Frame(
            self,
            bg=Theme.get_color("BORDER_COLOR"),
            padx=1,
            pady=1
        )
        self._container.pack(fill="x", expand=True)

        # Inner frame
        self._inner = tk.Frame(self._container, bg=Theme.get_color("BG_INPUT"))
        self._inner.pack(fill="x", expand=True)

        # Entry widget
        self._entry = tk.Entry(
            self._inner,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            insertbackground=Theme.get_color("TEXT_PRIMARY"),
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

        if validate_func and textvariable:
            textvariable.trace_add("write", self._on_value_change)

        # Tooltip
        if tooltip:
            self._tooltip = Tooltip(self._entry, tooltip)

    def _show_placeholder(self) -> None:
        """Show placeholder text."""
        self._entry.config(fg=Theme.get_color("TEXT_MUTED"), show="")
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder)

    def _hide_placeholder(self) -> None:
        """Hide placeholder text."""
        self._entry.config(fg=Theme.get_color("TEXT_PRIMARY"), show=self._show_char)
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")

    def _on_focus_in(self, event: tk.Event) -> None:
        """Handle focus in event."""
        self._has_focus = True
        self._container.config(bg=Theme.get_color("BORDER_FOCUS"))
        if self._entry.get() == self._placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        """Handle focus out event."""
        self._has_focus = False
        self._update_border_color()
        if not self._entry.get():
            self._show_placeholder()

    def _on_value_change(self, *args) -> None:
        """Handle value changes for validation."""
        if self._validate_func and self._textvariable:
            value = self._textvariable.get()
            if value and value != self._placeholder:
                self._is_valid = self._validate_func(value)
                self._update_border_color()

    def _update_border_color(self) -> None:
        """Update border color based on state."""
        if self._has_focus:
            self._container.config(bg=Theme.get_color("BORDER_FOCUS"))
        elif self._is_valid is True:
            self._container.config(bg=Theme.get_color("BORDER_SUCCESS"))
        elif self._is_valid is False:
            self._container.config(bg=Theme.get_color("BORDER_ERROR"))
        else:
            self._container.config(bg=Theme.get_color("BORDER_COLOR"))

    def set_validation_state(self, is_valid: Optional[bool]) -> None:
        """Manually set validation state."""
        self._is_valid = is_valid
        self._update_border_color()

    def get(self) -> str:
        """Get entry value."""
        value = self._entry.get()
        return "" if value == self._placeholder else value


class PasswordEntry(tk.Frame):
    """Password entry widget with show/hide toggle."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "Enter password",
        textvariable: Optional[tk.StringVar] = None,
        tooltip: str = "",
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._placeholder = placeholder
        self._has_focus = False
        self._is_visible = False
        self._textvariable = textvariable

        # Container frame with border effect
        self._container = tk.Frame(
            self,
            bg=Theme.get_color("BORDER_COLOR"),
            padx=1,
            pady=1
        )
        self._container.pack(fill="x", expand=True)

        # Inner frame
        self._inner = tk.Frame(self._container, bg=Theme.get_color("BG_INPUT"))
        self._inner.pack(fill="x", expand=True)

        # Entry widget
        self._entry = tk.Entry(
            self._inner,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            insertbackground=Theme.get_color("TEXT_PRIMARY"),
            relief="flat",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY),
            textvariable=textvariable,
            show="●",
            **kwargs
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(12, 0), pady=10)

        # Toggle visibility button (eye icon)
        self._toggle_btn = tk.Label(
            self._inner,
            text="👁",
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("ICON_DEFAULT"),
            font=(Theme.FONT_FAMILY, 12),
            cursor="hand2"
        )
        self._toggle_btn.pack(side="right", padx=(5, 12), pady=10)

        # Bindings
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._toggle_btn.bind("<Button-1>", self._toggle_visibility)
        self._toggle_btn.bind("<Enter>", self._on_toggle_enter)
        self._toggle_btn.bind("<Leave>", self._on_toggle_leave)

        # Placeholder handling
        if placeholder and textvariable and not textvariable.get():
            self._show_placeholder()

        # Tooltip
        if tooltip:
            self._tooltip = Tooltip(self._entry, tooltip)
        self._toggle_tooltip = Tooltip(self._toggle_btn, "Show/Hide Password")

    def _show_placeholder(self) -> None:
        """Show placeholder text."""
        self._entry.config(fg=Theme.get_color("TEXT_MUTED"), show="")
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder)

    def _hide_placeholder(self) -> None:
        """Hide placeholder text."""
        self._entry.config(fg=Theme.get_color("TEXT_PRIMARY"))
        if not self._is_visible:
            self._entry.config(show="●")
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")

    def _on_focus_in(self, event: tk.Event) -> None:
        """Handle focus in event."""
        self._has_focus = True
        self._container.config(bg=Theme.get_color("BORDER_FOCUS"))
        if self._entry.get() == self._placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        """Handle focus out event."""
        self._has_focus = False
        self._container.config(bg=Theme.get_color("BORDER_COLOR"))
        if not self._entry.get():
            self._show_placeholder()

    def _toggle_visibility(self, event: tk.Event) -> None:
        """Toggle password visibility."""
        self._is_visible = not self._is_visible
        current_value = self._entry.get()

        if current_value == self._placeholder:
            return

        if self._is_visible:
            self._entry.config(show="")
            self._toggle_btn.config(text="🙈", fg=Theme.get_color("ICON_ACTIVE"))
        else:
            self._entry.config(show="●")
            self._toggle_btn.config(text="👁", fg=Theme.get_color("ICON_DEFAULT"))

    def _on_toggle_enter(self, event: tk.Event) -> None:
        """Handle mouse enter on toggle button."""
        if not self._is_visible:
            self._toggle_btn.config(fg=Theme.get_color("ICON_HOVER"))

    def _on_toggle_leave(self, event: tk.Event) -> None:
        """Handle mouse leave on toggle button."""
        if not self._is_visible:
            self._toggle_btn.config(fg=Theme.get_color("ICON_DEFAULT"))

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
        tooltip: str = "",
        **kwargs
    ) -> None:
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=Theme.get_color("BG_CARD"),
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

        # Colors based on style
        self._update_colors()
        self._draw()

        # Bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        # Tooltip
        if tooltip:
            self._tooltip = Tooltip(self, tooltip)

    def _update_colors(self) -> None:
        """Update colors based on style and theme."""
        if self._primary:
            self._bg = Theme.get_color("BTN_PRIMARY_BG")
            self._fg = Theme.get_color("BTN_PRIMARY_FG")
            self._hover_bg = Theme.get_color("BTN_PRIMARY_HOVER")
        else:
            self._bg = Theme.get_color("BTN_SECONDARY_BG")
            self._fg = Theme.get_color("BTN_SECONDARY_FG")
            self._hover_bg = Theme.get_color("BTN_SECONDARY_HOVER")

    def _draw(self) -> None:
        """Draw the button."""
        self.delete("all")

        bg = self._bg if self._enabled else Theme.get_color("BTN_DISABLED_BG")
        fg = self._fg if self._enabled else Theme.get_color("BTN_DISABLED_FG")

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
        tooltip: str = "",
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._variable = variable or tk.BooleanVar()
        self._text = text

        # Checkbox canvas
        self._canvas = tk.Canvas(
            self,
            width=20,
            height=20,
            bg=Theme.get_color("BG_CARD"),
            highlightthickness=0
        )
        self._canvas.pack(side="left", padx=(0, 8))

        # Label
        self._label = tk.Label(
            self,
            text=text,
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        )
        self._label.pack(side="left")

        self._draw()

        # Bindings
        self._canvas.bind("<Button-1>", self._toggle)
        self._label.bind("<Button-1>", self._toggle)
        self._variable.trace_add("write", lambda *args: self._draw())

        # Tooltip
        if tooltip:
            self._tooltip = Tooltip(self, tooltip)

    def _draw(self) -> None:
        """Draw the checkbox."""
        self._canvas.delete("all")

        # Draw box
        self._canvas.create_rectangle(
            2, 2, 18, 18,
            outline=Theme.get_color("BORDER_COLOR"),
            fill=Theme.get_color("BG_INPUT"),
            width=2
        )

        # Draw checkmark if checked
        if self._variable.get():
            self._canvas.create_rectangle(
                2, 2, 18, 18,
                outline=Theme.get_color("ACCENT_PRIMARY"),
                fill=Theme.get_color("ACCENT_PRIMARY"),
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


class ThemeToggle(tk.Frame):
    """Toggle switch for dark/light theme."""

    def __init__(
        self,
        parent: tk.Widget,
        command: Optional[Callable[[bool], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._command = command
        self._is_dark = Theme.is_dark_mode()

        # Label
        self._label = tk.Label(
            self,
            text="Dark Mode",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        )
        self._label.pack(side="left", padx=(0, 10))

        # Toggle canvas
        self._canvas = tk.Canvas(
            self,
            width=50,
            height=26,
            bg=Theme.get_color("BG_CARD"),
            highlightthickness=0
        )
        self._canvas.pack(side="left")

        self._draw()

        # Bindings
        self._canvas.bind("<Button-1>", self._toggle)
        self._label.bind("<Button-1>", self._toggle)

        # Tooltip
        self._tooltip = Tooltip(self._canvas, "Toggle Dark/Light Mode")

    def _draw(self) -> None:
        """Draw the toggle switch."""
        self._canvas.delete("all")

        # Background track
        if self._is_dark:
            track_color = Theme.get_color("ACCENT_PRIMARY")
        else:
            track_color = Theme.get_color("BORDER_COLOR")

        # Draw rounded track
        self._canvas.create_oval(0, 0, 26, 26, fill=track_color, outline="")
        self._canvas.create_oval(24, 0, 50, 26, fill=track_color, outline="")
        self._canvas.create_rectangle(13, 0, 37, 26, fill=track_color, outline="")

        # Draw knob
        if self._is_dark:
            knob_x = 27
        else:
            knob_x = 3

        self._canvas.create_oval(
            knob_x, 3, knob_x + 20, 23,
            fill="#ffffff",
            outline=""
        )

        # Sun/Moon icon
        if self._is_dark:
            self._canvas.create_text(
                knob_x + 10, 13,
                text="🌙",
                font=(Theme.FONT_FAMILY, 8)
            )
        else:
            self._canvas.create_text(
                knob_x + 10, 13,
                text="☀",
                font=(Theme.FONT_FAMILY, 10)
            )

    def _toggle(self, event: tk.Event) -> None:
        """Toggle the theme."""
        self._is_dark = not self._is_dark
        self._draw()

        if self._command:
            self._command(self._is_dark)

    def set_state(self, is_dark: bool) -> None:
        """Set the toggle state."""
        self._is_dark = is_dark
        self._draw()


class IconButton(tk.Label):
    """Simple icon button."""

    def __init__(
        self,
        parent: tk.Widget,
        icon: str,
        command: Optional[Callable] = None,
        tooltip: str = "",
        size: int = 16,
        **kwargs
    ) -> None:
        super().__init__(
            parent,
            text=icon,
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("ICON_DEFAULT"),
            font=(Theme.FONT_FAMILY, size),
            cursor="hand2",
            **kwargs
        )

        self._command = command
        self._icon = icon

        # Bindings
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        # Tooltip
        if tooltip:
            self._tooltip = Tooltip(self, tooltip)

    def _on_enter(self, event: tk.Event) -> None:
        """Handle mouse enter."""
        self.config(fg=Theme.get_color("ICON_HOVER"))

    def _on_leave(self, event: tk.Event) -> None:
        """Handle mouse leave."""
        self.config(fg=Theme.get_color("ICON_DEFAULT"))

    def _on_click(self, event: tk.Event) -> None:
        """Handle click event."""
        if self._command:
            self._command()
