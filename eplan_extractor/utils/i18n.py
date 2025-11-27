"""
Internationalization (i18n) module for multi-language support.
"""

from typing import Dict, Optional

# Translations dictionary
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # ==========================================================================
    # English (default)
    # ==========================================================================
    "en": {
        # Window titles
        "app_title": "EPLAN eVIEW Extractor",
        "settings_title": "Settings",
        "update_available_title": "Update Available",
        "history_title": "Extraction History",
        "statistics_title": "Statistics",

        # Header
        "eplan": "EPLAN",
        "eview_extractor": " eVIEW Extractor",

        # Credentials card
        "microsoft_credentials": "Microsoft Credentials",
        "email_address": "Email Address",
        "password": "Password",
        "project_number": "Project Number",
        "email_placeholder": "your.email@company.com",
        "password_placeholder": "Enter your password",
        "project_placeholder": "e.g., PROJECT-001",
        "email_tooltip": "Enter your Microsoft account email",
        "password_tooltip": "Enter your Microsoft account password (shown as dots for security)",
        "project_tooltip": "Enter the EPLAN project number to extract",
        "recent_projects": "Recent Projects",
        "no_recent_projects": "No recent projects",

        # Options card
        "options": "Options",
        "export_format": "Export Format",
        "excel_xlsx": "Excel (.xlsx)",
        "csv_file": "CSV (.csv)",
        "json_file": "JSON (.json)",
        "behavior": "Behavior",
        "run_in_background": "Run in Background",
        "save_credentials": "Save Credentials",
        "export_tooltip_excel": "Export results to Excel format",
        "export_tooltip_csv": "Export results to CSV format",
        "export_tooltip_json": "Export results to JSON format",
        "headless_tooltip": "Run browser in headless mode (no visible window)",
        "save_creds_tooltip": "Remember your login credentials (encrypted)",
        "output_directory": "Output Directory",
        "browse": "Browse...",
        "default_directory": "Default (current directory)",

        # Progress card
        "extraction_progress": "Extraction Progress",
        "step_login": "Login",
        "step_open_project": "Open Project",
        "step_extract": "Extract Data",
        "step_export": "Export",

        # Action buttons
        "start_extraction": "Start Extraction",
        "stop": "Stop",
        "start_tooltip": "Start the extraction process",
        "stop_tooltip": "Stop the running extraction",

        # Log panel
        "log": "Log",
        "clear_log": "Clear",
        "export_log": "Export Log",
        "filter_all": "All",
        "filter_info": "Info",
        "filter_warning": "Warning",
        "filter_error": "Error",

        # Status messages
        "status_ready": "Ready",
        "status_starting": "Starting extraction...",
        "status_logging_in": "Logging in...",
        "status_opening_project": "Opening project...",
        "status_extracting": "Extracting variables...",
        "status_exporting": "Exporting data...",
        "status_completed": "Extraction completed!",
        "status_stopped": "Extraction stopped",
        "status_error": "Error",

        # Settings dialog
        "appearance": "Appearance",
        "dark_mode": "Dark Mode",
        "light_mode": "Light Mode",
        "theme_restart_note": "(Requires restart for full effect)",
        "language": "Language",
        "english": "English",
        "german": "Deutsch",

        "cache_management": "Cache Management",
        "cache_description": "Cached data speeds up re-extraction of the same pages.",
        "clear_cache": "Clear Cache",
        "cache_cleared": "Cache Cleared",
        "cache_cleared_msg": "Successfully cleared {count} cache entries.",

        "security": "Security",
        "security_description": "Your password is stored encrypted using Fernet encryption.",
        "clear_credentials": "Clear Saved Credentials",
        "credentials_cleared": "Credentials Cleared",
        "credentials_cleared_msg": "Saved credentials have been removed.",

        "updates": "Updates",
        "current_version": "Current version: v{version}",
        "check_for_updates": "Check for Updates",
        "checking_updates": "Checking for updates...",
        "up_to_date": "You're running the latest version!",
        "update_available": "Update available: v{version}",
        "update_check_failed": "Error checking for updates",
        "check_on_startup": "Check for updates on startup",

        "notifications": "Notifications",
        "show_notifications": "Show desktop notifications",
        "minimize_to_tray": "Minimize to system tray",

        "network": "Network",
        "proxy_settings": "Proxy Settings",
        "enable_proxy": "Enable proxy",
        "proxy_host": "Host",
        "proxy_port": "Port",
        "proxy_username": "Username (optional)",
        "proxy_password": "Password (optional)",

        "about": "About",
        "about_description": "Extracts PLC variables from EPLAN eVIEW diagrams.",
        "copyright": "EPLAN Extractor Team",

        "close": "Close",
        "save": "Save",
        "cancel": "Cancel",
        "ok": "OK",

        # Update dialog
        "update_available_header": "Update Available!",
        "new_version": "New version: v{version}",
        "download_size": "Download size: {size}",
        "release_notes": "Release Notes:",
        "no_release_notes": "No release notes available.",
        "download_update": "Download Update",
        "view_on_github": "View on GitHub",
        "later": "Later",
        "downloading_update": "Downloading update...",
        "download_complete": "Download Complete",
        "download_complete_msg": "Update v{version} downloaded successfully!\n\nFile: {file}\n\nWould you like to open the installer now?\n(The application will close)",
        "download_failed": "Download Failed",
        "manual_install_required": "Manual Installation Required",
        "manual_install_msg": "Please manually run the installer:\n\n{file}",

        # History dialog
        "extraction_history": "Extraction History",
        "no_history": "No extraction history yet.",
        "clear_history": "Clear History",
        "history_cleared": "History Cleared",
        "history_cleared_msg": "Successfully cleared {count} history entries.",
        "project_col": "Project",
        "date_col": "Date",
        "duration_col": "Duration",
        "pages_col": "Pages",
        "variables_col": "Variables",
        "status_col": "Status",
        "success": "Success",
        "failed": "Failed",

        # Statistics
        "statistics": "Statistics",
        "total_extractions": "Total Extractions",
        "successful_extractions": "Successful",
        "failed_extractions": "Failed",
        "total_pages": "Total Pages",
        "total_variables": "Total Variables",
        "total_time": "Total Time",
        "average_time": "Average Time",
        "unique_projects": "Unique Projects",

        # Validation
        "validation_email_required": "Please enter your email address",
        "validation_email_invalid": "Please enter a valid email address",
        "validation_password_required": "Please enter your password",
        "validation_project_required": "Please enter a project number",

        # Keyboard shortcuts
        "keyboard_shortcuts": "Keyboard Shortcuts",
        "shortcut_start": "Start extraction",
        "shortcut_stop": "Stop extraction",
        "shortcut_settings": "Open settings",
        "shortcut_quit": "Quit application",
    },

    # ==========================================================================
    # German
    # ==========================================================================
    "de": {
        # Window titles
        "app_title": "EPLAN eVIEW Extraktor",
        "settings_title": "Einstellungen",
        "update_available_title": "Update verfügbar",
        "history_title": "Extraktionsverlauf",
        "statistics_title": "Statistiken",

        # Header
        "eplan": "EPLAN",
        "eview_extractor": " eVIEW Extraktor",

        # Credentials card
        "microsoft_credentials": "Microsoft Anmeldedaten",
        "email_address": "E-Mail-Adresse",
        "password": "Passwort",
        "project_number": "Projektnummer",
        "email_placeholder": "ihre.email@firma.com",
        "password_placeholder": "Passwort eingeben",
        "project_placeholder": "z.B. PROJEKT-001",
        "email_tooltip": "Microsoft-Konto E-Mail eingeben",
        "password_tooltip": "Microsoft-Konto Passwort eingeben (aus Sicherheitsgründen als Punkte dargestellt)",
        "project_tooltip": "EPLAN Projektnummer für Extraktion eingeben",
        "recent_projects": "Letzte Projekte",
        "no_recent_projects": "Keine letzten Projekte",

        # Options card
        "options": "Optionen",
        "export_format": "Exportformat",
        "excel_xlsx": "Excel (.xlsx)",
        "csv_file": "CSV (.csv)",
        "json_file": "JSON (.json)",
        "behavior": "Verhalten",
        "run_in_background": "Im Hintergrund ausführen",
        "save_credentials": "Anmeldedaten speichern",
        "export_tooltip_excel": "Ergebnisse als Excel exportieren",
        "export_tooltip_csv": "Ergebnisse als CSV exportieren",
        "export_tooltip_json": "Ergebnisse als JSON exportieren",
        "headless_tooltip": "Browser im Hintergrundmodus ausführen (kein sichtbares Fenster)",
        "save_creds_tooltip": "Anmeldedaten merken (verschlüsselt)",
        "output_directory": "Ausgabeverzeichnis",
        "browse": "Durchsuchen...",
        "default_directory": "Standard (aktuelles Verzeichnis)",

        # Progress card
        "extraction_progress": "Extraktionsfortschritt",
        "step_login": "Anmeldung",
        "step_open_project": "Projekt öffnen",
        "step_extract": "Daten extrahieren",
        "step_export": "Exportieren",

        # Action buttons
        "start_extraction": "Extraktion starten",
        "stop": "Stopp",
        "start_tooltip": "Extraktionsprozess starten",
        "stop_tooltip": "Laufende Extraktion stoppen",

        # Log panel
        "log": "Protokoll",
        "clear_log": "Löschen",
        "export_log": "Log exportieren",
        "filter_all": "Alle",
        "filter_info": "Info",
        "filter_warning": "Warnung",
        "filter_error": "Fehler",

        # Status messages
        "status_ready": "Bereit",
        "status_starting": "Extraktion wird gestartet...",
        "status_logging_in": "Anmeldung läuft...",
        "status_opening_project": "Projekt wird geöffnet...",
        "status_extracting": "Variablen werden extrahiert...",
        "status_exporting": "Daten werden exportiert...",
        "status_completed": "Extraktion abgeschlossen!",
        "status_stopped": "Extraktion gestoppt",
        "status_error": "Fehler",

        # Settings dialog
        "appearance": "Erscheinungsbild",
        "dark_mode": "Dunkelmodus",
        "light_mode": "Hellmodus",
        "theme_restart_note": "(Neustart für volle Wirkung erforderlich)",
        "language": "Sprache",
        "english": "English",
        "german": "Deutsch",

        "cache_management": "Cache-Verwaltung",
        "cache_description": "Gecachte Daten beschleunigen die erneute Extraktion derselben Seiten.",
        "clear_cache": "Cache leeren",
        "cache_cleared": "Cache geleert",
        "cache_cleared_msg": "{count} Cache-Einträge erfolgreich gelöscht.",

        "security": "Sicherheit",
        "security_description": "Ihr Passwort wird mit Fernet-Verschlüsselung gespeichert.",
        "clear_credentials": "Gespeicherte Anmeldedaten löschen",
        "credentials_cleared": "Anmeldedaten gelöscht",
        "credentials_cleared_msg": "Gespeicherte Anmeldedaten wurden entfernt.",

        "updates": "Updates",
        "current_version": "Aktuelle Version: v{version}",
        "check_for_updates": "Nach Updates suchen",
        "checking_updates": "Suche nach Updates...",
        "up_to_date": "Sie verwenden die neueste Version!",
        "update_available": "Update verfügbar: v{version}",
        "update_check_failed": "Fehler bei der Update-Prüfung",
        "check_on_startup": "Beim Start nach Updates suchen",

        "notifications": "Benachrichtigungen",
        "show_notifications": "Desktop-Benachrichtigungen anzeigen",
        "minimize_to_tray": "In Systemablage minimieren",

        "network": "Netzwerk",
        "proxy_settings": "Proxy-Einstellungen",
        "enable_proxy": "Proxy aktivieren",
        "proxy_host": "Host",
        "proxy_port": "Port",
        "proxy_username": "Benutzername (optional)",
        "proxy_password": "Passwort (optional)",

        "about": "Über",
        "about_description": "Extrahiert SPS-Variablen aus EPLAN eVIEW Schaltplänen.",
        "copyright": "EPLAN Extraktor Team",

        "close": "Schließen",
        "save": "Speichern",
        "cancel": "Abbrechen",
        "ok": "OK",

        # Update dialog
        "update_available_header": "Update verfügbar!",
        "new_version": "Neue Version: v{version}",
        "download_size": "Downloadgröße: {size}",
        "release_notes": "Versionshinweise:",
        "no_release_notes": "Keine Versionshinweise verfügbar.",
        "download_update": "Update herunterladen",
        "view_on_github": "Auf GitHub ansehen",
        "later": "Später",
        "downloading_update": "Update wird heruntergeladen...",
        "download_complete": "Download abgeschlossen",
        "download_complete_msg": "Update v{version} erfolgreich heruntergeladen!\n\nDatei: {file}\n\nMöchten Sie das Installationsprogramm jetzt öffnen?\n(Die Anwendung wird geschlossen)",
        "download_failed": "Download fehlgeschlagen",
        "manual_install_required": "Manuelle Installation erforderlich",
        "manual_install_msg": "Bitte führen Sie das Installationsprogramm manuell aus:\n\n{file}",

        # History dialog
        "extraction_history": "Extraktionsverlauf",
        "no_history": "Noch kein Extraktionsverlauf.",
        "clear_history": "Verlauf löschen",
        "history_cleared": "Verlauf gelöscht",
        "history_cleared_msg": "{count} Verlaufseinträge erfolgreich gelöscht.",
        "project_col": "Projekt",
        "date_col": "Datum",
        "duration_col": "Dauer",
        "pages_col": "Seiten",
        "variables_col": "Variablen",
        "status_col": "Status",
        "success": "Erfolg",
        "failed": "Fehlgeschlagen",

        # Statistics
        "statistics": "Statistiken",
        "total_extractions": "Gesamtextraktionen",
        "successful_extractions": "Erfolgreich",
        "failed_extractions": "Fehlgeschlagen",
        "total_pages": "Gesamtseiten",
        "total_variables": "Gesamtvariablen",
        "total_time": "Gesamtzeit",
        "average_time": "Durchschnittszeit",
        "unique_projects": "Eindeutige Projekte",

        # Validation
        "validation_email_required": "Bitte geben Sie Ihre E-Mail-Adresse ein",
        "validation_email_invalid": "Bitte geben Sie eine gültige E-Mail-Adresse ein",
        "validation_password_required": "Bitte geben Sie Ihr Passwort ein",
        "validation_project_required": "Bitte geben Sie eine Projektnummer ein",

        # Keyboard shortcuts
        "keyboard_shortcuts": "Tastaturkürzel",
        "shortcut_start": "Extraktion starten",
        "shortcut_stop": "Extraktion stoppen",
        "shortcut_settings": "Einstellungen öffnen",
        "shortcut_quit": "Anwendung beenden",
    }
}


