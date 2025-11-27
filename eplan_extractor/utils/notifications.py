"""
Desktop notifications module for cross-platform notifications.
"""

import platform
import subprocess
import threading
from typing import Optional

from .i18n import t


class NotificationManager:
    """Cross-platform desktop notification manager."""

    _enabled: bool = True

    @classmethod
    def set_enabled(cls, enabled: bool) -> None:
        """Enable or disable notifications."""
        cls._enabled = enabled

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if notifications are enabled."""
        return cls._enabled

    @classmethod
    def notify(
        cls,
        title: str,
        message: str,
        icon: Optional[str] = None,
        timeout: int = 5000
    ) -> bool:
        """
        Show a desktop notification.

        Args:
            title: Notification title
            message: Notification message
            icon: Path to icon file (optional)
            timeout: Display duration in milliseconds

        Returns:
            True if notification was sent successfully
        """
        if not cls._enabled:
            return False

        system = platform.system().lower()

        try:
            if system == "windows":
                return cls._notify_windows(title, message, icon, timeout)
            elif system == "darwin":
                return cls._notify_macos(title, message, icon)
            else:  # Linux
                return cls._notify_linux(title, message, icon, timeout)
        except Exception:
            return False

    @classmethod
    def notify_async(
        cls,
        title: str,
        message: str,
        icon: Optional[str] = None,
        timeout: int = 5000
    ) -> None:
        """Show notification asynchronously."""
        thread = threading.Thread(
            target=cls.notify,
            args=(title, message, icon, timeout),
            daemon=True
        )
        thread.start()

    @classmethod
    def _notify_windows(
        cls,
        title: str,
        message: str,
        icon: Optional[str],
        timeout: int
    ) -> bool:
        """Windows notification using Windows Toast."""
        try:
            # Try using win10toast if available
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                title,
                message,
                icon_path=icon,
                duration=timeout // 1000,
                threaded=True
            )
            return True
        except ImportError:
            pass

        try:
            # Fallback to PowerShell
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
            </toast>
"@

            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("EPLAN Extractor").Show($toast)
            '''

            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception:
            return False

    @classmethod
    def _notify_macos(
        cls,
        title: str,
        message: str,
        icon: Optional[str]
    ) -> bool:
        """macOS notification using osascript."""
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception:
            return False

    @classmethod
    def _notify_linux(
        cls,
        title: str,
        message: str,
        icon: Optional[str],
        timeout: int
    ) -> bool:
        """Linux notification using notify-send."""
        try:
            cmd = ["notify-send", title, message]

            if icon:
                cmd.extend(["-i", icon])

            cmd.extend(["-t", str(timeout)])

            subprocess.run(cmd, capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    # =========================================================================
    # Convenience methods for common notifications
    # =========================================================================

    @classmethod
    def notify_extraction_complete(
        cls,
        project: str,
        variables_count: int,
        output_file: str
    ) -> None:
        """Notify that extraction completed successfully."""
        cls.notify_async(
            title=t("app_title"),
            message=f"Extraction of '{project}' completed.\n"
                    f"{variables_count} variables exported to {output_file}"
        )

    @classmethod
    def notify_extraction_failed(cls, project: str, error: str) -> None:
        """Notify that extraction failed."""
        cls.notify_async(
            title=t("app_title"),
            message=f"Extraction of '{project}' failed.\nError: {error[:50]}"
        )

    @classmethod
    def notify_update_available(cls, version: str) -> None:
        """Notify that an update is available."""
        cls.notify_async(
            title=t("app_title"),
            message=t("update_available", version=version)
        )
