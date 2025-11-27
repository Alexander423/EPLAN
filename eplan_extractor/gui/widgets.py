"""
Clean, professional widgets for the GUI.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from .theme import Theme


class Tooltip:
    """Simple tooltip for widgets."""

    def __init__(self, widget: tk.Widget, text: str, delay: int = 500) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        self._window: Optional[tk.Toplevel] = None
        self._id: Optional[str] = None

        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event: tk.Event) -> None:
        self._id = self.widget.after(self.delay, self._show)

    def _hide(self, event: tk.Event = None) -> None:
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self._window:
            self._window.destroy()
            self._window = None

    def _show(self) -> None:
        if self._window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5

        self._window = tk.Toplevel(self.widget)
        self._window.wm_overrideredirect(True)
        self._window.wm_geometry(f"+{x}+{y}")

        tk.Label(
            self._window,
            text=self.text,
            bg="#333",
            fg="#fff",
            relief="flat",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            padx=8,
            pady=4
        ).pack()

    def update_text(self, text: str) -> None:
        self.text = text


class ModernEntry(tk.Frame):
    """Clean entry field with border styling."""

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

        # Border container
        self._border = tk.Frame(self, bg=Theme.get_color("BORDER_COLOR"), padx=1, pady=1)
        self._border.pack(fill="x", expand=True)

        # Inner container
        self._inner = tk.Frame(self._border, bg=Theme.get_color("BG_INPUT"))
        self._inner.pack(fill="x", expand=True)

        # Entry
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
        self._entry.pack(fill="x", padx=10, pady=8)

        if placeholder and textvariable and not textvariable.get():
            self._show_placeholder()

        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)

        if validate_func and textvariable:
            textvariable.trace_add("write", self._on_change)

        if tooltip:
            Tooltip(self._entry, tooltip)

    def _show_placeholder(self) -> None:
        self._entry.config(fg=Theme.get_color("TEXT_MUTED"), show="")
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder)

    def _hide_placeholder(self) -> None:
        self._entry.config(fg=Theme.get_color("TEXT_PRIMARY"), show=self._show_char)
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")

    def _on_focus_in(self, event: tk.Event) -> None:
        self._has_focus = True
        self._border.config(bg=Theme.get_color("BORDER_FOCUS"))
        if self._entry.get() == self._placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        self._has_focus = False
        self._update_border()
        if not self._entry.get():
            self._show_placeholder()

    def _on_change(self, *args) -> None:
        if self._validate_func and self._textvariable:
            value = self._textvariable.get()
            if value and value != self._placeholder:
                self._is_valid = self._validate_func(value)
                self._update_border()

    def _update_border(self) -> None:
        if self._has_focus:
            color = Theme.get_color("BORDER_FOCUS")
        elif self._is_valid is False:
            color = Theme.get_color("BORDER_ERROR")
        else:
            color = Theme.get_color("BORDER_COLOR")
        self._border.config(bg=color)

    def get(self) -> str:
        value = self._entry.get()
        return "" if value == self._placeholder else value


class PasswordEntry(tk.Frame):
    """Password entry with visibility toggle."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "",
        textvariable: Optional[tk.StringVar] = None,
        tooltip: str = "",
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._placeholder = placeholder
        self._has_focus = False
        self._is_visible = False
        self._textvariable = textvariable

        # Border
        self._border = tk.Frame(self, bg=Theme.get_color("BORDER_COLOR"), padx=1, pady=1)
        self._border.pack(fill="x", expand=True)

        # Inner
        self._inner = tk.Frame(self._border, bg=Theme.get_color("BG_INPUT"))
        self._inner.pack(fill="x", expand=True)

        # Entry
        self._entry = tk.Entry(
            self._inner,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            insertbackground=Theme.get_color("TEXT_PRIMARY"),
            relief="flat",
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY),
            textvariable=textvariable,
            show="*",
            **kwargs
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=8)

        # Toggle button (text-based, no emoji)
        self._toggle = tk.Label(
            self._inner,
            text="Show",
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            cursor="hand2"
        )
        self._toggle.pack(side="right", padx=(5, 10), pady=8)

        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._toggle.bind("<Button-1>", self._toggle_visibility)
        self._toggle.bind("<Enter>", lambda e: self._toggle.config(fg=Theme.get_color("TEXT_PRIMARY")))
        self._toggle.bind("<Leave>", lambda e: self._toggle.config(fg=Theme.get_color("TEXT_MUTED")))

        if placeholder and textvariable and not textvariable.get():
            self._show_placeholder()

        if tooltip:
            Tooltip(self._entry, tooltip)

    def _show_placeholder(self) -> None:
        self._entry.config(fg=Theme.get_color("TEXT_MUTED"), show="")
        self._entry.delete(0, "end")
        self._entry.insert(0, self._placeholder)

    def _hide_placeholder(self) -> None:
        self._entry.config(fg=Theme.get_color("TEXT_PRIMARY"))
        if not self._is_visible:
            self._entry.config(show="*")
        if self._entry.get() == self._placeholder:
            self._entry.delete(0, "end")

    def _on_focus_in(self, event: tk.Event) -> None:
        self._has_focus = True
        self._border.config(bg=Theme.get_color("BORDER_FOCUS"))
        if self._entry.get() == self._placeholder:
            self._hide_placeholder()

    def _on_focus_out(self, event: tk.Event) -> None:
        self._has_focus = False
        self._border.config(bg=Theme.get_color("BORDER_COLOR"))
        if not self._entry.get():
            self._show_placeholder()

    def _toggle_visibility(self, event: tk.Event) -> None:
        if self._entry.get() == self._placeholder:
            return
        self._is_visible = not self._is_visible
        if self._is_visible:
            self._entry.config(show="")
            self._toggle.config(text="Hide")
        else:
            self._entry.config(show="*")
            self._toggle.config(text="Show")

    def get(self) -> str:
        value = self._entry.get()
        return "" if value == self._placeholder else value


