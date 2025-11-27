"""
Core modules for EPLAN eVIEW Extractor.

Note: Imports are done lazily to avoid issues with missing dependencies.
Import directly from submodules:
    from eplan_extractor.core.cache import CacheManager
    from eplan_extractor.core.config import AppConfig, ConfigManager
    from eplan_extractor.core.extractor import SeleniumEPlanExtractor
    from eplan_extractor.core.updater import UpdateChecker, UpdateDownloader, ReleaseInfo
"""

__all__ = [
    "CacheManager",
    "AppConfig",
    "ConfigManager",
    "SeleniumEPlanExtractor",
    "UpdateChecker",
    "UpdateDownloader",
    "ReleaseInfo",
]