class I18n:
    """Internationalization manager."""

    _current_language: str = "en"
    _observers: list = []

    @classmethod
    def set_language(cls, language: str) -> None:
        """Set the current language."""
        if language in TRANSLATIONS:
            cls._current_language = language
            cls._notify_observers()

    @classmethod
    def get_language(cls) -> str:
        """Get the current language code."""
        return cls._current_language

    @classmethod
    def get(cls, key: str, **kwargs) -> str:
        """
        Get a translated string.

        Args:
            key: The translation key
            **kwargs: Format arguments

        Returns:
            The translated string, or the key if not found
        """
        translations = TRANSLATIONS.get(cls._current_language, TRANSLATIONS["en"])
        text = translations.get(key, TRANSLATIONS["en"].get(key, key))

        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError:
                return text

        return text

    @classmethod
    def add_observer(cls, callback) -> None:
        """Add an observer for language changes."""
        if callback not in cls._observers:
            cls._observers.append(callback)

    @classmethod
    def remove_observer(cls, callback) -> None:
        """Remove an observer."""
        if callback in cls._observers:
            cls._observers.remove(callback)

    @classmethod
    def _notify_observers(cls) -> None:
        """Notify all observers of language change."""
        for callback in cls._observers:
            try:
                callback()
            except Exception:
                pass

    @classmethod
    def get_available_languages(cls) -> Dict[str, str]:
        """Get available languages with their display names."""
        return {
            "en": "English",
            "de": "Deutsch"
        }


# Convenience function
def t(key: str, **kwargs) -> str:
    """Shorthand for I18n.get()."""
    return I18n.get(key, **kwargs)
