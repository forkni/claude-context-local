"""Utility functions and helper classes."""

import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_string(text: str, max_length: int = 255) -> str:
    """Sanitize and truncate string input."""
    if not isinstance(text, str):
        text = str(text)
    
    # Remove any potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip()
    
    return sanitized.strip()


def format_timestamp(timestamp: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime object to string."""
    return timestamp.strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse timestamp string to datetime object."""
    try:
        return datetime.strptime(timestamp_str, format_str)
    except ValueError as e:
        raise ValueError(f"Invalid timestamp format: {e}")


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config = {}
        self.logger = logging.getLogger(__name__)
        
        if config_file and os.path.exists(config_file):
            self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            self.logger.info(f"Configuration loaded from {self.config_file}")
        except (IOError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to load configuration: {e}")
            self.config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self.config[key] = value
    
    def save_config(self) -> None:
        """Save configuration to file."""
        if not self.config_file:
            raise ValueError("No config file specified")
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Configuration saved to {self.config_file}")
        except IOError as e:
            self.logger.error(f"Failed to save configuration: {e}")


class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 3600):
        self.default_ttl = default_ttl
        self._cache = {}
        self._expiry = {}
    
    def get(self, key: str) -> Any:
        """Get value from cache."""
        if key not in self._cache:
            return None
        
        if key in self._expiry and datetime.now() > self._expiry[key]:
            self.delete(key)
            return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        self._cache[key] = value
        
        ttl = ttl or self.default_ttl
        if ttl > 0:
            self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        deleted = key in self._cache
        self._cache.pop(key, None)
        self._expiry.pop(key, None)
        return deleted
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._expiry.clear()
    
    def size(self) -> int:
        """Get number of items in cache."""
        return len(self._cache)


def retry_operation(func, max_attempts: int = 3, delay: float = 1.0):
    """Retry operation with exponential backoff."""
    import time
    
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt == max_attempts - 1:
                raise e
            
            wait_time = delay * (2 ** attempt)
            time.sleep(wait_time)
    
    return None


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    chunks = []
    for i in range(0, len(lst), chunk_size):
        chunks.append(lst[i:i + chunk_size])
    return chunks


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten nested dictionary."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)