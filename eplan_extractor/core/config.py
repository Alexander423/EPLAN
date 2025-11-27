"""
Configuration management with encrypted credential storage.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Optional encryption - fall back to base64 if not available
HAS_CRYPTO = False
Fernet = None
InvalidToken = Exception

def _try_import_crypto():
    """Try to import cryptography safely."""
    global HAS_CRYPTO, Fernet, InvalidToken
    try:
        import importlib.util
        spec = importlib.util.find_spec("cryptography")
        if spec is None:
            return
        # Try importing in a subprocess to avoid crash
        import subprocess
        result = subprocess.run(
            ["python3", "-c", "from cryptography.fernet import Fernet"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            from cryptography.fernet import Fernet as F, InvalidToken as IT
            HAS_CRYPTO = True
            Fernet = F
            InvalidToken = IT
    except Exception:
        pass

_try_import_crypto()

from ..utils.logging import get_logger


@dataclass
class AppConfig:
    """Application configuration data class."""
    # Credentials
    email: str = ""
    password_encrypted: str = ""
    project: str = ""

    # Export options
    headless: bool = True
    export_excel: bool = True
    export_csv: bool = False
    export_json: bool = False
    export_directory: str = ""

    # UI preferences
    dark_mode: bool = True
    language: str = "en"  # "en" or "de"
    check_updates_on_startup: bool = True
    minimize_to_tray: bool = False
    show_notifications: bool = True

    # Network
    proxy_enabled: bool = False
    proxy_host: str = ""
    proxy_port: int = 8080
    proxy_username: str = ""
    proxy_password_encrypted: str = ""

    # Recent projects (max 10)
    recent_projects: List[str] = field(default_factory=list)


@dataclass
class ExtractionRecord:
    """Record of a past extraction."""
    project: str
    timestamp: str
    duration_seconds: float
    pages_extracted: int
    variables_found: int
    output_file: str
    success: bool
    error_message: str = ""


class ConfigManager:
    """
    Manages application configuration with encrypted credential storage.

    Uses Fernet symmetric encryption for password storage.
    """

    CONFIG_FILE: str = "eplan_config.json"
    KEY_FILE: str = "fernet.key"
    HISTORY_FILE: str = "eplan_history.json"
    MAX_RECENT_PROJECTS: int = 10
    MAX_HISTORY_ENTRIES: int = 100

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._logger = get_logger()
        self._fernet: Optional[Fernet] = None
        self._config = AppConfig()
        self._history: List[ExtractionRecord] = []
        self._setup_encryption()

    def _setup_encryption(self) -> None:
        """Set up Fernet encryption key."""
        if not HAS_CRYPTO:
            self._logger.warning("cryptography not available - passwords stored as base64")
            self._fernet = None
            return

        key_path = Path(self.KEY_FILE)

        try:
            if key_path.exists():
                key = key_path.read_bytes()
            else:
                self._logger.info("Generating new encryption key...")
                key = Fernet.generate_key()
                key_path.write_bytes(key)

            self._fernet = Fernet(key)
        except Exception as e:
            self._logger.warning(f"Encryption setup failed, using base64: {e}")
            self._fernet = None

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.

        Args:
            password: Plain text password

        Returns:
            Base64-encoded encrypted password
        """
        if not self._fernet:
            # Fallback to base64 encoding (not secure, but functional)
            return base64.b64encode(password.encode()).decode()

        encrypted = self._fernet.encrypt(password.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt_password(self, encrypted: str) -> str:
        """
        Decrypt a password.

        Args:
            encrypted: Base64-encoded encrypted password

        Returns:
            Plain text password
        """
        if not encrypted:
            return ""

        if not self._fernet:
            # Fallback from base64 encoding
            try:
                return base64.b64decode(encrypted).decode()
            except Exception:
                return ""

        try:
            encrypted_bytes = base64.b64decode(encrypted)
            return self._fernet.decrypt(encrypted_bytes).decode()
        except (InvalidToken, Exception) as e:
            self._logger.error(f"Failed to decrypt password: {e}")
            return ""

    def load(self) -> AppConfig:
        """
        Load configuration from file.

        Returns:
            Loaded configuration
        """
        config_path = Path(self.CONFIG_FILE)

        if not config_path.exists():
            self._logger.debug("No configuration file found")
            return self._config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._config = AppConfig(
                email=data.get("email", ""),
                password_encrypted=data.get("password", ""),
                project=data.get("project", ""),
                headless=data.get("headless", True),
                export_excel=data.get("export_excel", True),
                export_csv=data.get("export_csv", False),
                export_json=data.get("export_json", False),
                export_directory=data.get("export_directory", ""),
                dark_mode=data.get("dark_mode", True),
                language=data.get("language", "en"),
                check_updates_on_startup=data.get("check_updates_on_startup", True),
                minimize_to_tray=data.get("minimize_to_tray", False),
                show_notifications=data.get("show_notifications", True),
                proxy_enabled=data.get("proxy_enabled", False),
                proxy_host=data.get("proxy_host", ""),
                proxy_port=data.get("proxy_port", 8080),
                proxy_username=data.get("proxy_username", ""),
                proxy_password_encrypted=data.get("proxy_password", ""),
                recent_projects=data.get("recent_projects", [])[:self.MAX_RECENT_PROJECTS]
            )

            self._logger.info("Configuration loaded successfully")
            return self._config

        except (json.JSONDecodeError, IOError) as e:
            self._logger.error(f"Failed to load configuration: {e}")
            return self._config

    def save(self, config: AppConfig) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration to save

        Returns:
            True if successful
        """
        try:
            data = {
                "email": config.email,
                "password": config.password_encrypted,
                "project": config.project,
                "headless": config.headless,
                "export_excel": config.export_excel,
                "export_csv": config.export_csv,
                "export_json": config.export_json,
                "export_directory": config.export_directory,
                "dark_mode": config.dark_mode,
                "language": config.language,
                "check_updates_on_startup": config.check_updates_on_startup,
                "minimize_to_tray": config.minimize_to_tray,
                "show_notifications": config.show_notifications,
                "proxy_enabled": config.proxy_enabled,
                "proxy_host": config.proxy_host,
                "proxy_port": config.proxy_port,
                "proxy_username": config.proxy_username,
                "proxy_password": config.proxy_password_encrypted,
                "recent_projects": config.recent_projects[:self.MAX_RECENT_PROJECTS]
            }

            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._config = config
            self._logger.info("Configuration saved successfully")
            return True

        except IOError as e:
            self._logger.error(f"Failed to save configuration: {e}")
            return False

    def add_recent_project(self, project: str) -> None:
        """Add a project to the recent projects list."""
        if not project:
            return

        # Remove if already exists
        if project in self._config.recent_projects:
            self._config.recent_projects.remove(project)

        # Add to front
        self._config.recent_projects.insert(0, project)

        # Trim to max
        self._config.recent_projects = self._config.recent_projects[:self.MAX_RECENT_PROJECTS]

        # Auto-save
        self.save(self._config)

    def get_recent_projects(self) -> List[str]:
        """Get list of recent projects."""
        return self._config.recent_projects.copy()

    # =========================================================================
    # History Management
    # =========================================================================

    def load_history(self) -> List[ExtractionRecord]:
        """Load extraction history from file."""
        history_path = Path(self.HISTORY_FILE)

        if not history_path.exists():
            return []

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._history = [
                ExtractionRecord(
                    project=entry.get("project", ""),
                    timestamp=entry.get("timestamp", ""),
                    duration_seconds=entry.get("duration_seconds", 0),
                    pages_extracted=entry.get("pages_extracted", 0),
                    variables_found=entry.get("variables_found", 0),
                    output_file=entry.get("output_file", ""),
                    success=entry.get("success", False),
                    error_message=entry.get("error_message", "")
                )
                for entry in data
            ]

            return self._history

        except (json.JSONDecodeError, IOError) as e:
            self._logger.error(f"Failed to load history: {e}")
            return []

    def add_history_entry(self, record: ExtractionRecord) -> None:
        """Add an extraction record to history."""
        self._history.insert(0, record)

        # Trim to max
        self._history = self._history[:self.MAX_HISTORY_ENTRIES]

        # Save
        self._save_history()

    def _save_history(self) -> bool:
        """Save history to file."""
        try:
            data = [
                {
                    "project": record.project,
                    "timestamp": record.timestamp,
                    "duration_seconds": record.duration_seconds,
                    "pages_extracted": record.pages_extracted,
                    "variables_found": record.variables_found,
                    "output_file": record.output_file,
                    "success": record.success,
                    "error_message": record.error_message
                }
                for record in self._history
            ]

            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True

        except IOError as e:
            self._logger.error(f"Failed to save history: {e}")
            return False

    def clear_history(self) -> int:
        """Clear extraction history. Returns number of entries cleared."""
        count = len(self._history)
        self._history = []
        self._save_history()
        return count

    def get_history(self) -> List[ExtractionRecord]:
        """Get extraction history."""
        if not self._history:
            self.load_history()
        return self._history.copy()

    def get_statistics(self) -> dict:
        """Get extraction statistics from history."""
        if not self._history:
            self.load_history()

        if not self._history:
            return {
                "total_extractions": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
                "total_pages": 0,
                "total_variables": 0,
                "total_time_seconds": 0,
                "average_time_seconds": 0,
                "unique_projects": 0
            }

        successful = [r for r in self._history if r.success]
        failed = [r for r in self._history if not r.success]
        projects = set(r.project for r in self._history)

        total_time = sum(r.duration_seconds for r in self._history)

        return {
            "total_extractions": len(self._history),
            "successful_extractions": len(successful),
            "failed_extractions": len(failed),
            "total_pages": sum(r.pages_extracted for r in successful),
            "total_variables": sum(r.variables_found for r in successful),
            "total_time_seconds": total_time,
            "average_time_seconds": total_time / len(self._history) if self._history else 0,
            "unique_projects": len(projects)
        }
