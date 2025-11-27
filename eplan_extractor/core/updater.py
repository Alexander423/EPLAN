"""
Auto-update module for checking and downloading updates from GitHub releases.
"""

import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
from pathlib import Path

from ..constants import VERSION


@dataclass
class ReleaseInfo:
    """Information about a GitHub release."""
    version: str
    tag_name: str
    name: str
    body: str  # Release notes
    published_at: str
    html_url: str
    download_url: Optional[str] = None
    download_size: int = 0


class UpdateChecker:
    """Check for updates from GitHub releases."""

    # Default GitHub repository (can be configured)
    DEFAULT_OWNER = "Alexander423"
    DEFAULT_REPO = "EPLAN"

    def __init__(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        current_version: Optional[str] = None
    ) -> None:
        """
        Initialize the update checker.

        Args:
            owner: GitHub repository owner
            repo: GitHub repository name
            current_version: Current application version (defaults to VERSION constant)
        """
        self.owner = owner or self.DEFAULT_OWNER
        self.repo = repo or self.DEFAULT_REPO
        self.current_version = current_version or VERSION
        self._api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/releases/latest"

    def _parse_version(self, version_str: str) -> Tuple[int, ...]:
        """
        Parse version string into comparable tuple.

        Args:
            version_str: Version string like "1.0.0" or "v1.0.0"

        Returns:
            Tuple of version numbers (e.g., (1, 0, 0))
        """
        # Remove 'v' prefix if present
        version_str = version_str.lstrip('vV')

        # Handle versions with suffixes like "1.0.0-beta"
        version_str = version_str.split('-')[0]

        try:
            parts = version_str.split('.')
            return tuple(int(p) for p in parts)
        except ValueError:
            return (0, 0, 0)

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Args:
            v1: First version string
            v2: Second version string

        Returns:
            -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
        """
        parsed_v1 = self._parse_version(v1)
        parsed_v2 = self._parse_version(v2)

        if parsed_v1 < parsed_v2:
            return -1
        elif parsed_v1 > parsed_v2:
            return 1
        return 0

    def _find_asset_url(self, assets: list) -> Tuple[Optional[str], int]:
        """
        Find the appropriate download URL from release assets.

        Args:
            assets: List of release assets from GitHub API

        Returns:
            Tuple of (download_url, file_size) or (None, 0) if not found
        """
        system = platform.system().lower()

        # Priority order for asset names
        priority_patterns = []

        if system == "windows":
            priority_patterns = [".exe", ".msi", "-windows", "-win64", "-win"]
        elif system == "darwin":
            priority_patterns = [".dmg", "-macos", "-mac", "-darwin"]
        else:  # Linux
            priority_patterns = [".AppImage", ".deb", "-linux", ".tar.gz"]

        # Also look for generic Python package
        priority_patterns.extend([".whl", ".tar.gz", ".zip"])

        for pattern in priority_patterns:
            for asset in assets:
                name = asset.get("name", "").lower()
                if pattern.lower() in name:
                    return (
                        asset.get("browser_download_url"),
                        asset.get("size", 0)
                    )

        # If no specific asset found, return the first one (if any)
        if assets:
            return (
                assets[0].get("browser_download_url"),
                assets[0].get("size", 0)
            )

        return None, 0

    def check_for_updates(self) -> Optional[ReleaseInfo]:
        """
        Check GitHub for newer releases.

        Returns:
            ReleaseInfo if update available, None otherwise

        Raises:
            urllib.error.URLError: If network request fails
            json.JSONDecodeError: If response is invalid JSON
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"EPLAN-Extractor/{self.current_version}"
        }

        request = urllib.request.Request(self._api_url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # No releases found
                return None
            raise

        tag_name = data.get("tag_name", "")
        latest_version = tag_name.lstrip('vV')

        # Compare versions
        if self._compare_versions(self.current_version, latest_version) >= 0:
            # Current version is up to date or newer
            return None

        # Find download URL
        assets = data.get("assets", [])
        download_url, download_size = self._find_asset_url(assets)

        return ReleaseInfo(
            version=latest_version,
            tag_name=tag_name,
            name=data.get("name", f"Release {tag_name}"),
            body=data.get("body", ""),
            published_at=data.get("published_at", ""),
            html_url=data.get("html_url", ""),
            download_url=download_url,
            download_size=download_size
        )

    def check_for_updates_async(
        self,
        callback: Callable[[Optional[ReleaseInfo], Optional[Exception]], None]
    ) -> threading.Thread:
        """
        Check for updates asynchronously.

        Args:
            callback: Function called with (release_info, error) when complete

        Returns:
            The thread running the check
        """
        def _check():
            try:
                result = self.check_for_updates()
                callback(result, None)
            except Exception as e:
                callback(None, e)

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()
        return thread


class UpdateDownloader:
    """Download and install updates."""

    def __init__(self, release_info: ReleaseInfo) -> None:
        """
        Initialize the downloader.

        Args:
            release_info: Information about the release to download
        """
        self.release_info = release_info
        self._progress_callback: Optional[Callable[[int, int], None]] = None
        self._cancelled = False

    def set_progress_callback(
        self,
        callback: Callable[[int, int], None]
    ) -> None:
        """
        Set callback for download progress updates.

        Args:
            callback: Function called with (bytes_downloaded, total_bytes)
        """
        self._progress_callback = callback

    def cancel(self) -> None:
        """Cancel the download."""
        self._cancelled = True

    def download(self, destination: Optional[Path] = None) -> Path:
        """
        Download the release.

        Args:
            destination: Where to save the file. If None, uses temp directory.

        Returns:
            Path to downloaded file

        Raises:
            ValueError: If no download URL available
            urllib.error.URLError: If download fails
        """
        if not self.release_info.download_url:
            raise ValueError("No download URL available for this release")

        self._cancelled = False

        # Determine filename from URL
        url_path = self.release_info.download_url.split('/')[-1]

        if destination is None:
            destination = Path(tempfile.gettempdir()) / url_path

        headers = {
            "User-Agent": f"EPLAN-Extractor/{VERSION}"
        }

        request = urllib.request.Request(
            self.release_info.download_url,
            headers=headers
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192

            with open(destination, 'wb') as f:
                while True:
                    if self._cancelled:
                        f.close()
                        destination.unlink(missing_ok=True)
                        raise InterruptedError("Download cancelled")

                    chunk = response.read(chunk_size)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    if self._progress_callback:
                        self._progress_callback(downloaded, total_size)

        return destination

    def download_async(
        self,
        callback: Callable[[Optional[Path], Optional[Exception]], None],
        destination: Optional[Path] = None
    ) -> threading.Thread:
        """
        Download asynchronously.

        Args:
            callback: Function called with (file_path, error) when complete
            destination: Where to save the file

        Returns:
            The thread running the download
        """
        def _download():
            try:
                path = self.download(destination)
                callback(path, None)
            except Exception as e:
                callback(None, e)

        thread = threading.Thread(target=_download, daemon=True)
        thread.start()
        return thread

    @staticmethod
    def open_release_page(url: str) -> bool:
        """
        Open the release page in the default browser.

        Args:
            url: URL to open

        Returns:
            True if successful, False otherwise
        """
        import webbrowser
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False

    @staticmethod
    def install_update(file_path: Path) -> bool:
        """
        Attempt to install the downloaded update.

        Args:
            file_path: Path to the downloaded update file

        Returns:
            True if installation started, False otherwise
        """
        system = platform.system().lower()

        try:
            if system == "windows":
                if file_path.suffix.lower() in ('.exe', '.msi'):
                    os.startfile(str(file_path))
                    return True
            elif system == "darwin":
                if file_path.suffix.lower() == '.dmg':
                    subprocess.Popen(['open', str(file_path)])
                    return True
            else:  # Linux
                if file_path.suffix.lower() == '.appimage':
                    file_path.chmod(0o755)
                    subprocess.Popen([str(file_path)])
                    return True
                elif file_path.suffix.lower() == '.deb':
                    subprocess.Popen(['xdg-open', str(file_path)])
                    return True

            # For other file types, try to open with default handler
            if system == "windows":
                os.startfile(str(file_path))
            elif system == "darwin":
                subprocess.Popen(['open', str(file_path)])
            else:
                subprocess.Popen(['xdg-open', str(file_path)])
            return True

        except Exception:
            return False


def format_size(size_bytes: int) -> str:
    """
    Format byte size to human readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string like "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
