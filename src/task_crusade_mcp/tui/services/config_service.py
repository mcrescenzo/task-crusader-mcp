"""TUI configuration service for persisting user preferences.

This module provides a service for loading and saving TUI preferences
such as status filter selections. Preferences are stored in a JSON file
within the ~/.crusader/ config directory.

Example usage:
    config_service = TUIConfigService()

    # Load saved filter preference
    filter_value = config_service.get_status_filter()  # Returns "all" if not set

    # Save filter preference
    config_service.set_status_filter("pending")
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Valid task status filter values
VALID_STATUS_FILTERS = {
    "all",
    "actionable",
    "pending",
    "in-progress",
    "done",
    "blocked",
    "cancelled",
}

# Default task status filter value
DEFAULT_STATUS_FILTER = "all"

# Valid campaign status filter values
VALID_CAMPAIGN_FILTERS = {"all", "planning", "active", "paused", "completed", "cancelled"}

# Default campaign status filter value
DEFAULT_CAMPAIGN_FILTER = "all"

# Config filename
TUI_PREFERENCES_FILENAME = "tui_preferences.json"


def get_config_directory() -> Path:
    """Get the config directory path.

    Returns path to ~/.crusader/, creating directory if needed.
    """
    config_dir = Path.home() / ".crusader"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


class TUIConfigService:
    """Service for managing TUI user preferences.

    This service handles loading and saving TUI preferences to a JSON file
    in the ~/.crusader/ config directory. It provides graceful error handling
    for missing files, corrupted JSON, and invalid values.

    Attributes:
        _config_path: Path to the preferences JSON file.
        _cache: In-memory cache of loaded preferences.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the config service.

        Args:
            config_path: Optional custom path for the config file.
                If None, uses the ~/.crusader/ config directory.
        """
        if config_path is not None:
            self._config_path = config_path
        else:
            config_dir = get_config_directory()
            self._config_path = config_dir / TUI_PREFERENCES_FILENAME
        self._cache: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        """Get the path to the config file."""
        return self._config_path

    def _load_preferences(self) -> dict[str, Any]:
        """Load preferences from the config file.

        Returns:
            Dictionary of preferences, or empty dict if file doesn't exist
            or is invalid.
        """
        if self._cache is not None:
            return self._cache

        try:
            if not self._config_path.exists():
                logger.debug("Config file does not exist: %s", self._config_path)
                self._cache = {}
                return self._cache

            with open(self._config_path, encoding="utf-8") as f:
                content = f.read()
                if not content.strip():
                    logger.debug("Config file is empty: %s", self._config_path)
                    self._cache = {}
                    return self._cache

                self._cache = json.loads(content)
                if not isinstance(self._cache, dict):
                    logger.warning(
                        "Config file contains non-dict value, resetting: %s",
                        self._config_path,
                    )
                    self._cache = {}
                return self._cache

        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse config file %s: %s. Using defaults.",
                self._config_path,
                e,
            )
            self._cache = {}
            return self._cache
        except OSError as e:
            logger.warning(
                "Failed to read config file %s: %s. Using defaults.",
                self._config_path,
                e,
            )
            self._cache = {}
            return self._cache

    def _save_preferences(self, preferences: dict[str, Any]) -> bool:
        """Save preferences to the config file.

        Args:
            preferences: Dictionary of preferences to save.

        Returns:
            True if save was successful, False otherwise.
        """
        try:
            # Ensure parent directory exists
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(preferences, f, indent=2)

            # Update cache
            self._cache = preferences
            logger.debug("Saved preferences to %s", self._config_path)
            return True

        except OSError as e:
            logger.warning(
                "Failed to save config file %s: %s",
                self._config_path,
                e,
            )
            return False

    def get_status_filter(self) -> str:
        """Get the saved status filter preference.

        Returns:
            The saved status filter value, or "all" if not set or invalid.
        """
        preferences = self._load_preferences()
        filter_value = preferences.get("status_filter", DEFAULT_STATUS_FILTER)

        # Validate the filter value
        if filter_value not in VALID_STATUS_FILTERS:
            logger.warning(
                "Invalid status filter value '%s', using default '%s'",
                filter_value,
                DEFAULT_STATUS_FILTER,
            )
            return DEFAULT_STATUS_FILTER

        return filter_value

    def set_status_filter(self, filter_value: str) -> bool:
        """Save the status filter preference.

        Args:
            filter_value: The status filter value to save.

        Returns:
            True if save was successful, False otherwise.
        """
        # Validate the filter value
        if filter_value not in VALID_STATUS_FILTERS:
            logger.warning(
                "Attempted to save invalid status filter value: %s",
                filter_value,
            )
            return False

        preferences = self._load_preferences()
        preferences["status_filter"] = filter_value
        return self._save_preferences(preferences)

    def get_campaign_filter(self) -> str:
        """Get the saved campaign status filter preference.

        Returns:
            The saved campaign filter value, or "all" if not set or invalid.
        """
        preferences = self._load_preferences()
        filter_value = preferences.get("campaign_filter", DEFAULT_CAMPAIGN_FILTER)

        # Validate the filter value
        if filter_value not in VALID_CAMPAIGN_FILTERS:
            logger.warning(
                "Invalid campaign filter value '%s', using default '%s'",
                filter_value,
                DEFAULT_CAMPAIGN_FILTER,
            )
            return DEFAULT_CAMPAIGN_FILTER

        return filter_value

    def set_campaign_filter(self, filter_value: str) -> bool:
        """Save the campaign status filter preference.

        Args:
            filter_value: The campaign filter value to save.

        Returns:
            True if save was successful, False otherwise.
        """
        # Validate the filter value
        if filter_value not in VALID_CAMPAIGN_FILTERS:
            logger.warning(
                "Attempted to save invalid campaign filter value: %s",
                filter_value,
            )
            return False

        preferences = self._load_preferences()
        preferences["campaign_filter"] = filter_value
        return self._save_preferences(preferences)

    def clear_cache(self) -> None:
        """Clear the in-memory cache, forcing a reload on next access."""
        self._cache = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a generic preference value.

        Args:
            key: The preference key to retrieve.
            default: Default value if key not found.

        Returns:
            The preference value, or default if not found.
        """
        preferences = self._load_preferences()
        return preferences.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Set a generic preference value.

        Args:
            key: The preference key to set.
            value: The value to save.

        Returns:
            True if save was successful, False otherwise.
        """
        preferences = self._load_preferences()
        preferences[key] = value
        return self._save_preferences(preferences)
