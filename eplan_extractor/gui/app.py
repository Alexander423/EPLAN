"""
Main GUI application for EPLAN eVIEW Text Extractor.
"""

from __future__ import annotations

import re
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from ..constants import BASE_URL, VERSION
from ..core.cache import CacheManager
from ..core.config import AppConfig, ConfigManager
from ..core.extractor import SeleniumEPlanExtractor
from ..core.updater import UpdateChecker, UpdateDownloader, ReleaseInfo, format_size
from ..utils.logging import get_logger
from .panels import LogPanel, ProgressIndicator, StatusBar
from .theme import Theme
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
    - Professional typography
    """

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI."""
        self.root = root
        self.root.title("EPLAN eVIEW Extractor")
        self.root.geometry("720x850")
        self.root.minsize(620, 750)
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

        # Variables
        self._username_var = tk.StringVar()
        self._password_var = tk.StringVar()
        self._project_var = tk.StringVar()
        self._headless_var = tk.BooleanVar(value=True)
        self._export_excel_var = tk.BooleanVar(value=True)
        self._export_csv_var = tk.BooleanVar(value=False)
        self._save_credentials_var = tk.BooleanVar(value=True)
        self._auto_open_file_var = tk.BooleanVar(value=False)

        self._setup_ui()
        self._load_config()

        # Register logger callback
        self._logger.add_callback(self._log_callback)

        # Register theme observer
        Theme.add_observer(self._on_theme_change)

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
            text="EPLAN",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("ACCENT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold")
        )
        self._title_eplan.pack(side="left")

        self._title_extractor = tk.Label(
            title_frame,
            text=" eVIEW Extractor",
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
        Tooltip(self._theme_btn, "Toggle Dark/Light Mode")

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
        Tooltip(self._settings_btn, "Open Settings")

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
        content = self._create_card(parent, "Microsoft Credentials", "🔐")

        # Email
        email_label_row = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        email_label_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            email_label_row,
            text="Email Address",
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
            placeholder="your.email@company.com",
            textvariable=self._username_var,
            tooltip="Enter your Microsoft account email",
            validate_func=validate_email
        )
        self._email_entry.pack(fill="x", pady=(0, 15))

        # Password
        password_label_row = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        password_label_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            password_label_row,
            text="Password",
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
            placeholder="Enter your password",
            textvariable=self._password_var,
            tooltip="Enter your Microsoft account password (shown as dots for security)"
        )
        self._password_entry.pack(fill="x", pady=(0, 15))

        # Project Number
        project_label_row = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        project_label_row.pack(fill="x", pady=(0, 5))

        tk.Label(
            project_label_row,
            text="Project Number",
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

        self._project_entry = ModernEntry(
            content,
            placeholder="e.g., PROJECT-001",
            textvariable=self._project_var,
            tooltip="Enter the EPLAN project number to extract",
            validate_func=validate_project
        )
        self._project_entry.pack(fill="x")

    def _create_options_card(self, parent: tk.Widget) -> None:
        """Create the options card."""
        content = self._create_card(parent, "Options", "⚙")

        options_grid = tk.Frame(content, bg=Theme.get_color("BG_CARD"))
        options_grid.pack(fill="x")

        # Left column - Export options
        left_col = tk.Frame(options_grid, bg=Theme.get_color("BG_CARD"))
        left_col.pack(side="left", fill="x", expand=True)

        tk.Label(
            left_col,
            text="Export Format",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        ModernCheckbox(
            left_col,
            text="Excel (.xlsx)",
            variable=self._export_excel_var,
            tooltip="Export results to Excel format"
        ).pack(anchor="w", pady=2)

        ModernCheckbox(
            left_col,
            text="CSV (.csv)",
            variable=self._export_csv_var,
            tooltip="Export results to CSV format"
        ).pack(anchor="w", pady=2)

        # Right column - Behavior options
        right_col = tk.Frame(options_grid, bg=Theme.get_color("BG_CARD"))
        right_col.pack(side="right", fill="x", expand=True)

        tk.Label(
            right_col,
            text="Behavior",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        ModernCheckbox(
            right_col,
            text="Run in Background",
            variable=self._headless_var,
            tooltip="Run browser in headless mode (no visible window)"
        ).pack(anchor="w", pady=2)

        ModernCheckbox(
            right_col,
            text="Save Credentials",
            variable=self._save_credentials_var,
            tooltip="Remember your login credentials (encrypted)"
        ).pack(anchor="w", pady=2)

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
            text="Extraction Progress",
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
            text="▶  Start Extraction",
            command=self._start_extraction,
            primary=True,
            width=180,
            tooltip="Start the extraction process"
        )
        self._start_button.pack(side="left", padx=5)

        self._stop_button = ModernButton(
            inner_frame,
            text="■  Stop",
            command=self._stop_extraction,
            primary=False,
            width=100,
            tooltip="Stop the running extraction"
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
        """Handle theme change - requires restart for full effect."""
        # Update header background
        is_dark = Theme.is_dark_mode()
        self._theme_btn.config(text="🌙" if is_dark else "☀")

        # Note: Full theme change requires app restart
        # This just updates the toggle icon

    def _show_settings(self) -> None:
        """Show settings dialog."""
        # Create settings window
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("480x500")
        settings_win.configure(bg=Theme.get_color("BG_PRIMARY"))
        settings_win.transient(self.root)
        settings_win.grab_set()

        # Center on parent
        settings_win.geometry(f"+{self.root.winfo_x() + 100}+{self.root.winfo_y() + 100}")

        # Title
        header = tk.Frame(settings_win, bg=Theme.get_color("BG_PRIMARY"))
        header.pack(fill="x", padx=20, pady=20)

        tk.Label(
            header,
            text="⚙  Settings",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE - 4, "bold")
        ).pack(side="left")

        # Appearance section
        appearance_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_CARD"))
        appearance_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            appearance_frame,
            text="🎨  Appearance",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Theme toggle
        theme_row = tk.Frame(appearance_frame, bg=Theme.get_color("BG_CARD"))
        theme_row.pack(fill="x", padx=15, pady=(0, 15))

        ThemeToggle(
            theme_row,
            command=lambda is_dark: self._apply_theme(is_dark, settings_win)
        ).pack(anchor="w")

        tk.Label(
            theme_row,
            text="(Requires restart for full effect)",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(5, 0))

        # Cache section
        cache_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_CARD"))
        cache_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            cache_frame,
            text="💾  Cache Management",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            cache_frame,
            text="Cached data speeds up re-extraction of the same pages.",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        cache_btn_row = tk.Frame(cache_frame, bg=Theme.get_color("BG_CARD"))
        cache_btn_row.pack(fill="x", padx=15, pady=(0, 15))

        ModernButton(
            cache_btn_row,
            text="🗑  Clear Cache",
            command=lambda: self._clear_cache_action(settings_win),
            primary=False,
            width=140,
            tooltip="Delete all cached extraction data"
        ).pack(side="left")

        # Security section
        security_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_CARD"))
        security_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            security_frame,
            text="🔒  Security",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            security_frame,
            text="Your password is stored encrypted using Fernet encryption.",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        security_btn_row = tk.Frame(security_frame, bg=Theme.get_color("BG_CARD"))
        security_btn_row.pack(fill="x", padx=15, pady=(0, 15))

        ModernButton(
            security_btn_row,
            text="🔑  Clear Saved Credentials",
            command=lambda: self._clear_credentials_action(settings_win),
            primary=False,
            width=200,
            tooltip="Delete saved login credentials"
        ).pack(side="left")

        # Updates section
        updates_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_CARD"))
        updates_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            updates_frame,
            text="🔄  Updates",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            updates_frame,
            text=f"Current version: v{VERSION}",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", padx=15, pady=(0, 5))

        # Update status label
        self._update_status_label = tk.Label(
            updates_frame,
            text="",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        self._update_status_label.pack(anchor="w", padx=15, pady=(0, 10))

        update_btn_row = tk.Frame(updates_frame, bg=Theme.get_color("BG_CARD"))
        update_btn_row.pack(fill="x", padx=15, pady=(0, 15))

        self._check_update_btn = ModernButton(
            update_btn_row,
            text="🔍  Check for Updates",
            command=lambda: self._check_for_updates(settings_win),
            primary=False,
            width=180,
            tooltip="Check GitHub for new releases"
        )
        self._check_update_btn.pack(side="left")

        # About section
        about_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_CARD"))
        about_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            about_frame,
            text="ℹ  About",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            about_frame,
            text=f"EPLAN eVIEW Extractor v{VERSION}\n"
                 "Extracts PLC variables from EPLAN eVIEW diagrams.\n"
                 "© 2024 EPLAN Extractor Team",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        # Close button
        close_frame = tk.Frame(settings_win, bg=Theme.get_color("BG_PRIMARY"))
        close_frame.pack(fill="x", padx=20, pady=15)

        ModernButton(
            close_frame,
            text="Close",
            command=settings_win.destroy,
            primary=True,
            width=100
        ).pack(side="right")

    def _apply_theme(self, is_dark: bool, settings_win: tk.Toplevel) -> None:
        """Apply theme change."""
        Theme.set_dark_mode(is_dark)
        self._theme_btn.config(text="🌙" if is_dark else "☀")

        # Show restart message
        messagebox.showinfo(
            "Theme Changed",
            f"Theme changed to {'Dark' if is_dark else 'Light'} mode.\n\n"
            "Please restart the application for the change to take full effect.",
            parent=settings_win
        )

    def _clear_cache_action(self, parent_window: tk.Toplevel) -> None:
        """Clear cache and show confirmation."""
        count = self._cache_manager.clear()
        self._log_panel.log(f"Cleared {count} cache entries", "SUCCESS")
        messagebox.showinfo(
            "Cache Cleared",
            f"Successfully cleared {count} cache entries.",
            parent=parent_window
        )

    def _clear_credentials_action(self, parent_window: tk.Toplevel) -> None:
        """Clear saved credentials."""
        self._password_var.set("")
        config = AppConfig(
            email=self._username_var.get(),
            password_encrypted="",
            project=self._project_var.get(),
            headless=self._headless_var.get(),
            export_excel=self._export_excel_var.get(),
            export_csv=self._export_csv_var.get()
        )
        self._config_manager.save(config)
        self._log_panel.log("Cleared saved credentials", "SUCCESS")
        messagebox.showinfo(
            "Credentials Cleared",
            "Saved credentials have been removed.",
            parent=parent_window
        )

    def _check_for_updates(self, parent_window: tk.Toplevel) -> None:
        """Check for updates from GitHub releases."""
        # Update UI
        self._check_update_btn.set_enabled(False)
        self._update_status_label.config(
            text="Checking for updates...",
            fg=Theme.get_color("TEXT_MUTED")
        )
        self._logger.info("Checking for updates...")

        # Create checker and start async check
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
                text=f"Error checking for updates: {str(error)[:40]}",
                fg=Theme.get_color("ACCENT_ERROR")
            )
            self._logger.error(f"Update check failed: {error}")
            return

        if release is None:
            self._update_status_label.config(
                text="You're running the latest version!",
                fg=Theme.get_color("ACCENT_SUCCESS")
            )
            self._logger.info("Application is up to date")
            return

        # Update available
        self._update_status_label.config(
            text=f"Update available: v{release.version}",
            fg=Theme.get_color("ACCENT_WARNING")
        )
        self._logger.info(f"Update available: v{release.version}")

        # Show update dialog
        self._show_update_dialog(release, parent_window)

    def _show_update_dialog(
        self,
        release: ReleaseInfo,
        parent_window: tk.Toplevel
    ) -> None:
        """Show dialog for available update."""
        dialog = tk.Toplevel(parent_window)
        dialog.title("Update Available")
        dialog.geometry("450x400")
        dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        dialog.transient(parent_window)
        dialog.grab_set()

        # Center on parent
        dialog.geometry(f"+{parent_window.winfo_x() + 50}+{parent_window.winfo_y() + 50}")

        # Header
        header_frame = tk.Frame(dialog, bg=Theme.get_color("BG_PRIMARY"))
        header_frame.pack(fill="x", padx=20, pady=(20, 10))

        tk.Label(
            header_frame,
            text="🎉  Update Available!",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("ACCENT_SUCCESS"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING + 2, "bold")
        ).pack(anchor="w")

        # Version info
        version_frame = tk.Frame(dialog, bg=Theme.get_color("BG_CARD"))
        version_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            version_frame,
            text=f"New version: v{release.version}",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            version_frame,
            text=f"Current version: v{VERSION}",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", padx=15)

        if release.download_size > 0:
            tk.Label(
                version_frame,
                text=f"Download size: {format_size(release.download_size)}",
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("TEXT_MUTED"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
            ).pack(anchor="w", padx=15, pady=(5, 15))
        else:
            tk.Label(version_frame, text="", bg=Theme.get_color("BG_CARD")).pack(pady=(0, 10))

        # Release notes
        notes_frame = tk.Frame(dialog, bg=Theme.get_color("BG_CARD"))
        notes_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(
            notes_frame,
            text="Release Notes:",
            bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL, "bold")
        ).pack(anchor="w", padx=15, pady=(10, 5))

        # Scrollable text for release notes
        notes_text = tk.Text(
            notes_frame,
            wrap="word",
            height=8,
            bg=Theme.get_color("BG_INPUT"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            relief="flat",
            padx=10,
            pady=10
        )
        notes_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        notes_text.insert("1.0", release.body or "No release notes available.")
        notes_text.config(state="disabled")

        # Buttons
        btn_frame = tk.Frame(dialog, bg=Theme.get_color("BG_PRIMARY"))
        btn_frame.pack(fill="x", padx=20, pady=15)

        # Download/Open button
        if release.download_url:
            ModernButton(
                btn_frame,
                text="⬇  Download Update",
                command=lambda: self._download_update(release, dialog),
                primary=True,
                width=150,
                tooltip="Download the update file"
            ).pack(side="left", padx=(0, 10))

        ModernButton(
            btn_frame,
            text="🌐  View on GitHub",
            command=lambda: UpdateDownloader.open_release_page(release.html_url),
            primary=False,
            width=140,
            tooltip="Open release page in browser"
        ).pack(side="left", padx=(0, 10))

        ModernButton(
            btn_frame,
            text="Later",
            command=dialog.destroy,
            primary=False,
            width=80
        ).pack(side="right")

    def _download_update(self, release: ReleaseInfo, dialog: tk.Toplevel) -> None:
        """Download update and offer to install."""
        # Create progress dialog
        progress_dialog = tk.Toplevel(dialog)
        progress_dialog.title("Downloading Update")
        progress_dialog.geometry("350x150")
        progress_dialog.configure(bg=Theme.get_color("BG_PRIMARY"))
        progress_dialog.transient(dialog)
        progress_dialog.grab_set()

        # Center on parent
        progress_dialog.geometry(f"+{dialog.winfo_x() + 50}+{dialog.winfo_y() + 100}")

        tk.Label(
            progress_dialog,
            text="Downloading update...",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY)
        ).pack(pady=(20, 10))

        # Progress label
        progress_label = tk.Label(
            progress_dialog,
            text="0%",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        progress_label.pack(pady=5)

        # Progress bar (simple canvas-based)
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

        # Cancel button
        cancel_pressed = [False]

        def cancel_download():
            cancel_pressed[0] = True
            downloader.cancel()
            progress_dialog.destroy()

        ModernButton(
            progress_dialog,
            text="Cancel",
            command=cancel_download,
            primary=False,
            width=80
        ).pack(pady=10)

        # Progress callback
        def update_progress(downloaded: int, total: int):
            if total > 0:
                percent = int((downloaded / total) * 100)
                bar_width = int((downloaded / total) * 300)
                self.root.after(0, lambda: [
                    progress_label.config(
                        text=f"{percent}% ({format_size(downloaded)} / {format_size(total)})"
                    ),
                    progress_canvas.coords(progress_bar, 0, 0, bar_width, 20)
                ])

        # Completion callback
        def on_download_complete(file_path, error):
            if cancel_pressed[0]:
                return

            self.root.after(0, progress_dialog.destroy)

            if error:
                self.root.after(0, lambda: messagebox.showerror(
                    "Download Failed",
                    f"Failed to download update:\n{str(error)}",
                    parent=dialog
                ))
                return

            if file_path:
                self.root.after(0, lambda: self._offer_install(file_path, release, dialog))

        # Start download
        downloader = UpdateDownloader(release)
        downloader.set_progress_callback(update_progress)
        downloader.download_async(on_download_complete)

    def _offer_install(self, file_path, release: ReleaseInfo, dialog: tk.Toplevel) -> None:
        """Offer to install downloaded update."""
        result = messagebox.askyesno(
            "Download Complete",
            f"Update v{release.version} downloaded successfully!\n\n"
            f"File: {file_path}\n\n"
            "Would you like to open the installer now?\n"
            "(The application will close)",
            parent=dialog
        )

        if result:
            if UpdateDownloader.install_update(file_path):
                self._logger.info("Starting update installer...")
                dialog.destroy()
                self.root.quit()
            else:
                messagebox.showinfo(
                    "Manual Installation Required",
                    f"Please manually run the installer:\n\n{file_path}",
                    parent=dialog
                )

    def _log_callback(self, message: str, level: str) -> None:
        """Callback for logger to update GUI log."""
        try:
            self._log_panel.log(message, level)
            self.root.update_idletasks()
        except Exception:
            pass

    def _load_config(self) -> None:
        """Load saved configuration."""
        config = self._config_manager.load()

        self._username_var.set(config.email)
        self._project_var.set(config.project)
        self._headless_var.set(config.headless)
        self._export_excel_var.set(config.export_excel)
        self._export_csv_var.set(config.export_csv)

        if config.password_encrypted:
            password = self._config_manager.decrypt_password(config.password_encrypted)
            self._password_var.set(password)

    def _save_config(self) -> None:
        """Save current configuration."""
        password_encrypted = ""
        if self._save_credentials_var.get():
            password_encrypted = self._config_manager.encrypt_password(
                self._password_var.get()
            )

        config = AppConfig(
            email=self._username_var.get(),
            password_encrypted=password_encrypted,
            project=self._project_var.get(),
            headless=self._headless_var.get(),
            export_excel=self._export_excel_var.get(),
            export_csv=self._export_csv_var.get()
        )
        self._config_manager.save(config)

    def _validate_inputs(self) -> bool:
        """Validate user inputs."""
        email = self._username_var.get()
        password = self._password_var.get()
        project = self._project_var.get()

        if not email:
            self._show_error("Please enter your email address")
            self._email_entry.set_validation_state(False)
            return False

        if not validate_email(email):
            self._show_error("Please enter a valid email address")
            self._email_entry.set_validation_state(False)
            return False

        self._email_entry.set_validation_state(True)

        if not password:
            self._show_error("Please enter your password")
            return False

        if not project:
            self._show_error("Please enter a project number")
            self._project_entry.set_validation_state(False)
            return False

        self._project_entry.set_validation_state(True)
        return True

    def _show_error(self, message: str) -> None:
        """Show error message."""
        self._status_bar.set_status(message, "error")
        self._log_panel.log(message, "ERROR")

    def _start_extraction(self) -> None:
        """Start the extraction process."""
        if self._is_running:
            return

        if not self._validate_inputs():
            return

        self._save_config()

        # Update UI state
        self._is_running = True
        self._start_button.set_enabled(False)
        self._stop_button.set_enabled(True)
        self._progress_indicator.reset()
        self._status_bar.set_status("Starting extraction...", "running")

        # Start extraction thread
        thread = threading.Thread(target=self._run_extraction, daemon=True)
        thread.start()

    def _stop_extraction(self) -> None:
        """Stop the extraction process."""
        self._is_running = False
        self._status_bar.set_status("Stopping...", "running")

        if self._extractor:
            self._extractor.request_stop()

        self._start_button.set_enabled(True)
        self._stop_button.set_enabled(False)
        self._status_bar.set_status("Extraction stopped", "idle")

    def _update_progress(self, step: int, progress: float = 0.0) -> None:
        """Update progress indicator (thread-safe)."""
        self.root.after(0, lambda: self._progress_indicator.set_step(step, progress))

    def _run_extraction(self) -> None:
        """Run the extraction in a background thread."""
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
            self.root.after(0, lambda: self._status_bar.set_status("Logging in...", "running"))

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
            self.root.after(0, lambda: self._status_bar.set_status("Opening project...", "running"))

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
            self.root.after(0, lambda: self._status_bar.set_status("Extracting variables...", "running"))

            if not self._extractor.extract_variables():
                raise Exception("Extraction failed")
            self._update_progress(2, 1.0)

            if not self._is_running:
                return

            # Step 3: Export
            self._update_progress(3, 1.0)

            # Success
            output_file = f"{self._project_var.get()} IO-List.xlsx"
            self._logger.success("Extraction completed successfully!")
            self.root.after(0, lambda: self._status_bar.set_status("Extraction completed!", "success"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extraction completed!\n\nOutput: {output_file}"
            ))

        except Exception as e:
            self._logger.error(f"Extraction error: {e}")
            self.root.after(0, lambda: self._status_bar.set_status(f"Error: {str(e)[:50]}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Extraction failed:\n{str(e)}"))

        finally:
            self._is_running = False
            self._extractor = None
            self.root.after(0, lambda: self._start_button.set_enabled(True))
            self.root.after(0, lambda: self._stop_button.set_enabled(False))
