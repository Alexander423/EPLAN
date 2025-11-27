"""
Panel components for the GUI (Progress, Status, Log).
"""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Optional

from ..constants import VERSION
from .theme import Theme


class ProgressIndicator(tk.Canvas):
    """Animated progress indicator with steps."""

    STEPS = [
        ("Login", "Authenticating with Microsoft"),
        ("Project", "Opening project"),
        ("Extract", "Extracting variables"),
        ("Export", "Saving results")
    ]

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(
            parent,
            height=80,
            bg=Theme.BG_CARD,
            highlightthickness=0,
            **kwargs
        )

        self._current_step = -1
        self._progress = 0.0
        self._animation_id: Optional[str] = None

        self.bind("<Configure>", lambda e: self._draw())

    def _draw(self) -> None:
        """Draw the progress indicator."""
        self.delete("all")

        width = self.winfo_width()
        if width < 10:
            return

        step_count = len(self.STEPS)
        step_width = (width - 40) / (step_count - 1)
        y_line = 25
        y_text = 55

        # Draw connecting line (background)
        self.create_line(
            20, y_line, width - 20, y_line,
            fill=Theme.BORDER_COLOR,
            width=3,
            capstyle="round"
        )

        # Draw progress line
        if self._current_step >= 0:
            progress_width = 20 + (self._current_step * step_width) + (self._progress * step_width)
            progress_width = min(progress_width, width - 20)
            self.create_line(
                20, y_line, progress_width, y_line,
                fill=Theme.ACCENT_PRIMARY,
                width=3,
                capstyle="round"
            )

        # Draw step circles and labels
        for i, (name, desc) in enumerate(self.STEPS):
            x = 20 + i * step_width

            # Circle
            if i < self._current_step:
                # Completed
                color = Theme.ACCENT_SUCCESS
                text_color = Theme.TEXT_PRIMARY
            elif i == self._current_step:
                # Current
                color = Theme.ACCENT_PRIMARY
                text_color = Theme.TEXT_PRIMARY
            else:
                # Pending
                color = Theme.BORDER_COLOR
                text_color = Theme.TEXT_MUTED

            self.create_oval(
                x - 12, y_line - 12, x + 12, y_line + 12,
                fill=color,
                outline=""
            )

            # Step number or checkmark
            if i < self._current_step:
                self.create_text(x, y_line, text="✓", fill="white", font=(Theme.FONT_FAMILY, 10, "bold"))
            else:
                self.create_text(x, y_line, text=str(i + 1), fill="white", font=(Theme.FONT_FAMILY, 10, "bold"))

            # Label
            self.create_text(
                x, y_text,
                text=name,
                fill=text_color,
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
            )

    def set_step(self, step: int, progress: float = 0.0) -> None:
        """Set the current step and progress."""
        self._current_step = step
        self._progress = max(0.0, min(1.0, progress))
        self._draw()

    def reset(self) -> None:
        """Reset the progress indicator."""
        self._current_step = -1
        self._progress = 0.0
        self._draw()


class StatusBar(tk.Frame):
    """Modern status bar with icon and message."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kwargs)

        # Status icon
        self._icon_label = tk.Label(
            self,
            text="●",
            bg=Theme.BG_SECONDARY,
            fg=Theme.STATUS_IDLE,
            font=(Theme.FONT_FAMILY, 12)
        )
        self._icon_label.pack(side="left", padx=(15, 8), pady=10)

        # Status text
        self._text_label = tk.Label(
            self,
            text="Ready",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY),
            anchor="w"
        )
        self._text_label.pack(side="left", fill="x", expand=True, pady=10)

        # Version
        self._version_label = tk.Label(
            self,
            text=f"v{VERSION}",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        self._version_label.pack(side="right", padx=15, pady=10)

    def set_status(self, message: str, status: str = "idle") -> None:
        """Set status message and state."""
        self._text_label.config(text=message)

        colors = {
            "idle": Theme.STATUS_IDLE,
            "running": Theme.STATUS_RUNNING,
            "success": Theme.STATUS_SUCCESS,
            "error": Theme.STATUS_ERROR
        }
        self._icon_label.config(fg=colors.get(status, Theme.STATUS_IDLE))


class LogPanel(tk.Frame):
    """Modern log panel with colored output."""

    def __init__(self, parent: tk.Widget, **kwargs) -> None:
        super().__init__(parent, bg=Theme.BG_SECONDARY, **kwargs)

        # Header
        header = tk.Frame(self, bg=Theme.BG_SECONDARY)
        header.pack(fill="x", padx=15, pady=(15, 10))

        tk.Label(
            header,
            text="Activity Log",
            bg=Theme.BG_SECONDARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(side="left")

        # Clear button
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

        # Log text area
        self._text = tk.Text(
            self,
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            relief="flat",
            padx=15,
            pady=10,
            wrap="word",
            state="disabled"
        )
        self._text.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Configure tags for colored output
        self._text.tag_configure("timestamp", foreground=Theme.TEXT_MUTED)
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
        """Add a log message."""
        self._text.config(state="normal")

        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text.insert("end", f"[{timestamp}] ", "timestamp")
        self._text.insert("end", f"{message}\n", level)

        self._text.see("end")
        self._text.config(state="disabled")

    def clear(self) -> None:
        """Clear the log."""
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        self._text.config(state="disabled")
