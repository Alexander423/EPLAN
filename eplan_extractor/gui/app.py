"""
EPLAN eVIEW Text Extractor - Clean Professional GUI
"""

from __future__ import annotations

import re
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Optional

from ..constants import BASE_URL, VERSION
from ..core.cache import CacheManager
from ..core.config import AppConfig, ConfigManager, ExtractionRecord
from ..core.extractor import SeleniumEPlanExtractor
from ..core.updater import UpdateChecker, UpdateDownloader, ReleaseInfo
from ..utils.logging import get_logger
from ..utils.i18n import I18n
from ..utils.notifications import NotificationManager
from .panels import LogPanel, ProgressIndicator, StatusBar
from .theme import Theme
from .tray import SystemTray
from .widgets import ModernButton, ModernCheckbox, ModernEntry, PasswordEntry, ThemeToggle


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


class EPlanExtractorGUI:
    """Clean, professional GUI for EPLAN eVIEW extraction."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EPLAN eVIEW Extractor")
        self.root.geometry("560x680")
        self.root.minsize(480, 600)
        self.root.configure(bg=Theme.get_color("BG_PRIMARY"))

        self._logger = get_logger()
        self._config_manager = ConfigManager()
        self._cache_manager = CacheManager()
        self._extractor: Optional[SeleniumEPlanExtractor] = None
        self._is_running = False
        self._extraction_start_time = 0.0

        # Variables
        self._email_var = tk.StringVar()
        self._password_var = tk.StringVar()
        self._project_var = tk.StringVar()
        self._headless_var = tk.BooleanVar(value=True)
        self._export_excel_var = tk.BooleanVar(value=True)
        self._export_csv_var = tk.BooleanVar(value=False)

        # Load config
        self._config = self._config_manager.load()
        I18n.set_language(self._config.language)
        NotificationManager.set_enabled(self._config.show_notifications)

        # System tray
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
        self._load_config()
        self._setup_bindings()

        self._logger.add_callback(self._log_callback)
        Theme.add_observer(self._on_theme_change)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Startup update check
        if self._config.check_updates_on_startup:
            self.root.after(2000, self._check_updates_silent)

    def _setup_bindings(self) -> None:
        self.root.bind("<Control-Return>", lambda e: self._start_extraction())
        self.root.bind("<Escape>", lambda e: self._stop_extraction() if self._is_running else None)
        self.root.bind("<Control-comma>", lambda e: self._show_settings())
        self.root.bind("<Control-q>", lambda e: self._quit_app())

    def _setup_ui(self) -> None:
        main = tk.Frame(self.root, bg=Theme.get_color("BG_PRIMARY"))
        main.pack(fill="both", expand=True)

        self._create_header(main)

        content = tk.Frame(main, bg=Theme.get_color("BG_PRIMARY"))
        content.pack(fill="both", expand=True, padx=24, pady=16)

        self._create_form(content)
        self._create_progress(content)
        self._create_buttons(content)

        self._log_panel = LogPanel(content)
        self._log_panel.pack(fill="both", expand=True, pady=(16, 0))

        self._status_bar = StatusBar(main)
        self._status_bar.pack(fill="x", side="bottom")

    def _create_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=Theme.get_color("BG_PRIMARY"))
        header.pack(fill="x", padx=24, pady=(20, 8))

        tk.Label(
            header, text="EPLAN eVIEW Extractor",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE, "bold")
        ).pack(side="left")

        settings_btn = tk.Label(
            header, text="Settings",
            bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
            cursor="hand2"
        )
        settings_btn.pack(side="right")
        settings_btn.bind("<Button-1>", lambda e: self._show_settings())
        settings_btn.bind("<Enter>", lambda e: settings_btn.config(fg=Theme.get_color("TEXT_PRIMARY")))
        settings_btn.bind("<Leave>", lambda e: settings_btn.config(fg=Theme.get_color("TEXT_MUTED")))

    def _create_form(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        card.pack(fill="x", pady=(0, 16))

        inner = tk.Frame(card, bg=Theme.get_color("BG_CARD"))
        inner.pack(fill="x", padx=20, pady=20)

        # Email
        self._create_field(inner, "Email", self._email_var, "email@company.com", validate_email)

        # Password
        tk.Label(
            inner, text="Password", bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(12, 4))

        self._password_entry = PasswordEntry(inner, textvariable=self._password_var)
        self._password_entry.pack(fill="x")

        # Project
        tk.Label(
            inner, text="Project Number", bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(12, 4))

        project_frame = tk.Frame(inner, bg=Theme.get_color("BG_CARD"))
        project_frame.pack(fill="x")

        self._project_entry = ModernEntry(
            project_frame, placeholder="e.g. PROJECT-001",
            textvariable=self._project_var
        )
        self._project_entry.pack(side="left", fill="x", expand=True)

        recent = self._config_manager.get_recent_projects()
        if recent:
            recent_btn = tk.Label(
                project_frame, text="Recent",
                bg=Theme.get_color("BG_CARD"),
                fg=Theme.get_color("TEXT_MUTED"),
                font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL),
                cursor="hand2"
            )
            recent_btn.pack(side="right", padx=(8, 0))
            recent_btn.bind("<Button-1>", self._show_recent)

        # Options
        opts = tk.Frame(inner, bg=Theme.get_color("BG_CARD"))
        opts.pack(fill="x", pady=(16, 0))

        ModernCheckbox(opts, text="Excel", variable=self._export_excel_var).pack(side="left")
        ModernCheckbox(opts, text="CSV", variable=self._export_csv_var).pack(side="left", padx=(16, 0))
        tk.Frame(opts, bg=Theme.get_color("BG_CARD"), width=32).pack(side="left")
        ModernCheckbox(opts, text="Background", variable=self._headless_var).pack(side="left")

    def _create_field(self, parent, label, var, placeholder="", validate=None) -> None:
        tk.Label(
            parent, text=label, bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_SECONDARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 4))

        ModernEntry(
            parent, placeholder=placeholder,
            textvariable=var, validate_func=validate
        ).pack(fill="x")

    def _create_progress(self, parent: tk.Widget) -> None:
        card = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        card.pack(fill="x", pady=(0, 16))

        self._progress = ProgressIndicator(card)
        self._progress.pack(fill="x", padx=16, pady=16)

    def _create_buttons(self, parent: tk.Widget) -> None:
        frame = tk.Frame(parent, bg=Theme.get_color("BG_PRIMARY"))
        frame.pack(fill="x")

        center = tk.Frame(frame, bg=Theme.get_color("BG_PRIMARY"))
        center.pack()

        self._start_btn = ModernButton(
            center, text="Start Extraction",
            command=self._start_extraction, primary=True, width=140
        )
        self._start_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = ModernButton(
            center, text="Stop",
            command=self._stop_extraction, primary=False, width=80
        )
        self._stop_btn.pack(side="left")
        self._stop_btn.set_enabled(False)

    def _show_recent(self, event: tk.Event) -> None:
        recent = self._config_manager.get_recent_projects()
        if not recent:
            return
        menu = tk.Menu(self.root, tearoff=0)
        for p in recent[:8]:
            menu.add_command(label=p, command=lambda x=p: self._project_var.set(x))
        menu.post(event.x_root, event.y_root)

    def _show_settings(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.geometry("400x480")
        win.configure(bg=Theme.get_color("BG_PRIMARY"))
        win.transient(self.root)
        win.grab_set()

        canvas = tk.Canvas(win, bg=Theme.get_color("BG_PRIMARY"), highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=Theme.get_color("BG_PRIMARY"))

        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=content, anchor="nw", width=380)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(
            content, text="Settings", bg=Theme.get_color("BG_PRIMARY"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_TITLE - 2, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 16))

        self._section(content, "Appearance", self._appearance_settings)
        self._section(content, "Updates", lambda p: self._update_settings(p, win))
        self._section(content, "Cache", lambda p: self._cache_settings(p, win))
        self._section(content, "About", self._about_settings)

        close_frame = tk.Frame(win, bg=Theme.get_color("BG_PRIMARY"))
        close_frame.pack(fill="x", side="bottom", padx=20, pady=16)
        ModernButton(close_frame, text="Close", command=win.destroy, primary=True, width=80).pack(side="right")

    def _section(self, parent, title, fn) -> None:
        frame = tk.Frame(parent, bg=Theme.get_color("BG_CARD"))
        frame.pack(fill="x", padx=20, pady=4)

        tk.Label(
            frame, text=title, bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_PRIMARY"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_HEADING)
        ).pack(anchor="w", padx=16, pady=(12, 8))

        inner = tk.Frame(frame, bg=Theme.get_color("BG_CARD"))
        inner.pack(fill="x", padx=16, pady=(0, 12))
        fn(inner)

    def _appearance_settings(self, parent) -> None:
        ThemeToggle(parent, command=self._on_theme_toggle).pack(anchor="w")

    def _on_theme_toggle(self, is_dark: bool) -> None:
        Theme.set_dark_mode(is_dark)
        self._config.dark_mode = is_dark
        self._config_manager.save(self._config)

    def _update_settings(self, parent, win) -> None:
        tk.Label(
            parent, text=f"Version {VERSION}",
            bg=Theme.get_color("BG_CARD"), fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 8))

        self._update_lbl = tk.Label(
            parent, text="", bg=Theme.get_color("BG_CARD"),
            fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        )
        self._update_lbl.pack(anchor="w", pady=(0, 8))

        ModernButton(
            parent, text="Check updates",
            command=lambda: self._check_updates(win), primary=False, width=110
        ).pack(anchor="w")

    def _cache_settings(self, parent, win) -> None:
        tk.Label(
            parent, text="Clear cached data",
            bg=Theme.get_color("BG_CARD"), fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL)
        ).pack(anchor="w", pady=(0, 8))

        ModernButton(
            parent, text="Clear cache",
            command=lambda: self._clear_cache(win), primary=False, width=100
        ).pack(anchor="w")

    def _about_settings(self, parent) -> None:
        tk.Label(
            parent,
            text=f"EPLAN eVIEW Extractor v{VERSION}\nExtracts PLC variables from EPLAN diagrams",
            bg=Theme.get_color("BG_CARD"), fg=Theme.get_color("TEXT_MUTED"),
            font=(Theme.FONT_FAMILY, Theme.FONT_SIZE_SMALL), justify="left"
        ).pack(anchor="w")

    def _clear_cache(self, win) -> None:
        count = self._cache_manager.clear()
        messagebox.showinfo("Cache", f"Cleared {count} entries", parent=win)

    def _check_updates(self, win) -> None:
        self._update_lbl.config(text="Checking...", fg=Theme.get_color("TEXT_MUTED"))

        def check():
            try:
                release = UpdateChecker().check_for_updates()
                self.root.after(0, lambda: self._update_result(release, win))
            except:
                self.root.after(0, lambda: self._update_lbl.config(
                    text="Check failed", fg=Theme.get_color("ACCENT_ERROR")
                ))

        threading.Thread(target=check, daemon=True).start()

    def _update_result(self, release, win) -> None:
        if release:
            self._update_lbl.config(text=f"v{release.version} available", fg=Theme.get_color("ACCENT_SUCCESS"))
            if messagebox.askyesno("Update", f"v{release.version} available.\nOpen page?", parent=win):
                UpdateDownloader.open_release_page(release.html_url)
        else:
            self._update_lbl.config(text="Up to date", fg=Theme.get_color("ACCENT_SUCCESS"))

    def _check_updates_silent(self) -> None:
        def check():
            try:
                release = UpdateChecker().check_for_updates()
                if release:
                    self.root.after(0, lambda: self._status_bar.set_status(
                        f"Update: v{release.version}", "info"
                    ))
            except:
                pass
        threading.Thread(target=check, daemon=True).start()

    def _on_theme_change(self) -> None:
        pass

    def _on_close(self) -> None:
        if self._config.minimize_to_tray and self._tray.is_enabled():
            self._tray.minimize_to_tray()
        else:
            self._quit_app()

    def _restore_window(self) -> None:
        self._tray.restore_from_tray()

    def _quit_app(self) -> None:
        if self._is_running:
            if not messagebox.askyesno("Quit", "Extraction running. Quit?"):
                return
            self._stop_extraction()
        self._tray.stop()
        self.root.destroy()

    def _log_callback(self, msg: str, level: str) -> None:
        try:
            self._log_panel.log(msg, level)
            self.root.update_idletasks()
        except:
            pass

    def _load_config(self) -> None:
        self._email_var.set(self._config.email)
        self._project_var.set(self._config.project)
        self._headless_var.set(self._config.headless)
        self._export_excel_var.set(self._config.export_excel)
        self._export_csv_var.set(self._config.export_csv)

        if self._config.password_encrypted:
            self._password_var.set(
                self._config_manager.decrypt_password(self._config.password_encrypted)
            )

        Theme.set_dark_mode(self._config.dark_mode)

    def _save_config(self) -> None:
        self._config.email = self._email_var.get()
        self._config.password_encrypted = self._config_manager.encrypt_password(self._password_var.get())
        self._config.project = self._project_var.get()
        self._config.headless = self._headless_var.get()
        self._config.export_excel = self._export_excel_var.get()
        self._config.export_csv = self._export_csv_var.get()
        self._config_manager.save(self._config)

    def _validate(self) -> bool:
        if not self._email_var.get():
            self._status_bar.set_status("Email required", "error")
            return False
        if not validate_email(self._email_var.get()):
            self._status_bar.set_status("Invalid email", "error")
            return False
        if not self._password_var.get():
            self._status_bar.set_status("Password required", "error")
            return False
        if not self._project_var.get():
            self._status_bar.set_status("Project required", "error")
            return False
        return True

    def _start_extraction(self) -> None:
        if self._is_running:
            return
        if not self._validate():
            return

        self._save_config()
        self._config_manager.add_recent_project(self._project_var.get())

        self._is_running = True
        self._extraction_start_time = time.time()
        self._start_btn.set_enabled(False)
        self._stop_btn.set_enabled(True)
        self._progress.reset()
        self._status_bar.set_status("Starting...", "running")
        self._tray.set_running_state(True)

        threading.Thread(target=self._run, daemon=True).start()

    def _stop_extraction(self) -> None:
        self._is_running = False
        self._status_bar.set_status("Stopped", "idle")
        if self._extractor:
            self._extractor.request_stop()
        self._start_btn.set_enabled(True)
        self._stop_btn.set_enabled(False)
        self._tray.set_running_state(False)

    def _update_step(self, step: int, prog: float = 0.0) -> None:
        self.root.after(0, lambda: self._progress.set_step(step, prog))

    def _run(self) -> None:
        pages, variables, output, success, error = 0, 0, "", False, ""

        try:
            self._logger.info("Starting extraction...")

            self._extractor = SeleniumEPlanExtractor(
                base_url=BASE_URL,
                username=self._email_var.get(),
                password=self._password_var.get(),
                project_number=self._project_var.get(),
                headless=self._headless_var.get(),
                cache_manager=self._cache_manager
            )

            # Login
            self._update_step(0, 0.0)
            self.root.after(0, lambda: self._status_bar.set_status("Logging in...", "running"))

            self._extractor.setup_driver()
            self._update_step(0, 0.3)

            if not self._extractor.click_on_login_with_microsoft():
                raise Exception("Login button not found")
            self._update_step(0, 0.6)

            if not self._extractor.login():
                raise Exception("Login failed")
            self._update_step(0, 1.0)

            if not self._is_running:
                return

            # Project
            self._update_step(1, 0.0)
            self.root.after(0, lambda: self._status_bar.set_status("Opening project...", "running"))

            if not self._extractor.open_project():
                raise Exception("Failed to open project")
            self._update_step(1, 0.5)

            if not self._extractor.switch_to_list_view():
                raise Exception("View switch failed")
            self._update_step(1, 1.0)

            if not self._is_running:
                return

            # Extract
            self._update_step(2, 0.0)
            self.root.after(0, lambda: self._status_bar.set_status("Extracting...", "running"))

            if not self._extractor.extract_variables():
                raise Exception("Extraction failed")
            self._update_step(2, 1.0)

            if not self._is_running:
                return

            # Done
            self._update_step(3, 1.0)

            pages = getattr(self._extractor, '_pages_processed', 0)
            variables = getattr(self._extractor, '_variables_found', 0)
            output = f"{self._project_var.get()} IO-List.xlsx"
            success = True

            self._logger.success("Complete")
            self.root.after(0, lambda: self._status_bar.set_status("Complete", "success"))
            self.root.after(0, lambda: messagebox.showinfo("Done", f"{variables} variables exported"))

            NotificationManager.notify_extraction_complete(self._project_var.get(), variables, output)

        except Exception as e:
            error = str(e)
            self._logger.error(str(e))
            self.root.after(0, lambda: self._status_bar.set_status(f"Error: {str(e)[:30]}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            NotificationManager.notify_extraction_failed(self._project_var.get(), error)

        finally:
            self._config_manager.add_history_entry(ExtractionRecord(
                project=self._project_var.get(),
                timestamp=datetime.now().isoformat(),
                duration_seconds=time.time() - self._extraction_start_time,
                pages_extracted=pages,
                variables_found=variables,
                output_file=output,
                success=success,
                error_message=error
            ))

            self._is_running = False
            self._extractor = None
            self.root.after(0, lambda: self._start_btn.set_enabled(True))
            self.root.after(0, lambda: self._stop_btn.set_enabled(False))
            self.root.after(0, lambda: self._tray.set_running_state(False))
