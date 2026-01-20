import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Union, Optional

# Define project root relative to this file's location (src/core/config_loader.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / 'config'

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self):
        """
        Initializes the ConfigLoader with empty defaults as legacy JSON files are removed.
        """
        self.settings: Dict[str, Any] = {}
        self.accounts: List[Dict[str, Any]] = []

    def _load_json(self, file_path: Path, default_value: Union[Dict, List]) -> Any:
        """
        Legacy JSON loader - kept for potential future use or subclassing, 
        but no longer used for core settings/accounts.
        """
        if not file_path.exists():
            return default_value
            
        try:
            with file_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Could not load JSON from {file_path}: {e}")
            return default_value

    def get_settings(self) -> Dict[str, Any]:
        """Returns all loaded settings."""
        return self.settings

    def get_accounts_config(self) -> List[Dict[str, Any]]:
        """Returns all loaded account configurations."""
        return self.accounts

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

    def get_api_key(self, service_name: str) -> Optional[str]:
        """Retrieves an API key for a specific service."""
        return self.get_setting(f'api_keys.{service_name}')

    def get_twitter_automation_setting(self, setting_name: str, default: Any = None) -> Any:
        """Retrieves a specific setting from the 'twitter_automation' block."""
        return self.get_setting(f'twitter_automation.{setting_name}', default)

    def get_logging_setting(self, setting_name: str, default: Any = None) -> Any:
        """Retrieves a specific setting from the 'logging' block."""
        return self.get_setting(f'logging.{setting_name}', default)

# Example usage (optional, for testing)
# Example usage (optional, for testing)
if __name__ == '__main__':
    # Basic logging setup for testing ConfigLoader directly
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    loader = ConfigLoader()
    
    logger.info(f"All Settings (should be empty): {loader.get_settings()}")
    logger.info(f"All Accounts (should be empty): {loader.get_accounts_config()}")
    
    logger.info(f"OpenAI API Key (should be None): {loader.get_api_key('openai_api_key')}")
    
    logger.info("--- Testing generic get_setting with defaults ---")
    logger.info(f"Logging Level (default): {loader.get_setting('logging.level', 'INFO')}")
    logger.info(f"Non-existent deep path (default): {loader.get_setting('a.b.c.d', 'default_value')}")
