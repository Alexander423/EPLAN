"""
Configuration management with encrypted credential storage.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ..utils.logging import get_logger


@dataclass
class AppConfig:
    """Application configuration data class."""
    email: str = ""
    password_encrypted: str = ""
    project: str = ""
    headless: bool = True
    export_excel: bool = True
    export_csv: bool = False


class ConfigManager:
    """
    Manages application configuration with encrypted credential storage.

    Uses Fernet symmetric encryption for password storage.
    """

    CONFIG_FILE: str = "eplan_config.json"
    KEY_FILE: str = "fernet.key"

    def __init__(self) -> None:
        """Initialize the configuration manager."""
        self._logger = get_logger()
        self._fernet: Optional[Fernet] = None
        self._config = AppConfig()
        self._setup_encryption()

    def _setup_encryption(self) -> None:
        """Set up Fernet encryption key."""
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
            self._logger.error(f"Failed to set up encryption: {e}")
            raise

    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a password.

        Args:
            password: Plain text password

        Returns:
            Base64-encoded encrypted password
        """
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")

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
        if not self._fernet:
            raise RuntimeError("Encryption not initialized")

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
                export_csv=data.get("export_csv", False)
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
                "export_csv": config.export_csv
            }

            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            self._config = config
            self._logger.info("Configuration saved successfully")
            return True

        except IOError as e:
            self._logger.error(f"Failed to save configuration: {e}")
            return False