class ModernButton(tk.Canvas):
    """Clean button with hover effect."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        command: Optional[Callable] = None,
        primary: bool = True,
        width: int = 120,
        height: int = 36,
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

        self._draw()

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

        if tooltip:
            Tooltip(self, tooltip)

    def _draw(self) -> None:
        self.delete("all")

        if self._primary:
            bg = Theme.get_color("BTN_PRIMARY_BG")
            fg = Theme.get_color("BTN_PRIMARY_FG")
            hover = Theme.get_color("BTN_PRIMARY_HOVER")
        else:
            bg = Theme.get_color("BTN_SECONDARY_BG")
            fg = Theme.get_color("BTN_SECONDARY_FG")
            hover = Theme.get_color("BTN_SECONDARY_HOVER")

        if not self._enabled:
            bg = Theme.get_color("BTN_DISABLED_BG")
            fg = Theme.get_color("BTN_DISABLED_FG")
        elif self._hovered:
            bg = hover

        # Rectangle with slight rounding
        r = 4
        self.create_polygon(
            r, 0, self._width - r, 0,
            self._width, 0, self._width, r,
            self._width, self._height - r, self._width, self._height,
            self._width - r, self._height, r, self._height,
            0, self._height, 0, self._height - r,
            0, r, 0, 0,
            smooth=True, fill=bg, outline=""
        )

        self.create_text(
            self._width // 2,
            self._height // 2,
            text=self._text,
            fill=fg,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        )

    def _on_enter(self, event: tk.Event) -> None:
        if self._enabled:
            self._hovered = True
            self._draw()
            self.config(cursor="hand2")

    def _on_leave(self, event: tk.Event) -> None:
        self._hovered = False
        self._draw()
        self.config(cursor="")

    def _on_click(self, event: tk.Event) -> None:
        if self._enabled and self._command:
            self._command()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        self._draw()


class ModernCheckbox(tk.Frame):
    """Clean checkbox widget."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        variable: Optional[tk.BooleanVar] = None,
        command: Optional[Callable] = None,
        tooltip: str = "",
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._variable = variable or tk.BooleanVar()
        self._command = command

        self._canvas = tk.Canvas(
            self, width=16, height=16,
            bg=Theme.get_color("BG_CARD"),
            highlightthickness=0
        )
        self._canvas.pack(side="left", padx=(0, 8))

        self._label = tk.Label(
            self, text=text,
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        )
        self._label.pack(side="left")

        self._draw()

        self._canvas.bind("<Button-1>", self._toggle)
        self._label.bind("<Button-1>", self._toggle)
        self._variable.trace_add("write", lambda *a: self._draw())

        if tooltip:
            Tooltip(self, tooltip)

    def _draw(self) -> None:
        self._canvas.delete("all")

        if self._variable.get():
            self._canvas.create_rectangle(
                1, 1, 15, 15,
                fill=Theme.get_color("ACCENT_PRIMARY"),
                outline=""
            )
            # Checkmark
            self._canvas.create_line(
                4, 8, 7, 11, 12, 4,
                fill="#fff", width=2, capstyle="round", joinstyle="round"
            )
        else:
            self._canvas.create_rectangle(
                1, 1, 15, 15,
                fill=Theme.get_color("BG_INPUT"),
                outline=Theme.get_color("BORDER_COLOR"),
                width=1
            )

    def _toggle(self, event: tk.Event) -> None:
        self._variable.set(not self._variable.get())
        if self._command:
            self._command()


class ThemeToggle(tk.Frame):
    """Simple dark/light theme toggle."""

    def __init__(
        self,
        parent: tk.Widget,
        command: Optional[Callable[[bool], None]] = None,
        **kwargs
    ) -> None:
        super().__init__(parent, bg=Theme.get_color("BG_CARD"))

        self._command = command
        self._is_dark = Theme.is_dark_mode()

        self._label = tk.Label(
            self,
            text="Dark mode",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        )
        self._label.pack(side="left", padx=(0, 10))

        self._canvas = tk.Canvas(
            self, width=40, height=20,
            bg=Theme.get_color("BG_CARD"),
            highlightthickness=0
        )
        self._canvas.pack(side="left")

        self._draw()

        self._canvas.bind("<Button-1>", self._toggle)
        self._label.bind("<Button-1>", self._toggle)

    def _draw(self) -> None:
        self._canvas.delete("all")

        # Track
        color = Theme.get_color("ACCENT_PRIMARY") if self._is_dark else Theme.get_color("BORDER_COLOR")
        self._canvas.create_oval(0, 0, 20, 20, fill=color, outline="")
        self._canvas.create_oval(20, 0, 40, 20, fill=color, outline="")
        self._canvas.create_rectangle(10, 0, 30, 20, fill=color, outline="")

        # Knob
        x = 22 if self._is_dark else 2
        self._canvas.create_oval(x, 2, x + 16, 18, fill="#fff", outline="")

    def _toggle(self, event: tk.Event) -> None:
        self._is_dark = not self._is_dark
        self._draw()
        if self._command:
            self._command(self._is_dark)
