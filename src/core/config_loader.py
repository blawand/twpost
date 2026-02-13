import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self):
        """
        Initializes the ConfigLoader with empty defaults as legacy JSON files are removed.
        """
        self.settings: Dict[str, Any] = {}

    def get_settings(self) -> Dict[str, Any]:
        """Returns all loaded settings."""
        return self.settings

    def get_setting(self, path_str: str, default: Any = None) -> Any:
        """
        Retrieves a setting value using a dot-separated path.

        Args:
            path_str (str): Dot-separated path to the setting (e.g., "logging.level").
            default (Any, optional): Default value if the setting is not found. Defaults to None.

        Returns:
            Any: The setting value or the default.
        """
        keys = path_str.split('.')
        current_level = self.settings
        try:
            for key in keys:
                if isinstance(current_level, dict):
                    current_level = current_level[key]
                else: # Path leads to a non-dict item before all keys are consumed
                    logger.warning(f"Invalid path '{path_str}' at key '{key}'. Expected a dictionary, found {type(current_level)}.")
                    return default
            return current_level
        except KeyError:
            logger.debug(f"Setting '{path_str}' not found. Returning default: {default}")
            return default
        except Exception as e:
            logger.warning(f"Error accessing setting '{path_str}': {e}. Returning default: {default}")
            return default

    def get_logging_setting(self, setting_name: str, default: Any = None) -> Any:
        """Retrieves a specific setting from the 'logging' block."""
        return self.get_setting(f'logging.{setting_name}', default)
