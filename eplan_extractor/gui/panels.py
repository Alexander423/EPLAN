"""
Clean panel components for the GUI.
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Optional

from ..constants import VERSION
from .theme import Theme


class ProgressIndicator(tk.Canvas):
    """Simple step-based progress indicator."""

    STEPS = ["Login", "Project", "Extract", "Export"]

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(
            parent,
            height=60,
            bg=Theme.BG_CARD,
            highlightthickness=0,
            **kwargs
        )
        self._current_step = -1
        self._progress = 0.0
        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self) -> None:
        self.delete("all")

        width = self.winfo_width()
        if width < 10:
            return

        steps = len(self.STEPS)
        step_width = (width - 60) / (steps - 1)
        y = 20

        # Background line
        self.create_line(30, y, width - 30, y, fill=Theme.BORDER_COLOR, width=2)

        # Progress line
        if self._current_step >= 0:
            progress_x = 30 + (self._current_step * step_width) + (self._progress * step_width)
            progress_x = min(progress_x, width - 30)
            self.create_line(30, y, progress_x, y, fill=Theme.ACCENT_PRIMARY, width=2)

        # Step circles
        for i, name in enumerate(self.STEPS):
            x = 30 + i * step_width

            if i < self._current_step:
                color = Theme.ACCENT_SUCCESS
                fg = Theme.TEXT_PRIMARY
            elif i == self._current_step:
                color = Theme.ACCENT_PRIMARY
                fg = Theme.TEXT_PRIMARY
            else:
                color = Theme.BORDER_COLOR
                fg = Theme.TEXT_MUTED

            self.create_oval(x - 8, y - 8, x + 8, y + 8, fill=color, outline="")
            self.create_text(x, y, text=str(i + 1), fill="#fff", font=(Theme.FONT_FAMILY, 8))
            self.create_text(x, y + 25, text=name, fill=fg, font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL))

    def set_step(self, step: int, progress: float = 0.0) -> None:
        self._current_step = step
        self._progress = max(0.0, min(1.0, progress))
        self._draw()

    def reset(self) -> None:
        self._current_step = -1
        self._progress = 0.0
        self._draw()


class StatusBar(tk.Frame):
    """Simple status bar."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kwargs)

        self._dot = tk.Label(
            self,
            text="",
            bg=Theme.BG_SECONDARY,
            fg=Theme.STATUS_IDLE,
            font=(Theme.FONT_FAMILY, 8)
        )
        self._dot.pack(side="left", padx=(15, 8), pady=8)

        self._text = tk.Label(
            self,
            text="Ready",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            anchor="w"
        )
        self._text.pack(side="left", fill="x", expand=True, pady=8)

        self._version = tk.Label(
            self,
            text=f"v{VERSION}",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        self._version.pack(side="right", padx=15, pady=8)

    def set_status(self, message: str, status: str = "idle") -> None:
        self._text.config(text=message)
        colors = {
            "idle": Theme.STATUS_IDLE,
            "running": Theme.STATUS_RUNNING,
            "success": Theme.STATUS_SUCCESS,
            "error": Theme.STATUS_ERROR,
            "info": Theme.ACCENT_PRIMARY
        }
        self._dot.config(fg=colors.get(status, Theme.STATUS_IDLE))


class LogPanel(tk.Frame):
    """Clean log panel."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kwargs)

        # Header
        header = tk.Frame(self, bg=Theme.BG_SECONDARY)
        header.pack(fill="x", padx=12, pady=(12, 8))

        tk.Label(
            header,
            text="Log",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING)
        ).pack(side="left")

        clear_btn = tk.Label(
            header,
            text="Clear",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            cursor="hand2"
        )
        clear_btn.pack(side="right")
        clear_btn.bind("<Button-1>", lambda e: self.clear())
        clear_btn.bind("<Enter>", lambda e: clear_btn.config(fg=Theme.TEXT_PRIMARY))
        clear_btn.bind("<Leave>", lambda e: clear_btn.config(fg=Theme.TEXT_MUTED))

        # Log area
        self._text = tk.Text(
            self,
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            relief="flat",
            padx=12,
            pady=8,
            wrap="word",
            state="disabled",
            height=8
        )
        self._text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Tags
        self._text.tag_configure("time", foreground=Theme.TEXT_MUTED)
        self._text.tag_configure("DEBUG", foreground=Theme.TEXT_MUTED)
        self._text.tag_configure("INFO", foreground=Theme.TEXT_SECONDARY)
        self._text.tag_configure("WARNING", foreground=Theme.ACCENT_WARNING)
        self._text.tag_configure("ERROR", foreground=Theme.ACCENT_ERROR)
        self._text.tag_configure("SUCCESS", foreground=Theme.ACCENT_SUCCESS)

        # Scrollbar
        scrollbar = tk.Scrollbar(self._text, command=self._text.yview)
        scrollbar.pack(side="right", fill="y")
        self._text.config(yscrollcommand=scrollbar.set)

    def log(self, message: str, level: str = "INFO") -> None:
        self._text.config(state="normal")
        time = datetime.now().strftime("%H:%M:%S")
        self._text.insert("end", f"[{time}] ", "time")
        self._text.insert("end", f"{message}\n", level)
        self._text.see("end")
        self._text.config(state="disabled")

    def clear(self) -> None:
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")
