"""
Tests for the ConfigManager class.
"""

import unittest
from pathlib import Path

from eplan_extractor.core.config import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Tests for the ConfigManager class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Backup existing files
        self.config_backup = None
        self.key_backup = None

        if Path(ConfigManager.CONFIG_FILE).exists():
            self.config_backup = Path(ConfigManager.CONFIG_FILE).read_text()
        if Path(ConfigManager.KEY_FILE).exists():
            self.key_backup = Path(ConfigManager.KEY_FILE).read_bytes()

    def tearDown(self) -> None:
        """Restore backed up files."""
        if self.config_backup:
            Path(ConfigManager.CONFIG_FILE).write_text(self.config_backup)
        if self.key_backup:
            Path(ConfigManager.KEY_FILE).write_bytes(self.key_backup)

    def test_encrypt_decrypt_password(self) -> None:
        """Test password encryption and decryption."""
        manager = ConfigManager()
        password = "TestPassword123!"

        encrypted = manager.encrypt_password(password)
        self.assertNotEqual(encrypted, password)

        decrypted = manager.decrypt_password(encrypted)
        self.assertEqual(decrypted, password)


if __name__ == "__main__":
    unittest.main()
