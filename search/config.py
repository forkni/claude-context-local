"""Configuration system for search modes and hybrid search features."""

import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class SearchConfig:
    """Configuration for search behavior."""

    # Search Mode Configuration
    default_search_mode: str = "hybrid"  # hybrid, semantic, bm25, auto
    enable_hybrid_search: bool = True

    # Hybrid Search Weights
    bm25_weight: float = 0.4
    dense_weight: float = 0.6

    # Performance Settings
    use_parallel_search: bool = True
    max_parallel_workers: int = 2

    # BM25 Configuration
    bm25_k_parameter: int = 100
    bm25_use_stopwords: bool = True
    min_bm25_score: float = 0.1

    # Reranking Configuration
    rrf_k_parameter: int = 100
    enable_result_reranking: bool = True

    # GPU Configuration
    prefer_gpu: bool = True
    gpu_memory_threshold: float = 0.8

    # Auto-reindexing
    enable_auto_reindex: bool = True
    max_index_age_minutes: float = 5.0

    # Search Result Limits
    default_k: int = 5
    max_k: int = 50

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SearchConfig":
        """Create from dictionary."""
        # Filter only known fields to avoid TypeError
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


class SearchConfigManager:
    """Manages search configuration from environment variables and config files."""

    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or self._get_default_config_path()
        self._config = None

    def _get_default_config_path(self) -> str:
        """Get default config file path."""
        # Try common locations
        candidates = [
            "search_config.json",
            ".search_config.json",
            os.path.expanduser("~/.claude-context-mcp/search_config.json"),
        ]

        for candidate in candidates:
            if os.path.exists(candidate):
                return candidate

        # Return first candidate as default
        return candidates[0]

    def load_config(self) -> SearchConfig:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config

        # Start with defaults
        config_dict = {}

        # Load from file if exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config_dict = json.load(f)
                self.logger.info(f"Loaded search config from {self.config_file}")
            except Exception as e:
                self.logger.warning(
                    f"Failed to load config file {self.config_file}: {e}"
                )

        # Override with environment variables
        env_overrides = self._load_from_environment()
        config_dict.update(env_overrides)

        # Create config object
        self._config = SearchConfig.from_dict(config_dict)

        self.logger.info(
            f"Search mode: {self._config.default_search_mode}, "
            f"hybrid enabled: {self._config.enable_hybrid_search}"
        )

        return self._config

    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mapping = {
            "CLAUDE_SEARCH_MODE": ("default_search_mode", str),
            "CLAUDE_ENABLE_HYBRID": ("enable_hybrid_search", self._bool_from_env),
            "CLAUDE_BM25_WEIGHT": ("bm25_weight", float),
            "CLAUDE_DENSE_WEIGHT": ("dense_weight", float),
            "CLAUDE_USE_PARALLEL": ("use_parallel_search", self._bool_from_env),
            "CLAUDE_PREFER_GPU": ("prefer_gpu", self._bool_from_env),
            "CLAUDE_GPU_THRESHOLD": ("gpu_memory_threshold", float),
            "CLAUDE_AUTO_REINDEX": ("enable_auto_reindex", self._bool_from_env),
            "CLAUDE_MAX_INDEX_AGE": ("max_index_age_minutes", float),
            "CLAUDE_DEFAULT_K": ("default_k", int),
            "CLAUDE_MAX_K": ("max_k", int),
        }

        config_dict = {}
        for env_var, (config_key, converter) in env_mapping.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                try:
                    config_dict[config_key] = converter(env_value)
                    self.logger.debug(
                        f"Set {config_key} = {config_dict[config_key]} from {env_var}"
                    )
                except ValueError as e:
                    self.logger.warning(
                        f"Invalid value for {env_var}: {env_value} ({e})"
                    )

        return config_dict

    def _bool_from_env(self, value: str) -> bool:
        """Convert environment variable string to boolean."""
        return value.lower() in ("true", "1", "yes", "on", "enabled")

    def save_config(self, config: SearchConfig) -> None:
        """Save configuration to file."""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)

            # Save to file
            with open(self.config_file, "w") as f:
                json.dump(config.to_dict(), f, indent=2)

            self.logger.info(f"Saved search config to {self.config_file}")
            self._config = config  # Update cached config

        except Exception as e:
            self.logger.error(f"Failed to save config to {self.config_file}: {e}")

    def get_search_mode_for_query(
        self, query: str, explicit_mode: Optional[str] = None
    ) -> str:
        """Determine best search mode for a query."""
        config = self.load_config()

        # Use explicit mode if provided
        if explicit_mode and explicit_mode != "auto":
            return explicit_mode

        # Use default mode if not auto
        if config.default_search_mode != "auto":
            return config.default_search_mode

        # Auto-detect based on query characteristics
        query_lower = query.lower()

        # Text-heavy queries -> BM25
        if any(
            keyword in query_lower
            for keyword in ["text", "string", "message", "error", "log"]
        ):
            return "bm25"

        # Code structure queries -> semantic
        if any(
            keyword in query_lower
            for keyword in ["class", "function", "method", "interface"]
        ):
            return "semantic"

        # Default to hybrid for balanced approach
        return "hybrid"


# Global configuration manager instance
_config_manager: Optional[SearchConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> SearchConfigManager:
    """Get or create global configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SearchConfigManager(config_file)
    return _config_manager


def get_search_config() -> SearchConfig:
    """Get current search configuration."""
    return get_config_manager().load_config()


def is_hybrid_search_enabled() -> bool:
    """Check if hybrid search is enabled."""
    config = get_search_config()
    return config.enable_hybrid_search


def get_default_search_mode() -> str:
    """Get default search mode."""
    config = get_search_config()
    return config.default_search_mode
