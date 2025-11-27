"""
Thread-safe file logging system with rotation support.
"""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from ..constants import DEBUG, LOG_BACKUP_COUNT, LOG_FILE, LOG_MAX_SIZE, VERSION


class LogLevel:
    """Log level constants."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class FileLogger:
    """
    Thread-safe file logger with rotation support.

    Logs messages to both file and optionally to a callback function.
    """

    _instance: Optional[FileLogger] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> FileLogger:
        """Singleton pattern for logger instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize the file logger."""
        if self._initialized:
            return

        self._initialized = True
        self._log_file = Path(LOG_FILE)
        self._callbacks: List[Callable[[str, str], None]] = []
        self._file_lock = threading.Lock()

        # Rotate log if too large
        self._rotate_if_needed()

        # Write startup marker
        self._write_to_file(f"\n{'='*60}\n")
        self._write_to_file(f"EPLAN Extractor v{VERSION} - Session Started\n")
        self._write_to_file(f"Timestamp: {datetime.now().isoformat()}\n")
        self._write_to_file(f"{'='*60}\n\n")

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds maximum size."""
        if not self._log_file.exists():
            return

        if self._log_file.stat().st_size > LOG_MAX_SIZE:
            # Rotate existing backups
            for i in range(LOG_BACKUP_COUNT - 1, 0, -1):
                old_backup = self._log_file.with_suffix(f".log.{i}")
                new_backup = self._log_file.with_suffix(f".log.{i + 1}")
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)

            # Move current log to first backup
            backup_path = self._log_file.with_suffix(".log.1")
            if backup_path.exists():
                backup_path.unlink()
            self._log_file.rename(backup_path)

    def _write_to_file(self, message: str) -> None:
        """Write a message to the log file (thread-safe)."""
        with self._file_lock:
            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(message)
            except IOError as e:
                print(f"Failed to write to log file: {e}")

    def add_callback(self, callback: Callable[[str, str], None]) -> None:
        """Add a callback function to receive log messages."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[str, str], None]) -> None:
        """Remove a callback function."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def log(self, message: str, level: str = LogLevel.INFO) -> None:
        """
        Log a message with timestamp and level.

        Args:
            message: The message to log
            level: Log level (DEBUG, INFO, WARNING, ERROR, SUCCESS)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"

        # Write to file
        self._write_to_file(formatted + "\n")

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(message, level)
            except Exception:
                pass  # Don't let callback errors break logging

    def debug(self, message: str) -> None:
        """Log a debug message."""
        if DEBUG:
            self.log(message, LogLevel.DEBUG)

    def info(self, message: str) -> None:
        """Log an info message."""
        self.log(message, LogLevel.INFO)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.log(message, LogLevel.WARNING)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.log(message, LogLevel.ERROR)

    def success(self, message: str) -> None:
        """Log a success message."""
        self.log(message, LogLevel.SUCCESS)


def get_logger() -> FileLogger:
    """Get the singleton logger instance."""
    return FileLogger()
