"""
Main GUI application for EPLAN eVIEW Text Extractor.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox
from typing import Optional

from ..constants import BASE_URL
from ..core.cache import CacheManager
from ..core.config import AppConfig, ConfigManager
from ..core.extractor import SeleniumEPlanExtractor
from ..utils.logging import get_logger
from .panels import LogPanel, ProgressIndicator, StatusBar
from .theme import Theme
from .widgets import ModernButton, ModernCheckbox, ModernEntry


class EPlanExtractorGUI:
    """
    Modern professional GUI for the EPLAN eVIEW Text Extractor.

    Features:
    - Dark theme with accent colors
    - Card-based layout
    - Progress step indicator
    - Animated status updates
    - Professional typography
    """

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI."""
        self.root = root
        self.root.title("EPLAN eVIEW Extractor")
        self.root.geometry("700x800")
        self.root.minsize(600, 700)
        self.root.configure(bg=Theme.BG_PRIMARY)

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

        self._setup_ui()
        self._load_config()

        # Register logger callback
        self._logger.add_callback(self._log_callback)

    def _setup_ui(self) -> None:
        """Set up the modern user interface."""
        # Main container
        main_container = tk.Frame(self.root, bg=Theme.BG_PRIMARY)
        main_container.pack(fill="both", expand=True)

        # Header
        self._create_header(main_container)

        # Content area with scrolling
        content_frame = tk.Frame(main_container, bg=Theme.BG_PRIMARY)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Credentials Card
        self._create_credentials_card(content_frame)

        # Options Card
        self._create_options_card(content_frame)

        # Progress Card
        self._create_progress_card(content_frame)

        # Action Buttons
        self._create_action_buttons(content_frame)

        # Log Panel (collapsible in future)
        self._create_log_panel(content_frame)

        # Status Bar
        self._status_bar = StatusBar(main_container)
        self._status_bar.pack(fill="x", side="bottom")

    def _create_header(self, parent: tk.Widget) -> None:
        """Create the header section."""
        header = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        header.pack(fill="x", padx=20, pady=(20, 10))

        # Logo/Title
        title_frame = tk.Frame(header, bg=Theme.BG_PRIMARY)
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text="EPLAN",
            bg=Theme.BG_PRIMARY,
            fg=Theme.ACCENT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold")
        ).pack(side="left")

        tk.Label(
            title_frame,
            text=" eVIEW Extractor",
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE)
        ).pack(side="left")

        # Settings button (placeholder)
        settings_btn = tk.Label(
            header,
            text="⚙",
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, 18),
            cursor="hand2"
        )
        settings_btn.pack(side="right", padx=10)
        settings_btn.bind("<Enter>", lambda e: settings_btn.config(fg=Theme.TEXT_PRIMARY))
        settings_btn.bind("<Leave>", lambda e: settings_btn.config(fg=Theme.TEXT_MUTED))
        settings_btn.bind("<Button-1>", lambda e: self._show_settings())

    def _create_card(self, parent: tk.Widget, title: str) -> tk.Frame:
        """Create a card container."""
        card = tk.Frame(parent, bg=Theme.BG_CARD)
        card.pack(fill="x", pady=8)

        # Title
        tk.Label(
            card,
            text=title,
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Content frame
        content = tk.Frame(card, bg=Theme.BG_CARD)
        content.pack(fill="x", padx=20, pady=(0, 15))

        return content

    def _create_credentials_card(self, parent: tk.Widget) -> None:
        """Create the credentials input card."""
        content = self._create_card(parent, "Microsoft Credentials")

        # Email
        tk.Label(
            content,
            text="Email Address",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        self._email_entry = ModernEntry(
            content,
            placeholder="your.email@company.com",
            textvariable=self._username_var
        )
        self._email_entry.pack(fill="x", pady=(0, 15))

        # Password
        tk.Label(
            content,
            text="Password",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        self._password_entry = ModernEntry(
            content,
            placeholder="Enter your password",
            show="●",
            textvariable=self._password_var
        )
        self._password_entry.pack(fill="x", pady=(0, 15))

        # Project Number
        tk.Label(
            content,
            text="Project Number",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_SECONDARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 5))

        self._project_entry = ModernEntry(
            content,
            placeholder="e.g., PROJECT-001",
            textvariable=self._project_var
        )
        self._project_entry.pack(fill="x")

    def _create_options_card(self, parent: tk.Widget) -> None:
        """Create the options card."""
        content = self._create_card(parent, "Export Options")

        options_grid = tk.Frame(content, bg=Theme.BG_CARD)
        options_grid.pack(fill="x")

        # Left column
        left_col = tk.Frame(options_grid, bg=Theme.BG_CARD)
        left_col.pack(side="left", fill="x", expand=True)

        ModernCheckbox(
            left_col,
            text="Export to Excel (.xlsx)",
            variable=self._export_excel_var
        ).pack(anchor="w", pady=3)

        ModernCheckbox(
            left_col,
            text="Export to CSV",
            variable=self._export_csv_var
        ).pack(anchor="w", pady=3)

        # Right column
        right_col = tk.Frame(options_grid, bg=Theme.BG_CARD)
        right_col.pack(side="right", fill="x", expand=True)

        ModernCheckbox(
            right_col,
            text="Run in Background (Headless)",
            variable=self._headless_var
        ).pack(anchor="w", pady=3)

    def _create_progress_card(self, parent: tk.Widget) -> None:
        """Create the progress indicator card."""
        card = tk.Frame(parent, bg=Theme.BG_CARD)
        card.pack(fill="x", pady=8)

        tk.Label(
            card,
            text="Extraction Progress",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self._progress_indicator = ProgressIndicator(card)
        self._progress_indicator.pack(fill="x", padx=20, pady=(0, 15))

    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create action buttons."""
        button_frame = tk.Frame(parent, bg=Theme.BG_PRIMARY)
        button_frame.pack(fill="x", pady=15)

        # Center the buttons
        inner_frame = tk.Frame(button_frame, bg=Theme.BG_PRIMARY)
        inner_frame.pack()

        self._start_button = ModernButton(
            inner_frame,
            text="Start Extraction",
            command=self._start_extraction,
            primary=True,
            width=160
        )
        self._start_button.pack(side="left", padx=5)

        self._stop_button = ModernButton(
            inner_frame,
            text="Stop",
            command=self._stop_extraction,
            primary=False,
            width=100
        )
        self._stop_button.pack(side="left", padx=5)
        self._stop_button.set_enabled(False)

    def _create_log_panel(self, parent: tk.Widget) -> None:
        """Create the log panel."""
        self._log_panel = LogPanel(parent)
        self._log_panel.pack(fill="both", expand=True, pady=8)

    def _show_settings(self) -> None:
        """Show settings dialog."""
        # Create settings window
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("400x300")
        settings_win.configure(bg=Theme.BG_PRIMARY)
        settings_win.transient(self.root)
        settings_win.grab_set()

        # Title
        tk.Label(
            settings_win,
            text="Settings",
            bg=Theme.BG_PRIMARY,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING, "bold")
        ).pack(pady=20)

        # Cache section
        cache_frame = tk.Frame(settings_win, bg=Theme.BG_CARD)
        cache_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(
            cache_frame,
            text="Cache Management",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_PRIMARY,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_BODY, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 5))

        tk.Label(
            cache_frame,
            text="Clear cached extraction data to force re-extraction",
            bg=Theme.BG_CARD,
            fg=Theme.TEXT_MUTED,
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", padx=15, pady=(0, 10))

        clear_cache_btn = ModernButton(
            cache_frame,
            text="Clear Cache",
            command=lambda: self._clear_cache_action(settings_win),
            primary=False,
            width=120
        )
        clear_cache_btn.pack(anchor="w", padx=15, pady=(0, 15))

    def _clear_cache_action(self, parent_window: tk.Toplevel) -> None:
        """Clear cache and show confirmation."""
        count = self._cache_manager.clear()
        self._log_panel.log(f"Cleared {count} cache entries", "SUCCESS")
        parent_window.destroy()

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
        config = AppConfig(
            email=self._username_var.get(),
            password_encrypted=self._config_manager.encrypt_password(
                self._password_var.get()
            ),
            project=self._project_var.get(),
            headless=self._headless_var.get(),
            export_excel=self._export_excel_var.get(),
            export_csv=self._export_csv_var.get()
        )
        self._config_manager.save(config)

    def _validate_inputs(self) -> bool:
        """Validate user inputs."""
        if not self._username_var.get():
            self._show_error("Please enter your email address")
            return False
        if not self._password_var.get():
            self._show_error("Please enter your password")
            return False
        if not self._project_var.get():
            self._show_error("Please enter a project number")
            return False
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
            self._logger.success("Extraction completed successfully!")
            self.root.after(0, lambda: self._status_bar.set_status("Extraction completed!", "success"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Extraction completed!\n\nOutput: {self._project_var.get()} IO-List.xlsx"
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
