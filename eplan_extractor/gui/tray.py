"""
System tray integration for background operation.
"""

import threading
import tkinter as tk
from typing import Callable, Optional

from .theme import Theme
from ..utils.i18n import t


class SystemTray:
    """
    System tray manager for background operation.

    Uses pystray for cross-platform tray support.
    Falls back gracefully if pystray is not available.
    """

    def __init__(
        self,
        root: tk.Tk,
        on_show: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None
    ) -> None:
        """
        Initialize system tray.

        Args:
            root: The main tkinter window
            on_show: Callback when "Show" is clicked
            on_quit: Callback when "Quit" is clicked
            on_start: Callback when "Start Extraction" is clicked
            on_stop: Callback when "Stop Extraction" is clicked
        """
        self._root = root
        self._on_show = on_show
        self._on_quit = on_quit
        self._on_start = on_start
        self._on_stop = on_stop
        self._icon = None
        self._available = False
        self._enabled = False
        self._is_running = False

        self._check_availability()

    def _check_availability(self) -> None:
        """Check if system tray is available."""
        try:
            import pystray
            from PIL import Image
            self._available = True
        except ImportError:
            self._available = False

    def is_available(self) -> bool:
        """Check if system tray functionality is available."""
        return self._available

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable system tray."""
        self._enabled = enabled and self._available

    def is_enabled(self) -> bool:
        """Check if system tray is enabled."""
        return self._enabled

    def set_running_state(self, is_running: bool) -> None:
        """Update the running state for menu items."""
        self._is_running = is_running
        self._update_menu()

    def _create_icon_image(self, size: int = 64):
        """Create a simple icon image."""
        try:
            from PIL import Image, ImageDraw

            # Create a simple "E" icon
            image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)

            # Background circle
            bg_color = (41, 128, 185) if Theme.is_dark_mode() else (52, 152, 219)
            draw.ellipse([2, 2, size - 2, size - 2], fill=bg_color)

            # Letter "E"
            text_color = (255, 255, 255)
            font_size = size // 2

            # Draw simple E shape
            margin = size // 5
            thickness = size // 8

            # Vertical bar
            draw.rectangle([margin, margin, margin + thickness, size - margin], fill=text_color)
            # Top bar
            draw.rectangle([margin, margin, size - margin, margin + thickness], fill=text_color)
            # Middle bar
            mid = size // 2
            draw.rectangle([margin, mid - thickness // 2, size - margin - thickness, mid + thickness // 2], fill=text_color)
            # Bottom bar
            draw.rectangle([margin, size - margin - thickness, size - margin, size - margin], fill=text_color)

            return image

        except ImportError:
            return None

    def _create_menu(self):
        """Create the tray menu."""
        try:
            import pystray

            def show_window(icon, item):
                if self._on_show:
                    self._root.after(0, self._on_show)

            def start_extraction(icon, item):
                if self._on_start and not self._is_running:
                    self._root.after(0, self._on_start)

            def stop_extraction(icon, item):
                if self._on_stop and self._is_running:
                    self._root.after(0, self._on_stop)

            def quit_app(icon, item):
                if self._on_quit:
                    self._root.after(0, self._on_quit)

            menu = pystray.Menu(
                pystray.MenuItem(
                    t("app_title"),
                    show_window,
                    default=True
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    t("start_extraction"),
                    start_extraction,
                    enabled=lambda item: not self._is_running
                ),
                pystray.MenuItem(
                    t("stop"),
                    stop_extraction,
                    enabled=lambda item: self._is_running
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    t("close"),
                    quit_app
                )
            )

            return menu

        except ImportError:
            return None

    def _update_menu(self) -> None:
        """Update the menu (refresh enabled states)."""
        if self._icon:
            try:
                self._icon.update_menu()
            except Exception:
                pass

    def start(self) -> bool:
        """
        Start the system tray icon.

        Returns:
            True if started successfully
        """
        if not self._available or not self._enabled:
            return False

        try:
            import pystray

            image = self._create_icon_image()
            if image is None:
                return False

            menu = self._create_menu()

            self._icon = pystray.Icon(
                "eplan_extractor",
                image,
                t("app_title"),
                menu
            )

            # Run in separate thread
            thread = threading.Thread(target=self._icon.run, daemon=True)
            thread.start()

            return True

        except Exception:
            return False

    def stop(self) -> None:
        """Stop the system tray icon."""
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

    def minimize_to_tray(self) -> bool:
        """
        Minimize the window to system tray.

        Returns:
            True if successful
        """
        if not self._enabled or self._icon is None:
            return False

        try:
            self._root.withdraw()
            return True
        except Exception:
            return False

    def restore_from_tray(self) -> bool:
        """
        Restore the window from system tray.

        Returns:
            True if successful
        """
        try:
            self._root.deiconify()
            self._root.lift()
            self._root.focus_force()
            return True
        except Exception:
            return False

    def set_tooltip(self, text: str) -> None:
        """Set the tray icon tooltip."""
        if self._icon:
            try:
                self._icon.title = text
            except Exception:
                pass


class TrayMinimizeBehavior:
    """
    Mixin behavior for handling minimize-to-tray.

    Add this to your main window class to handle minimize events.
    """

    def setup_tray_behavior(
        self,
        root: tk.Tk,
        tray: SystemTray,
        minimize_to_tray: bool = False
    ) -> None:
        """Set up minimize-to-tray behavior."""
        self._tray = tray
        self._minimize_to_tray = minimize_to_tray

        if minimize_to_tray and tray.is_available():
            # Override window close to minimize instead
            root.protocol("WM_DELETE_WINDOW", self._on_close_request)

            # Handle minimize event
            root.bind("<Unmap>", self._on_minimize)

    def _on_close_request(self) -> None:
        """Handle window close request."""
        if self._minimize_to_tray and self._tray.is_enabled():
            self._tray.minimize_to_tray()
        else:
            self._tray.stop()
            self._root.destroy()

    def _on_minimize(self, event) -> None:
        """Handle minimize event."""
        if self._minimize_to_tray and self._tray.is_enabled():
            # Check if actually minimized (not just focus lost)
            if self._root.state() == 'iconic':
                self._tray.minimize_to_tray()
