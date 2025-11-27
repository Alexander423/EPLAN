"""
Main GUI application for EPLAN eVIEW Text Extractor.
"""

from __future__ import annotations

import os
import re
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from ..constants import BASE_URL, VERSION
from ..core.cache import CacheManager
from ..core.config import AppConfig, ConfigManager, ExtractionRecord
from ..core.extractor import SeleniumEPlanExtractor
from ..core.updater import UpdateChecker, UpdateDownloader, ReleaseInfo, format_size
from ..utils.logging import get_logger
from ..utils.i18n import I18n, t
from ..utils.notifications import NotificationManager
from .panels import LogPanel, ProgressIndicator, StatusBar
from .theme import Theme
from .tray import SystemTray
from .widgets import (
    ModernButton,
    ModernCheckbox,
    ModernEntry,
    PasswordEntry,
    ThemeToggle,
    Tooltip,
)


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_project(project: str) -> bool:
    """Validate project number (non-empty)."""
    return len(project.strip()) >= 2


class EPlanExtractorGUI:
    """
    Modern professional GUI for the EPLAN eVIEW Text Extractor.

    Features:
    - Dark/Light theme with toggle
    - Card-based layout
    - Progress step indicator
    - Password visibility toggle
    - Input validation
    - Tooltips for help
    - Multi-language support (EN/DE)
    - System tray integration
    - Desktop notifications
    - Keyboard shortcuts
    - Recent projects dropdown
    - Extraction history
    - Statistics dashboard
    """

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI."""
        self.root = root
        self.root.title(t("app_title"))
        self.root.geometry("720x900")
        self.root.minsize(620, 800)
        self.root.configure(bg=Theme.get_color("BG_PRIMARY"))

        # Try to set window icon (if available)
        try:
            self.root.iconbitmap(default="")
        except:
            pass

        self._logger = get_logger()
        self._config_manager = ConfigManager()
        self._cache_manager = CacheManager()
        self._extractor: Optional[SeleniumEPlanExtractor] = None
        self._is_running = False
        self._current_step = -1
        self._extraction_start_time = 0.0

        # Variables
        self._username_var = tk.StringVar()
        self._password_var = tk.StringVar()
        self._project_var = tk.StringVar()
        self._headless_var = tk.BooleanVar(value=True)
        self._export_excel_var = tk.BooleanVar(value=True)
        self._export_csv_var = tk.BooleanVar(value=False)
        self._export_json_var = tk.BooleanVar(value=False)
        self._save_credentials_var = tk.BooleanVar(value=True)
        self._output_dir_var = tk.StringVar()

        # Load config first to get settings
        self._config = self._config_manager.load()

        # Set language from config
        I18n.set_language(self._config.language)

        # Set up notifications
        NotificationManager.set_enabled(self._config.show_notifications)

        # Set up system tray
        self._tray = SystemTray(
            root,
            on_show=self._restore_window,
            on_quit=self._quit_app,
            on_start=self._start_extraction,
            on_stop=self._stop_extraction
        )

        if self._config.minimize_to_tray and self._tray.is_available():
            self._tray.set_enabled(True)
            self._tray.start()

        self._setup_ui()
        self._setup_keyboard_shortcuts()
        self._load_config()

        # Register logger callback
        self._logger.add_callback(self._log_callback)

        # Register theme observer
        Theme.add_observer(self._on_theme_change)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Check for updates on startup if enabled
        if self._config.check_updates_on_startup:
            self.root.after(2000, self._check_updates_on_startup)

    def _setup_keyboard_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        self.root.bind("<Control-Return>", lambda e: self._start_extraction())
        self.root.bind("<Escape>", lambda e: self._stop_extraction() if self._is_running else None)
        self.root.bind("<Control-comma>", lambda e: self._show_settings())
        self.root.bind("<Control-q>", lambda e: self._quit_app())
        self.root.bind("<Control-h>", lambda e: self._show_history())
        self.root.bind("<F1>", lambda e: self._show_shortcuts_help())

    def _setup_ui(self) -> None:
        """Set up the modern user interface."""
        # Main container
        self._main_container = tk.Frame(self.root, bg=Theme.get_color("BG_PRIMARY"))
        self._main_container.pack(fill="both", expand=True)

        # Header
        self._create_header(self._main_container)

        # Content area with scrolling
        self._content_frame = tk.Frame(self._main_container, bg=Theme.get_color("BG_PRIMARY"))
        self._content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Credentials Card
        self._create_credentials_card(self._content_frame)

        # Options Card
        self._create_options_card(self._content_frame)

        # Progress Card
        self._create_progress_card(self._content_frame)

        # Action Buttons
        self._create_action_buttons(self._content_frame)

        # Log Panel
        self._create_log_panel(self._content_frame)

        # Status Bar
        self._status_bar = StatusBar(self._main_container)
        self._status_bar.pack(fill="x", side="bottom")

    def _create_header(self, parent: tk.Widget) -> None:
        """Create the header section."""
        self._header = tk.Frame(parent, bg=Theme.get_color("BG_PRIMARY"))
        self._header.pack(fill="x", padx=20, pady=(20, 10))

        # Logo/Title
        title_frame = tk.Frame(self._header, bg=Theme.get_color("BG_PRIMARY"))
        title_frame.pack(side="left")

        self._title_eplan = tk.Label(
            title_frame,
            text=t("eplan"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("ACCENT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold")
        )
        self._title_eplan.pack(side="left")

        self._title_extractor = tk.Label(
            title_frame,
            text=t("eview_extractor"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE)
        )
        self._title_extractor.pack(side="left")

        # Version badge
        version_badge = tk.Label(
            title_frame,
            text=f" v{VERSION}",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        version_badge.pack(side="left", padx=(5, 0), pady=(8, 0))

        # Right side controls
        controls_frame = tk.Frame(self._header, bg=Theme.get_color("BG_PRIMARY"))
        controls_frame.pack(side="right")

        # History button
        self._history_btn = tk.Label(
            controls_frame,
            text="📋",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, 16),
            cursor="hand2"
        )
        self._history_btn.pack(side="left", padx=8)
        self._history_btn.bind("<Button-1>", lambda e: self._show_history())
        self._history_btn.bind("<Enter>", lambda e: self._history_btn.config(fg=Theme.get_color("TEXT_PRIMARY")))
        self._history_btn.bind("<Leave>", lambda e: self._history_btn.config(fg=Theme.get_color("TEXT_MUTED")))
        Tooltip(self._history_btn, t("extraction_history"))

        # Statistics button
        self._stats_btn = tk.Label(
            controls_frame,
            text="📊",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, 16),
            cursor="hand2"
        )
        self._stats_btn.pack(side="left", padx=8)
        self._stats_btn.bind("<Button-1>", lambda e: self._show_statistics())
        self._stats_btn.bind("<Enter>", lambda e: self._stats_btn.config(fg=Theme.get_color("TEXT_PRIMARY")))
        self._stats_btn.bind("<Leave>", lambda e: self._stats_btn.config(fg=Theme.get_color("TEXT_MUTED")))
        Tooltip(self._stats_btn, t("statistics"))

        # Theme toggle (mini)
        self._theme_btn = tk.Label(
            controls_frame,
            text="🌙" if Theme.is_dark_mode() else "☀",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, 16),
            cursor="hand2"
        )
        self._theme_btn.pack(side="left", padx=8)
        self._theme_btn.bind("<Button-1>", self._toggle_theme)
        self._theme_btn.bind("<Enter>", lambda e: self._theme_btn.config(fg=Theme.get_color("TEXT_PRIMARY")))
        self._theme_btn.bind("<Leave>", lambda e: self._theme_btn.config(fg=Theme.get_color("TEXT_MUTED")))
        Tooltip(self._theme_btn, t("dark_mode") if Theme.is_dark_mode() else t("light_mode"))

        # Settings button
        self._settings_btn = tk.Label(
            controls_frame,
            text="⚙",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, 18),
            cursor="hand2"
        )
        self._settings_btn.pack(side="left", padx=8)
        self._settings_btn.bind("<Enter>", lambda e: self._settings_btn.config(fg=Theme.get_color("TEXT_PRIMARY")))
        self._settings_btn.bind("<Leave>", lambda e: self._settings_btn.config(fg=Theme.get_color("TEXT_MUTED")))
        self._settings_btn.bind("<Button-1>", lambda e: self._show_settings())
        Tooltip(self._settings_btn, t("settings_title") + " (Ctrl+,)")

    def _create_card(self, parent: tk.Widget, title: str, icon: str = "") -> tk.Frame:
        """Create a card container."""
        card = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        card.pack(fill="x", pady=8)

        # Title row
        title_row = tk.Frame(card, bg=Theme.get_color("BG_CARD"))
        title_row.pack(fill="x", padx=20, pady=(15, 10))

        if icon:
            tk.Label(
                title_row,
                text=icon,
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("ACCENT_PRIMARY"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING)
            ).pack(side="left", padx=(0, 8))

        tk.Label(
            title_row,
            text=title,
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(side="left")

        # Content frame
        content = tk.Frame(card, bg=Theme.get_color("BG_CARD"))
        content.pack(fill="x", padx=20, pady=(0, 15))

        return content

    def _create_credentials_card(self, parent: tk.Widget) -> None:
        """Create the credentials input card."""
        content = self._create_card(parent, t("microsoft_credentials"), "🔐")

        # Email
        email_label_row = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        email_label_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            email_label_row,
            text=t("email_address"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        tk.Label(
            email_label_row,
            text="*",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("ACCENT_ERROR"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        self._email_entry = ModernEntry(
            content,
            placeholder=t("email_placeholder"),
            textvariable=self._username_var,
            tooltip=t("email_tooltip"),
            validate_func=validate_email
        )
        self._email_entry.pack(fill="x", pady=(0, 15))

        # Password
        password_label_row = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        password_label_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            password_label_row,
            text=t("password"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        tk.Label(
            password_label_row,
            text="*",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("ACCENT_ERROR"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        self._password_entry = PasswordEntry(
            content,
            placeholder=t("password_placeholder"),
            textvariable=self._password_var,
            tooltip=t("password_tooltip")
        )
        self._password_entry.pack(fill="x", pady=(0, 15))

        # Project Number with recent projects dropdown
        project_label_row = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        project_label_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            project_label_row,
            text=t("project_number"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        tk.Label(
            project_label_row,
            text="*",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("ACCENT_ERROR"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        # Project entry with dropdown
        project_frame = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        project_frame.pack(fill="x")

        self._project_entry = ModernEntry(
            project_frame,
            placeholder=t("project_placeholder"),
            textvariable=self._project_var,
            tooltip=t("project_tooltip"),
            validate_func=validate_project
        )
        self._project_entry.pack(side="left", fill="x", expand=True)

        # Recent projects dropdown button
        recent_projects = self._config_manager.get_recent_projects()
        if recent_projects:
            self._recent_btn = tk.Label(
                project_frame,
                text="▼",
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("TEXT_MUTED"),
                font=(Theme.FONT_FAMILY, 10),
                cursor="hand2"
            )
            self._recent_btn.pack(side="right", padx=(5, 0))
            self._recent_btn.bind("<Button-1>", self._show_recent_projects)
            Tooltip(self._recent_btn, t("recent_projects"))

    def _show_recent_projects(self, event: tk.Event) -> None:
        """Show recent projects dropdown."""
        recent_projects = self._config_manager.get_recent_projects()
        if not recent_projects:
            return

        menu = tk.Menu(self.root, tearoff=0)

        for project in recent_projects[:10]:
            menu.add_command(
                label=project,
                command=lambda p=project: self._project_var.set(p)
            )

        menu.post(event.x_root, event.y_root)

    def _create_options_card(self, parent: tk.Widget) -> None:
        """Create the options card."""
        content = self._create_card(parent, t("options"), "⚙")

        options_grid = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        options_grid.pack(fill="x")

        # Left column - Export options
        left_col = tk.Frame(options_grid, bg=Theme.get_color("BG_CARD"))
        left_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            left_col,
            text=t("export_format"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        ModernCheckbox(
            left_col,
            text=t("excel_xlsx"),
            variable=self._export_excel_var,
            tooltip=t("export_tooltip_excel")
        ).pack(anchor="w", pady=2)

        ModernCheckbox(
            left_col,
            text=t("csv_file"),
            variable=self._export_csv_var,
            tooltip=t("export_tooltip_csv")
        ).pack(anchor="w", pady=2)

        ModernCheckbox(
            left_col,
            text=t("json_file"),
            variable=self._export_json_var,
            tooltip=t("export_tooltip_json")
        ).pack(anchor="w", pady=2)

        # Right column - Behavior options
        right_col = tk.Frame(options_grid, bg=Theme.get_color("BG_CARD"))
        right_col.pack(side="right", fill="x", expand=True)

        tk.Label(
            right_col,
            text=t("behavior"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        ModernCheckbox(
            right_col,
            text=t("run_in_background"),
            variable=self._headless_var,
            tooltip=t("headless_tooltip")
        ).pack(anchor="w", pady=2)

        ModernCheckbox(
            right_col,
            text=t("save_credentials"),
            variable=self._save_credentials_var,
            tooltip=t("save_creds_tooltip")
        ).pack(anchor="w", pady=2)

        # Output directory
        output_frame = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        output_frame.pack(fill="x", pady=(15, 0))

        tk.Label(
            output_frame,
            text=t("output_directory"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        dir_row = tk.Frame(output_frame, bg=Theme.get_color("BG_CARD"))
        dir_row.pack(fill="x")

        self._output_dir_entry = ModernEntry(
            dir_row,
            placeholder=t("default_directory"),
            textvariable=self._output_dir_var
        )
        self._output_dir_entry.pack(side="left", fill="x", expand=True)

        ModernButton(
            dir_row,
            text=t("browse"),
            command=self._browse_output_dir,
            primary=False,
            width=80
        ).pack(side="right", padx=(10, 0))

    def _browse_output_dir(self) -> None:
        """Open directory browser for output."""
        directory = filedialog.askdirectory(
            title=t("output_directory"),
            initialdir=self._output_dir_var.get() or os.getcwd()
        )
        if directory:
            self._output_dir_var.set(directory)

    def _create_progress_card(self, parent: tk.Widget) -> None:
        """Create the progress indicator card."""
        card = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        card.pack(fill="x", pady=8)

        # Title row
        title_row = tk.Frame(card, bg=Theme.get_color("BG_CARD"))
        title_row.pack(fill="x", padx=20, pady=(15, 10))

        tk.Label(
            title_row,
            text="📊",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("ACCENT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING)
        ).pack(side="left", padx=(0, 8))

        tk.Label(
            title_row,
            text=t("extraction_progress"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(side="left")

        self._progress_indicator = ProgressIndicator(card)
        self._progress_indicator.pack(fill="x", padx=20, pady=(0, 15))

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = tk.Frame(parent, bg=Theme.get_color("BG_PRIMARY"))
        button_frame.pack(fill="x", pady=15)

        # Center the buttons
        inner_frame = tk.Frame(button_frame, bg=Theme.get_color("BG_PRIMARY"))
        inner_frame.pack()

        self._start_button = ModernButton(
            inner_frame,
            text="▶  " + t("start_extraction"),
            command=self._start_extraction,
            primary=True,
            width=180,
            tooltip=t("start_tooltip") + " (Ctrl+Enter)"
        )
        self._start_button.pack(side="left", padx=5)

        self._stop_button = ModernButton(
            inner_frame,
            text="■  " + t("stop"),
            command=self._stop_extraction,
            primary=False,
            width=100,
            tooltip=t("stop_tooltip") + " (Esc)"
        )
        self._stop_button.pack(side="left", padx=5)
        self._stop_button.set_enabled(False)

    def _create_log_panel(self, parent: tk.Widget) -> None:
        """Create the log panel."""
        self._log_panel = LogPanel(parent)
        self._log_panel.pack(fill="both", expand=True, pady=8)

    def _toggle_theme(self, event: tk.Event = None) -> None:
        """Toggle between dark and light theme."""
        is_dark = Theme.toggle_mode()
        self._theme_btn.config(text="🌙" if is_dark else "☀")
        self._logger.info(f"Switched to {'dark' if is_dark else 'light'} mode")

    def _on_theme_change(self) -> None:
        """Handle theme change."""
        is_dark = Theme.is_dark_mode()
        self._theme_btn.config(text="🌙" if is_dark else "☀")

    def _on_close(self) -> None:
        """Handle window close."""
        if self._config.minimize_to_tray and self._tray.is_enabled():
            self._tray.minimize_to_tray()
        else:
            self._quit_app()

    def _restore_window(self) -> None:
        """Restore window from tray."""
        self._tray.restore_from_tray()

    def _quit_app(self) -> None:
        """Quit the application."""
        if self._is_running:
            if not messagebox.askyesno(
                t("app_title"),
                "Extraction is running. Are you sure you want to quit?"
            ):
                return
            self._stop_extraction()

        self._tray.stop()
        self.root.destroy()

    def _check_updates_on_startup(self) -> None:
        """Check for updates on startup (silent)."""
        def check():
            try:
                checker = UpdateChecker()
                release = checker.check_for_updates()
                if release:
                    self.root.after(0, lambda: self._notify_update_available(release))
            except Exception:
                pass

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _notify_update_available(self, release: ReleaseInfo) -> None:
        """Notify user about available update."""
        self._status_bar.set_status(
            t("update_available", version=release.version),
            "info"
        )
        NotificationManager.notify_update_available(release.version)

    def _show_settings(self) -> None:
        """Show settings dialog."""
        settings_win = tk.Toplevel(self.root)
        settings_win.title(t("settings_title"))
        settings_win.geometry("520x650")
        settings_win.configure(bg=Theme.get_color("BG_PRIMARY"))
        settings_win.transient(self.root)
        settings_win.grab_set()
        settings_win.geometry(f"+{self.root.winfo_x() + 100}+{self.root.winfo_y() + 50}")

        # Create scrollable canvas
        canvas = tk.Canvas(settings_win, bg=Theme.get_color("BG_PRIMARY"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(settings_win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=Theme.get_color("BG_PRIMARY"))

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Title
        header = tk.Frame(scrollable_frame, bg=Theme.get_color("BG_PRIMARY"))
        header.pack(fill="x", padx=20, pady=20)

        tk.Label(
            header,
            text="⚙  " + t("settings_title"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE - 4, "bold")
        ).pack(side="left")

        # Appearance section
        self._create_settings_section(
            scrollable_frame, "🎨", t("appearance"),
            lambda parent: self._create_appearance_settings(parent, settings_win)
        )

        # Language section
        self._create_settings_section(
            scrollable_frame, "🌐", t("language"),
            lambda parent: self._create_language_settings(parent, settings_win)
        )

        # Notifications section
        self._create_settings_section(
            scrollable_frame, "🔔", t("notifications"),
            lambda parent: self._create_notification_settings(parent)
        )

        # Network section
        self._create_settings_section(
            scrollable_frame, "🌐", t("network"),
            lambda parent: self._create_proxy_settings(parent)
        )

        # Cache section
        self._create_settings_section(
            scrollable_frame, "💾", t("cache_management"),
            lambda parent: self._create_cache_settings(parent, settings_win)
        )

        # Security section
        self._create_settings_section(
            scrollable_frame, "🔒", t("security"),
            lambda parent: self._create_security_settings(parent, settings_win)
        )

        # Updates section
        self._create_settings_section(
            scrollable_frame, "🔄", t("updates"),
            lambda parent: self._create_update_settings(parent, settings_win)
        )

        # About section
        self._create_settings_section(
            scrollable_frame, "ℹ", t("about"),
            lambda parent: self._create_about_section(parent)
        )

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Close button at bottom
        close_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_PRIMARY"))
        close_frame.pack(fill="x", side="bottom", padx=20, pady=15)

        ModernButton(
            close_frame,
            text=t("close"),
            command=settings_win.destroy,
            primary=True,
            width=100
        ).pack(side="right")

    def _create_settings_section(self, parent, icon, title, content_creator) -> None:
        """Create a settings section."""
        frame = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            frame,
            text=f"{icon}  {title}",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        content_frame = tk.Frame(frame, bg=Theme.get_color("BG_CARD"))
        content_frame.pack(fill="x", padx=15, pady=(0, 15))

        content_creator(content_frame)

    def _create_appearance_settings(self, parent, settings_win) -> None:
        """Create appearance settings."""
        ThemeToggle(
            parent,
            command=lambda is_dark: self._apply_theme(is_dark, settings_win)
        ).pack(anchor="w")

        tk.Label(
            parent,
            text=t("theme_restart_note"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(5, 0))

    def _create_language_settings(self, parent, settings_win) -> None:
        """Create language settings."""
        lang_var = tk.StringVar(value=I18n.get_language())

        lang_frame = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        lang_frame.pack(fill="x")

        for code, name in I18n.get_available_languages().items():
            tk.Radiobutton(
                lang_frame,
                text=name,
                variable=lang_var,
                value=code,
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("TEXT_PRIMARY"),
                selectcolor=Theme.get_color("BG_INPUT"),
                activebackground=Theme.get_color("BG_CARD"),
                activeforeground=Theme.get_color("TEXT_PRIMARY"),
                command=lambda: self._change_language(lang_var.get(), settings_win)
            ).pack(side="left", padx=(0, 20))

    def _change_language(self, lang: str, settings_win) -> None:
        """Change application language."""
        I18n.set_language(lang)
        self._config.language = lang
        self._config_manager.save(self._config)

        messagebox.showinfo(
            t("language"),
            "Language changed. Please restart the application for full effect.",
            parent=settings_win
        )

    def _create_notification_settings(self, parent) -> None:
        """Create notification settings."""
        notif_var = tk.BooleanVar(value=self._config.show_notifications)
        tray_var = tk.BooleanVar(value=self._config.minimize_to_tray)

        def save_notif():
            self._config.show_notifications = notif_var.get()
            NotificationManager.set_enabled(notif_var.get())
            self._config_manager.save(self._config)

        def save_tray():
            self._config.minimize_to_tray = tray_var.get()
            self._tray.set_enabled(tray_var.get())
            self._config_manager.save(self._config)

        ModernCheckbox(
            parent,
            text=t("show_notifications"),
            variable=notif_var,
            command=save_notif
        ).pack(anchor="w", pady=2)

        if self._tray.is_available():
            ModernCheckbox(
                parent,
                text=t("minimize_to_tray"),
                variable=tray_var,
                command=save_tray
            ).pack(anchor="w", pady=2)

    def _create_proxy_settings(self, parent) -> None:
        """Create proxy settings."""
        proxy_var = tk.BooleanVar(value=self._config.proxy_enabled)
        host_var = tk.StringVar(value=self._config.proxy_host)
        port_var = tk.StringVar(value=str(self._config.proxy_port))

        def save_proxy():
            self._config.proxy_enabled = proxy_var.get()
            self._config.proxy_host = host_var.get()
            try:
                self._config.proxy_port = int(port_var.get())
            except ValueError:
                self._config.proxy_port = 8080
            self._config_manager.save(self._config)

        ModernCheckbox(
            parent,
            text=t("enable_proxy"),
            variable=proxy_var,
            command=save_proxy
        ).pack(anchor="w", pady=2)

        proxy_frame = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        proxy_frame.pack(fill="x", pady=(10, 0))

        tk.Label(
            proxy_frame,
            text=t("proxy_host") + ":",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left")

        host_entry = tk.Entry(
            proxy_frame,
            textvariable=host_var,
            width=25,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            insertbackground=Theme.get_color("TEXT_PRIMARY")
        )
        host_entry.pack(side="left", padx=5)
        host_entry.bind("<FocusOut>", lambda e: save_proxy())

        tk.Label(
            proxy_frame,
            text=t("proxy_port") + ":",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(side="left", padx=(10, 0))

        port_entry = tk.Entry(
            proxy_frame,
            textvariable=port_var,
            width=6,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            insertbackground=Theme.get_color("TEXT_PRIMARY")
        )
        port_entry.pack(side="left", padx=5)
        port_entry.bind("<FocusOut>", lambda e: save_proxy())

    def _create_cache_settings(self, parent, settings_win) -> None:
        """Create cache settings."""
        tk.Label(
            parent,
            text=t("cache_description"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 10))

        ModernButton(
            parent,
            text="🗑  " + t("clear_cache"),
            command=lambda: self._clear_cache_action(settings_win),
            primary=False,
            width=140
        ).pack(anchor="w")

    def _create_security_settings(self, parent, settings_win) -> None:
        """Create security settings."""
        tk.Label(
            parent,
            text=t("security_description"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 10))

        ModernButton(
            parent,
            text="🔑  " + t("clear_credentials"),
            command=lambda: self._clear_credentials_action(settings_win),
            primary=False,
            width=200
        ).pack(anchor="w")

    def _create_update_settings(self, parent, settings_win) -> None:
        """Create update settings."""
        tk.Label(
            parent,
            text=t("current_version", version=VERSION),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        self._update_status_label = tk.Label(
            parent,
            text="",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        self._update_status_label.pack(anchor="w", pady=(0, 10))

        btn_row = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        btn_row.pack(fill="x")

        self._check_update_btn = ModernButton(
            btn_row,
            text="🔍  " + t("check_for_updates"),
            command=lambda: self._check_for_updates(settings_win),
            primary=False,
            width=180
        )
        self._check_update_btn.pack(side="left")

        # Startup check option
        startup_var = tk.BooleanVar(value=self._config.check_updates_on_startup)

        def save_startup():
            self._config.check_updates_on_startup = startup_var.get()
            self._config_manager.save(self._config)

        ModernCheckbox(
            parent,
            text=t("check_on_startup"),
            variable=startup_var,
            command=save_startup
        ).pack(anchor="w", pady=(10, 0))

    def _create_about_section(self, parent) -> None:
        """Create about section."""
        tk.Label(
            parent,
            text=f"EPLAN eVIEW Extractor v{VERSION}\n"
                 f"{t('about_description')}\n"
                 f"© 2024 {t('copyright')}",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            justify="left"
        ).pack(anchor="w")

    def _apply_theme(self, is_dark: bool, settings_win: tk.Toplevel) -> None:
        """Apply theme change."""
        Theme.set_dark_mode(is_dark)
        self._config.dark_mode = is_dark
        self._config_manager.save(self._config)
        self._theme_btn.config(text="🌙" if is_dark else "☀")

        messagebox.showinfo(
            t("appearance"),
            t("theme_restart_note"),
            parent=settings_win
        )

    def _clear_cache_action(self, parent_window: tk.Toplevel) -> None:
        """Clear cache."""
        count = self._cache_manager.clear()
        self._log_panel.log(t("cache_cleared_msg", count=count), "SUCCESS")
        messagebox.showinfo(
            t("cache_cleared"),
            t("cache_cleared_msg", count=count),
            parent=parent_window
        )

    def _clear_credentials_action(self, parent_window: tk.Toplevel) -> None:
        """Clear saved credentials."""
        self._password_var.set("")
        self._config.password_encrypted = ""
        self._config_manager.save(self._config)
        self._log_panel.log(t("credentials_cleared_msg"), "SUCCESS")
        messagebox.showinfo(
            t("credentials_cleared"),
            t("credentials_cleared_msg"),
            parent=parent_window
        )

    def _check_for_updates(self, parent_window: tk.Toplevel) -> None:
        """Check for updates."""
        self._check_update_btn.set_enabled(False)
        self._update_status_label.config(
            text=t("checking_updates"),
            fg=Theme.get_color("TEXT_MUTED")
        )

        checker = UpdateChecker()
        checker.check_for_updates_async(
            lambda release, error: self.root.after(
                0,
                lambda: self._on_update_check_complete(release, error, parent_window)
            )
        )

    def _on_update_check_complete(
        self,
        release: Optional[ReleaseInfo],
        error: Optional[Exception],
        parent_window: tk.Toplevel
    ) -> None:
        """Handle update check completion."""
        self._check_update_btn.set_enabled(True)

        if error:
            self._update_status_label.config(
                text=t("update_check_failed"),
                fg=Theme.get_color("ACCENT_ERROR")
            )
            return

        if release is None:
            self._update_status_label.config(
                text=t("up_to_date"),
                fg=Theme.get_color("ACCENT_SUCCESS")
            )
            return

        self._update_status_label.config(
            text=t("update_available", version=release.version),
            fg=Theme.get_color("ACCENT_WARNING")
        )
        self._show_update_dialog(release, parent_window)

    def _show_update_dialog(self, release: ReleaseInfo, parent_window: tk.Toplevel) -> None:
        """Show update dialog."""
        dialog = tk.Toplevel(parent_window)
        dialog.title(t("update_available_title"))
        dialog.geometry("450x400")
        dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        dialog.transient(parent_window)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="🎉  " + t("update_available_header"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("ACCENT_SUCCESS"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING + 2, "bold")
        ).pack(pady=(20, 10))

        info_frame = tk.Frame(dialog, bg=Theme.get_color("BG_CARD"))
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            info_frame,
            text=t("new_version", version=release.version),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            info_frame,
            text=t("current_version", version=VERSION),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # Release notes
        notes_frame = tk.Frame(dialog, bg=Theme.get_color("BG_CARD"))
        notes_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(
            notes_frame,
            text=t("release_notes"),
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        notes_text = tk.Text(
            notes_frame,
            wrap="word",
            height=8,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            relief="flat"
        )
        notes_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        notes_text.insert("1.0", release.body or t("no_release_notes"))
        notes_text.config(state="disabled")

        # Buttons
        btn_frame = tk.Frame(dialog, bg=Theme.get_color("BG_PRIMARY"))
        btn_frame.pack(fill="x", padx=20, pady=15)

        if release.download_url:
            ModernButton(
                btn_frame,
                text="⬇  " + t("download_update"),
                command=lambda: self._download_update(release, dialog),
                primary=True,
                width=150
            ).pack(side="left", padx=(0, 10))

        ModernButton(
            btn_frame,
            text="🌐  " + t("view_on_github"),
            command=lambda: UpdateDownloader.open_release_page(release.html_url),
            primary=False,
            width=140
        ).pack(side="left")

        ModernButton(
            btn_frame,
            text=t("later"),
            command=dialog.destroy,
            primary=False,
            width=80
        ).pack(side="right")

    def _download_update(self, release: ReleaseInfo, dialog: tk.Toplevel) -> None:
        """Download update with progress."""
        progress_dialog = tk.Toplevel(dialog)
        progress_dialog.title(t("downloading_update"))
        progress_dialog.geometry("350x150")
        progress_dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        progress_dialog.transient(dialog)
        progress_dialog.grab_set()

        tk.Label(
            progress_dialog,
            text=t("downloading_update"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        ).pack(pady=(20, 10))

        progress_label = tk.Label(
            progress_dialog,
            text="0%",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        progress_label.pack(pady=5)

        progress_canvas = tk.Canvas(
            progress_dialog,
            width=300,
            height=20,
            bg=Theme.get_color("BG_SECONDARY"),
            highlightthickness=0
        )
        progress_canvas.pack(pady=10)
        progress_bar = progress_canvas.create_rectangle(
            0, 0, 0, 20,
            fill=Theme.get_color("ACCENT_PRIMARY"),
            outline=""
        )

        cancel_pressed = [False]
        downloader = UpdateDownloader(release)

        def cancel():
            cancel_pressed[0] = True
            downloader.cancel()
            progress_dialog.destroy()

        ModernButton(
            progress_dialog,
            text=t("cancel"),
            command=cancel,
            primary=False,
            width=80
        ).pack(pady=10)

        def update_progress(downloaded: int, total: int):
            if total > 0:
                percent = int((downloaded / total) * 100)
                bar_width = int((downloaded / total) * 300)
                self.root.after(0, lambda: [
                    progress_label.config(text=f"{percent}%"),
                    progress_canvas.coords(progress_bar, 0, 0, bar_width, 20)
                ])

        def on_complete(file_path, error):
            if cancel_pressed[0]:
                return
            self.root.after(0, progress_dialog.destroy)
            if error:
                self.root.after(0, lambda: messagebox.showerror(
                    t("download_failed"), str(error), parent=dialog
                ))
            elif file_path:
                self.root.after(0, lambda: self._offer_install(file_path, release, dialog))

        downloader.set_progress_callback(update_progress)
        downloader.download_async(on_complete)

    def _offer_install(self, file_path, release: ReleaseInfo, dialog: tk.Toplevel) -> None:
        """Offer to install update."""
        if messagebox.askyesno(
            t("download_complete"),
            t("download_complete_msg", version=release.version, file=file_path),
            parent=dialog
        ):
            if UpdateDownloader.install_update(file_path):
                dialog.destroy()
                self.root.quit()
            else:
                messagebox.showinfo(
                    t("manual_install_required"),
                    t("manual_install_msg", file=file_path),
                    parent=dialog
                )

    def _show_history(self) -> None:
        """Show extraction history dialog."""
        history = self._config_manager.get_history()

        dialog = tk.Toplevel(self.root)
        dialog.title(t("history_title"))
        dialog.geometry("700x500")
        dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        dialog.transient(self.root)

        tk.Label(
            dialog,
            text="📋  " + t("extraction_history"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE - 4, "bold")
        ).pack(pady=(20, 10))

        if not history:
            tk.Label(
                dialog,
                text=t("no_history"),
                bg=Theme.get_color("BG_PRIMARY"),
                fg=Theme.get_color("TEXT_MUTED"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
            ).pack(expand=True)
        else:
            # Create treeview
            columns = ("date", "project", "duration", "variables", "status")
            tree = ttk.Treeview(dialog, columns=columns, show="headings", height=15)

            tree.heading("date", text=t("date_col"))
            tree.heading("project", text=t("project_col"))
            tree.heading("duration", text=t("duration_col"))
            tree.heading("variables", text=t("variables_col"))
            tree.heading("status", text=t("status_col"))

            tree.column("date", width=150)
            tree.column("project", width=200)
            tree.column("duration", width=100)
            tree.column("variables", width=100)
            tree.column("status", width=100)

            for record in history:
                date = record.timestamp[:19].replace("T", " ") if record.timestamp else ""
                duration = f"{record.duration_seconds:.1f}s"
                status = t("success") if record.success else t("failed")
                tree.insert("", "end", values=(
                    date, record.project, duration, record.variables_found, status
                ))

            tree.pack(fill="both", expand=True, padx=20, pady=10)

        btn_frame = tk.Frame(dialog, bg=Theme.get_color("BG_PRIMARY"))
        btn_frame.pack(fill="x", padx=20, pady=15)

        ModernButton(
            btn_frame,
            text="🗑  " + t("clear_history"),
            command=lambda: self._clear_history(dialog),
            primary=False,
            width=140
        ).pack(side="left")

        ModernButton(
            btn_frame,
            text=t("close"),
            command=dialog.destroy,
            primary=True,
            width=100
        ).pack(side="right")

    def _clear_history(self, dialog: tk.Toplevel) -> None:
        """Clear extraction history."""
        count = self._config_manager.clear_history()
        messagebox.showinfo(
            t("history_cleared"),
            t("history_cleared_msg", count=count),
            parent=dialog
        )
        dialog.destroy()
        self._show_history()

    def _show_statistics(self) -> None:
        """Show statistics dialog."""
        stats = self._config_manager.get_statistics()

        dialog = tk.Toplevel(self.root)
        dialog.title(t("statistics_title"))
        dialog.geometry("400x400")
        dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        dialog.transient(self.root)

        tk.Label(
            dialog,
            text="📊  " + t("statistics"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE - 4, "bold")
        ).pack(pady=(20, 20))

        stats_frame = tk.Frame(dialog, bg=Theme.get_color("BG_CARD"))
        stats_frame.pack(fill="x", padx=20, pady=10)

        stat_items = [
            (t("total_extractions"), stats["total_extractions"]),
            (t("successful_extractions"), stats["successful_extractions"]),
            (t("failed_extractions"), stats["failed_extractions"]),
            (t("total_pages"), stats["total_pages"]),
            (t("total_variables"), stats["total_variables"]),
            (t("unique_projects"), stats["unique_projects"]),
            (t("total_time"), f"{stats['total_time_seconds'] / 60:.1f} min"),
            (t("average_time"), f"{stats['average_time_seconds']:.1f}s"),
        ]

        for label, value in stat_items:
            row = tk.Frame(stats_frame, bg=Theme.get_color("BG_CARD"))
            row.pack(fill="x", padx=15, pady=5)

            tk.Label(
                row,
                text=label,
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("TEXT_SECONDARY"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
            ).pack(side="left")

            tk.Label(
                row,
                text=str(value),
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("TEXT_PRIMARY"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
            ).pack(side="right")

        ModernButton(
            dialog,
            text=t("close"),
            command=dialog.destroy,
            primary=True,
            width=100
        ).pack(pady=20)

    def _show_shortcuts_help(self) -> None:
        """Show keyboard shortcuts help."""
        dialog = tk.Toplevel(self.root)
        dialog.title(t("keyboard_shortcuts"))
        dialog.geometry("350x250")
        dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        dialog.transient(self.root)

        tk.Label(
            dialog,
            text="⌨  " + t("keyboard_shortcuts"),
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(pady=(20, 20))

        shortcuts = [
            ("Ctrl+Enter", t("shortcut_start")),
            ("Escape", t("shortcut_stop")),
            ("Ctrl+,", t("shortcut_settings")),
            ("Ctrl+H", t("extraction_history")),
            ("Ctrl+Q", t("shortcut_quit")),
            ("F1", t("keyboard_shortcuts")),
        ]

        for key, desc in shortcuts:
            row = tk.Frame(dialog, bg=Theme.get_color("BG_PRIMARY"))
            row.pack(fill="x", padx=30, pady=3)

            tk.Label(
                row,
                text=key,
                bg=Theme.get_color("BG_PRIMARY"),
                fg=Theme.get_color("ACCENT_PRIMARY"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold"),
                width=12,
                anchor="w"
            ).pack(side="left")

            tk.Label(
                row,
                text=desc,
                bg=Theme.get_color("BG_PRIMARY"),
                fg=Theme.get_color("TEXT_SECONDARY"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
            ).pack(side="left")

        ModernButton(
            dialog,
            text=t("close"),
            command=dialog.destroy,
            primary=True,
            width=80
        ).pack(pady=20)

    def _log_callback(self, message: str, level: str) -> None:
        """Callback for logger."""
        try:
            self._log_panel.log(message, level)
            self.root.update_idletasks()
        except Exception:
            pass

    def _load_config(self) -> None:
        """Load saved configuration."""
        self._username_var.set(self._config.email)
        self._project_var.set(self._config.project)
        self._headless_var.set(self._config.headless)
        self._export_excel_var.set(self._config.export_excel)
        self._export_csv_var.set(self._config.export_csv)
        self._export_json_var.set(self._config.export_json)
        self._output_dir_var.set(self._config.export_directory)

        if self._config.password_encrypted:
            password = self._config_manager.decrypt_password(self._config.password_encrypted)
            self._password_var.set(password)

        # Apply theme
        Theme.set_dark_mode(self._config.dark_mode)

    def _save_config(self) -> None:
        """Save current configuration."""
        password_encrypted = ""
        if self._save_credentials_var.get():
            password_encrypted = self._config_manager.encrypt_password(
                self._password_var.get()
            )

        self._config.email = self._username_var.get()
        self._config.password_encrypted = password_encrypted
        self._config.project = self._project_var.get()
        self._config.headless = self._headless_var.get()
        self._config.export_excel = self._export_excel_var.get()
        self._config.export_csv = self._export_csv_var.get()
        self._config.export_json = self._export_json_var.get()
        self._config.export_directory = self._output_dir_var.get()

        self._config_manager.save(self._config)

    def _validate_inputs(self) -> bool:
        """Validate user inputs."""
        email = self._username_var.get()
        password = self._password_var.get()
        project = self._project_var.get()

        if not email:
            self._show_error(t("validation_email_required"))
            return False

        if not validate_email(email):
            self._show_error(t("validation_email_invalid"))
            return False

        if not password:
            self._show_error(t("validation_password_required"))
            return False

        if not project:
            self._show_error(t("validation_project_required"))
            return False

        return True

    def _show_error(self, message: str) -> None:
        """Show error message."""
        self._status_bar.set_status(message, "error")
        self._log_panel.log(message, "ERROR")

    def _start_extraction(self) -> None:
        """Start extraction."""
        if self._is_running:
            return

        if not self._validate_inputs():
            return

        self._save_config()
        self._config_manager.add_recent_project(self._project_var.get())

        self._is_running = True
        self._extraction_start_time = time.time()
        self._start_button.set_enabled(False)
        self._stop_button.set_enabled(True)
        self._progress_indicator.reset()
        self._status_bar.set_status(t("status_starting"), "running")
        self._tray.set_running_state(True)

        thread = threading.Thread(target=self._run_extraction, daemon=True)
        thread.start()

    def _stop_extraction(self) -> None:
        """Stop extraction."""
        self._is_running = False
        self._status_bar.set_status(t("status_stopped"), "idle")

        if self._extractor:
            self._extractor.request_stop()

        self._start_button.set_enabled(True)
        self._stop_button.set_enabled(False)
        self._tray.set_running_state(False)

    def _update_progress(self, step: int, progress: float = 0.0) -> None:
        """Update progress (thread-safe)."""
        self.root.after(0, lambda: self._progress_indicator.set_step(step, progress))

    def _run_extraction(self) -> None:
        """Run extraction in background thread."""
        pages_extracted = 0
        variables_found = 0
        output_file = ""
        success = False
        error_message = ""

        try:
            self._logger.info("=" * 40)
            self._logger.info("Starting EPLAN eVIEW extraction")
            self._logger.info(f"Project: {self._project_var.get()}")
            self._logger.info("=" * 40)

            self._extractor = SeleniumEPlanExtractor(
                base_url=BASE_URL,
                username=self._username_var.get(),
                password=self._password_var.get(),
                project_number=self._project_var.get(),
                headless=self._headless_var.get(),
                cache_manager=self._cache_manager
            )

            # Step 0: Login
            self._update_progress(0, 0.0)
            self.root.after(0, lambda: self._status_bar.set_status(t("status_logging_in"), "running"))

            self._extractor.setup_driver()
            self._update_progress(0, 0.3)

            if not self._extractor.click_on_login_with_microsoft():
                raise Exception("Failed to find Microsoft login")
            self._update_progress(0, 0.6)

            if not self._extractor.login():
                raise Exception("Login failed")
            self._update_progress(0, 1.0)

            if not self._is_running:
                return

            # Step 1: Open Project
            self._update_progress(1, 0.0)
            self.root.after(0, lambda: self._status_bar.set_status(t("status_opening_project"), "running"))

            if not self._extractor.open_project():
                raise Exception("Failed to open project")
            self._update_progress(1, 0.5)

            if not self._extractor.switch_to_list_view():
                raise Exception("Failed to switch view")
            self._update_progress(1, 1.0)

            if not self._is_running:
                return

            # Step 2: Extract
            self._update_progress(2, 0.0)
            self.root.after(0, lambda: self._status_bar.set_status(t("status_extracting"), "running"))

            if not self._extractor.extract_variables():
                raise Exception("Extraction failed")
            self._update_progress(2, 1.0)

            if not self._is_running:
                return

            # Step 3: Export
            self._update_progress(3, 1.0)

            # Get stats
            pages_extracted = getattr(self._extractor, '_pages_processed', 0)
            variables_found = getattr(self._extractor, '_variables_found', 0)
            output_file = f"{self._project_var.get()} IO-List.xlsx"
            success = True

            self._logger.success(t("status_completed"))
            self.root.after(0, lambda: self._status_bar.set_status(t("status_completed"), "success"))
            self.root.after(0, lambda: messagebox.showinfo(
                t("success"),
                f"{t('status_completed')}\n\nOutput: {output_file}"
            ))

            # Notification
            NotificationManager.notify_extraction_complete(
                self._project_var.get(),
                variables_found,
                output_file
            )

        except Exception as e:
            error_message = str(e)
            self._logger.error(f"Extraction error: {e}")
            self.root.after(0, lambda: self._status_bar.set_status(f"{t('status_error')}: {str(e)[:50]}", "error"))
            self.root.after(0, lambda: messagebox.showerror(t("status_error"), str(e)))
            NotificationManager.notify_extraction_failed(self._project_var.get(), error_message)

        finally:
            # Save history
            record = ExtractionRecord(
                project=self._project_var.get(),
                timestamp=datetime.now().isoformat(),
                duration_seconds=time.time() - self._extraction_start_time,
                pages_extracted=pages_extracted,
                variables_found=variables_found,
                output_file=output_file,
                success=success,
                error_message=error_message
            )
            self._config_manager.add_history_entry(record)

            self._is_running = False
            self._extractor = None
            self.root.after(0, lambda: self._start_button.set_enabled(True))
            self.root.after(0, lambda: self._stop_button.set_enabled(False))
            self.root.after(0, lambda: self._tray.set_running_state(False))
