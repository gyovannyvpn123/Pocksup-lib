"""
Configuration module for pocksup library.
"""

import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration handler for the pocksup library.
    Manages library settings and user credentials.
    """
    
    DEFAULT_CONFIG = {
        "log_level": "INFO",
        "auto_reconnect": True,
        "reconnect_delay": 5,  # seconds
        "max_retries": 5,
        "media_path": "./media",
        "credentials_path": "./credentials.json",
        "user_agent": "Pocksup/0.1.0",
        "enable_encryption": True,
        "enable_compression": True,
        "heartbeat_interval": 60,  # seconds
        "request_timeout": 15,  # seconds
        "debug_protocol": False,
        "debug_http": False
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration.
        
        Args:
            config_path: Path to the configuration file. If None, uses default config.
        """
        self.config = self.DEFAULT_CONFIG.copy()
        self.config_path = config_path
        
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)
        
        # Setup logging based on config
        self._setup_logging()
        
    def _load_config(self, config_path: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file.
        """
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                self.config.update(user_config)
            logger.debug(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {str(e)}")
    
    def _setup_logging(self) -> None:
        """Configure logging based on settings."""
        log_level = getattr(logging, self.config.get("log_level", "INFO"))
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set more verbose logging for debug components if enabled
        if self.config.get("debug_protocol", False):
            logging.getLogger("pocksup.protocol").setLevel(logging.DEBUG)
            
        if self.config.get("debug_http", False):
            logging.getLogger("pocksup.connection").setLevel(logging.DEBUG)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: The configuration key.
            default: Default value if key is not found.
            
        Returns:
            The configuration value or default.
        """
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: The configuration key.
            value: The value to set.
        """
        self.config[key] = value
        
        # Reload logging if log level changes
        if key == "log_level":
            self._setup_logging()
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save the current configuration to a file.
        
        Args:
            path: Path to save the configuration file. If None, uses config_path.
        """
        save_path = path or self.config_path
        
        if not save_path:
            logger.warning("No path specified for saving configuration")
            return
            
        try:
            # Ensure directory exists
            Path(os.path.dirname(save_path)).mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            logger.debug(f"Saved configuration to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {save_path}: {str(e)}")
    
    def load_credentials(self) -> Dict[str, str]:
        """
        Load user credentials from the credentials file.
        
        Returns:
            Dict containing the user credentials.
        """
        credentials_path = self.get("credentials_path")
        credentials = {}
        
        if credentials_path and os.path.exists(credentials_path):
            try:
                with open(credentials_path, 'r') as f:
                    credentials = json.load(f)
                logger.debug(f"Loaded credentials from {credentials_path}")
            except Exception as e:
                logger.warning(f"Failed to load credentials: {str(e)}")
        
        return credentials
    
    def save_credentials(self, credentials: Dict[str, str]) -> None:
        """
        Save user credentials to the credentials file.
        
        Args:
            credentials: Dict containing the user credentials.
        """
        credentials_path = self.get("credentials_path")
        
        if not credentials_path:
            logger.warning("No path specified for saving credentials")
            return
            
        try:
            # Ensure directory exists
            Path(os.path.dirname(credentials_path)).mkdir(parents=True, exist_ok=True)
            
            with open(credentials_path, 'w') as f:
                json.dump(credentials, f, indent=4)
            logger.debug(f"Saved credentials to {credentials_path}")
        except Exception as e:
            logger.error(f"Failed to save credentials to {credentials_path}: {str(e)}")
