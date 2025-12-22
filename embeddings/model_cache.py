"""Model cache management for HuggingFace models.

This module provides cache validation, path resolution, and cleanup functionality
for HuggingFace models, including split cache scenarios for trust_remote_code models.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


class ModelCacheManager:
    """Manages HuggingFace model cache validation and maintenance.

    Handles:
    - Cache path resolution for HuggingFace models
    - Cache validation (config, weights, tokenizer)
    - Split cache detection for trust_remote_code models
    - Incomplete download detection and cleanup
    - Symlink creation for split cache models

    Example:
        >>> manager = ModelCacheManager(
        ...     model_name="BAAI/bge-m3",
        ...     cache_dir="/path/to/cache",
        ...     model_config_getter=lambda: {"trust_remote_code": False}
        ... )
        >>> is_valid, reason = manager.validate_cache()
        >>> if is_valid:
        ...     local_path = manager.find_local_model_dir()
    """

    def __init__(
        self,
        model_name: str,
        cache_dir: str,
        model_config_getter: Callable[[], Dict],
    ):
        """Initialize model cache manager.

        Args:
            model_name: Name of the model (e.g., "BAAI/bge-m3")
            cache_dir: Path to custom cache directory
            model_config_getter: Callback function that returns model config dict
                                 (must include 'trust_remote_code' key)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._get_model_config = model_config_getter
        self._logger = logging.getLogger(__name__)

    def get_model_cache_path(self) -> Optional[Path]:
        """Get the HuggingFace cache directory path for this model.

        Returns the models--{org}--{name} directory, or None if cache_dir not set.
        Does NOT check if the path exists.

        Returns:
            Path to models--{org}--{name} directory, or None if cache_dir not set
        """
        if not self.cache_dir:
            return None

        cache_root = Path(self.cache_dir)

        # Hugging Face cache structure: cache_dir/models--{org}--{model_name}/
        # Handle both 'org/model_name' and 'model_name' formats
        parts = self.model_name.split("/")
        if len(parts) == 2:
            org, name = parts
            expected_model_dir_name = f"models--{org}--{name}"
        else:
            name = parts[0]
            expected_model_dir_name = f"models--{name}"

        return cache_root / expected_model_dir_name

    def get_default_hf_cache_path(self) -> Optional[Path]:
        """Get the default HuggingFace cache directory path for this model.

        This is used as a fallback when trust_remote_code models ignore cache_folder.

        Returns the models--{org}--{name} directory in default HF cache.

        Returns:
            Path to models--{org}--{name} directory in default HF cache
        """
        default_hf_cache = Path.home() / ".cache" / "huggingface" / "hub"

        # Hugging Face cache structure: cache_dir/models--{org}--{model_name}/
        parts = self.model_name.split("/")
        if len(parts) == 2:
            org, name = parts
            expected_model_dir_name = f"models--{org}--{name}"
        else:
            name = parts[0]
            expected_model_dir_name = f"models--{name}"

        return default_hf_cache / expected_model_dir_name

    def check_config_at_location(self, cache_path: Path) -> bool:
        """Check if config.json exists and is valid at location.

        Used for split cache validation where config may be in custom cache
        while model weights are in default HuggingFace cache.

        Args:
            cache_path: Path to models--{org}--{name} directory to check

        Returns:
            True if valid config.json found, False otherwise
        """
        if not cache_path or not cache_path.exists():
            return False

        try:
            # Find snapshot directories (skip empty ones)
            all_snapshots = list(cache_path.glob("snapshots/*"))
            if not all_snapshots:
                return False

            # Filter out empty snapshots
            valid_snapshots = [s for s in all_snapshots if list(s.iterdir())]
            if not valid_snapshots:
                return False

            # Use latest valid snapshot
            snapshot_dir = max(valid_snapshots, key=lambda p: p.stat().st_mtime)

            # Check if config.json exists
            config_path = snapshot_dir / "config.json"
            return config_path.exists()

        except Exception as e:
            self._logger.debug(f"Error checking config at {cache_path}: {e}")
            return False

    def check_weights_at_location(self, cache_path: Path) -> bool:
        """Check if model weights exist at location (any format).

        Used for split cache validation where model weights may be in default
        HuggingFace cache while config is in custom cache.

        Supports both single-file formats (model.safetensors, pytorch_model.bin)
        and sharded formats (*.index.json).

        Args:
            cache_path: Path to models--{org}--{name} directory to check

        Returns:
            True if model weights found in any format, False otherwise
        """
        if not cache_path or not cache_path.exists():
            return False

        try:
            # Find snapshot directories (skip empty ones)
            all_snapshots = list(cache_path.glob("snapshots/*"))
            if not all_snapshots:
                return False

            # Filter out empty snapshots
            valid_snapshots = [s for s in all_snapshots if list(s.iterdir())]
            if not valid_snapshots:
                return False

            # Use latest valid snapshot
            snapshot_dir = max(valid_snapshots, key=lambda p: p.stat().st_mtime)

            # Check for model weights in any format
            has_weights = (
                (snapshot_dir / "model.safetensors").exists()
                or (snapshot_dir / "pytorch_model.bin").exists()
                or (snapshot_dir / "model.safetensors.index.json").exists()
                or (snapshot_dir / "pytorch_model.bin.index.json").exists()
            )

            return has_weights

        except Exception as e:
            self._logger.debug(f"Error checking weights at {cache_path}: {e}")
            return False

    def ensure_split_cache_symlink(self) -> bool:
        """Ensure symlink exists for split cache models (trust_remote_code).

        For models with trust_remote_code=True, HuggingFace may store:
        - Config/tokenizer: custom cache folder
        - Model weights: default HF cache (~/.cache/huggingface/hub)

        This method creates a symlink from custom→default for model.safetensors
        so SentenceTransformer can find all files in one location.

        Returns:
            True if symlink was created or already exists, False otherwise
        """
        try:
            model_config = self._get_model_config()
            if not model_config.get("trust_remote_code", False):
                return False  # Not a split cache model

            custom_cache_path = self.get_model_cache_path()
            default_cache_path = self.get_default_hf_cache_path()

            # Check for split cache scenario
            custom_has_config = self.check_config_at_location(custom_cache_path)
            default_has_weights = self.check_weights_at_location(default_cache_path)

            if not (custom_has_config and default_has_weights):
                return False  # Not a split cache scenario

            # Get snapshot directories
            custom_snapshots = [
                s for s in custom_cache_path.glob("snapshots/*") if list(s.iterdir())
            ]
            default_snapshots = [
                s for s in default_cache_path.glob("snapshots/*") if list(s.iterdir())
            ]

            if not custom_snapshots or not default_snapshots:
                return False

            custom_snapshot = max(custom_snapshots, key=lambda p: p.stat().st_mtime)
            default_snapshot = max(default_snapshots, key=lambda p: p.stat().st_mtime)

            custom_weights = custom_snapshot / "model.safetensors"
            default_weights = default_snapshot / "model.safetensors"

            if custom_weights.exists():
                self._logger.debug(
                    f"[SPLIT CACHE] Weights already accessible: {custom_weights}"
                )
                return True  # Already exists (symlink or copy)

            if not default_weights.exists():
                return False  # No weights to link to

            # Create symlink (or copy as fallback)
            try:
                custom_weights.symlink_to(default_weights)
                self._logger.info(
                    f"[SYMLINK CREATED] model.safetensors symlink created\n"
                    f"  From: {custom_weights}\n"
                    f"  To: {default_weights}\n"
                    f"  Note: Future loads will be instant."
                )
                return True
            except OSError as e:
                self._logger.warning(f"[SYMLINK FAILED] {e}, falling back to copy...")
                shutil.copy2(default_weights, custom_weights)
                self._logger.info(
                    f"[COPY CREATED] model.safetensors copied to {custom_weights}"
                )
                return True

        except Exception as e:
            self._logger.debug(f"Error in ensure_split_cache_symlink: {e}")
            return False

    def check_cache_at_location(self, cache_path: Path) -> Tuple[bool, str]:
        """Check if valid model cache exists at a specific location.

        Args:
            cache_path: Path to models--{org}--{name} directory to validate

        Returns:
            (is_valid, reason) - True if cache is complete and valid, False with reason if not
        """
        # Check cache directory structure exists
        if not cache_path or not cache_path.exists():
            return False, "Cache directory not found"

        try:
            # Find snapshot directories (skip empty ones from interrupted downloads)
            all_snapshots = list(cache_path.glob("snapshots/*"))
            if not all_snapshots:
                return False, "No snapshots found in cache"

            # Filter out empty snapshots (common with interrupted downloads)
            valid_snapshots = [s for s in all_snapshots if list(s.iterdir())]
            if not valid_snapshots:
                return False, "All snapshots are empty (interrupted downloads)"

            # Use latest valid snapshot (sorted by modification time)
            snapshot_dir = max(valid_snapshots, key=lambda p: p.stat().st_mtime)

            # CRITICAL: Validate config.json exists and is valid
            config_path = snapshot_dir / "config.json"
            if not config_path.exists():
                return False, "Missing config.json (corrupted download)"

            # Validate config.json is valid JSON with required keys
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Check for model_type or architectures (required by transformers)
                    if "model_type" not in config and "architectures" not in config:
                        return (
                            False,
                            "Invalid config.json (missing model_type and architectures)",
                        )
            except json.JSONDecodeError as e:
                return False, f"Corrupted config.json (invalid JSON): {e}"
            except Exception as e:
                return False, f"Cannot read config.json: {e}"

            # Validate model weights exist (single-file or sharded formats)
            has_safetensors = (snapshot_dir / "model.safetensors").exists()
            has_pytorch = (snapshot_dir / "pytorch_model.bin").exists()
            has_pytorch_index = (snapshot_dir / "pytorch_model.bin.index.json").exists()
            has_safetensors_index = (
                snapshot_dir / "model.safetensors.index.json"
            ).exists()

            # For sharded models, validate that actual shard files exist
            if has_safetensors_index or has_pytorch_index:
                # Parse index.json to find shard files
                index_file = snapshot_dir / (
                    "model.safetensors.index.json"
                    if has_safetensors_index
                    else "pytorch_model.bin.index.json"
                )
                try:
                    with open(index_file, "r", encoding="utf-8") as f:
                        index_data = json.load(f)
                        shard_files = set(index_data.get("weight_map", {}).values())

                        if not shard_files:
                            return (
                                False,
                                f"Invalid index file (no shards listed): {index_file.name}",
                            )

                        # Check that all shard files exist (either as actual files or symlinks)
                        missing_shards = []
                        incomplete_shards = []

                        for shard in shard_files:
                            shard_path = snapshot_dir / shard
                            if not shard_path.exists():
                                # Check if it's a symlink pointing to a blob
                                if shard_path.is_symlink():
                                    target = shard_path.resolve()
                                    if not target.exists():
                                        # Check if there's an incomplete blob
                                        incomplete_blob = (
                                            target.parent / f"{target.name}.incomplete"
                                        )
                                        if incomplete_blob.exists():
                                            size_mb = incomplete_blob.stat().st_size / (
                                                1024**2
                                            )
                                            incomplete_shards.append(
                                                f"{shard} ({size_mb:.1f}MB incomplete)"
                                            )
                                        else:
                                            missing_shards.append(
                                                f"{shard} -> {target.name} (broken symlink)"
                                            )
                                else:
                                    missing_shards.append(shard)

                        if incomplete_shards:
                            return (
                                False,
                                f"Incomplete downloads detected: {', '.join(incomplete_shards)}. Run cleanup to remove partial downloads.",
                            )

                        if missing_shards:
                            return (
                                False,
                                f"Missing shard files: {', '.join(missing_shards)}",
                            )

                except json.JSONDecodeError as e:
                    return False, f"Corrupted index file {index_file.name}: {e}"
                except Exception as e:
                    return False, f"Error validating shards: {e}"

            elif not (has_safetensors or has_pytorch):
                return False, "Missing model weights (no .safetensors or .bin files)"

            # Validate tokenizer files exist (at least one)
            tokenizer_files = [
                "tokenizer.json",
                "tokenizer_config.json",
                "vocab.txt",
                "sentencepiece.bpe.model",
                "tokenizer.model",
            ]
            has_tokenizer = any((snapshot_dir / f).exists() for f in tokenizer_files)
            if not has_tokenizer:
                return False, "Missing tokenizer files"

            # All checks passed
            return True, f"Valid cache at {snapshot_dir}"

        except Exception as e:
            self._logger.debug(f"Error during cache validation: {e}")
            return False, f"Validation error: {str(e)}"

    def validate_cache(self) -> Tuple[bool, str]:
        """Validate cached model integrity with fallback to default HuggingFace cache.

        Checks both custom cache location and default HuggingFace cache for models
        with trust_remote_code=True (which may ignore cache_folder parameter).

        Returns:
            (is_valid, reason) - True if cache is complete and valid in either location
        """
        # First, check custom cache location
        custom_cache_path = self.get_model_cache_path()
        custom_valid, custom_reason = self.check_cache_at_location(custom_cache_path)

        if custom_valid:
            return True, custom_reason

        # Custom cache invalid - check if this is a trust_remote_code model
        model_config = self._get_model_config()
        requires_trust_remote_code = model_config.get("trust_remote_code", False)

        if requires_trust_remote_code:
            # SPLIT CACHE VALIDATION: Check if config+tokenizer in custom, weights in default
            # trust_remote_code models often split cache:
            #   - Custom cache: config.json, tokenizer, Python code
            #   - Default HF cache: model.safetensors (weights only)
            default_cache_path = self.get_default_hf_cache_path()

            # Check what exists in each location
            custom_has_config = self.check_config_at_location(custom_cache_path)
            default_has_weights = self.check_weights_at_location(default_cache_path)

            if custom_has_config and default_has_weights:
                # Valid split cache scenario!
                self._logger.info(
                    f"[SPLIT CACHE VALID] trust_remote_code model detected.\n"
                    f"  Config/tokenizer: {custom_cache_path}\n"
                    f"  Model weights: {default_cache_path}\n"
                    f"  Reason: Models with trust_remote_code=True split cache across locations.\n"
                    f"  Impact: Model will load successfully using both cache locations."
                )
                return (
                    True,
                    "Valid (split cache: config in custom, weights in default HF cache)",
                )

            # Full fallback: Check if complete cache exists in default location
            default_valid, default_reason = self.check_cache_at_location(
                default_cache_path
            )

            if default_valid:
                # Complete cache found in default location instead of custom location
                self._logger.warning(
                    f"[CACHE LOCATION MISMATCH] Complete model cache found in default HuggingFace cache.\n"
                    f"  Expected: {custom_cache_path}\n"
                    f"  Found: {default_cache_path}\n"
                    f"  Reason: Models with trust_remote_code=True may ignore cache_folder parameter.\n"
                    f"  Impact: Model will load successfully but from default cache location."
                )
                return True, f"Valid (found in default HF cache): {default_reason}"

        # Cache invalid in both locations
        return False, custom_reason

    def check_incomplete_downloads(self) -> Tuple[bool, str]:
        """Check if there are incomplete downloads that could cause validation failures.

        Scans the blobs directory for .incomplete files from interrupted HuggingFace downloads.

        Returns:
            (has_incomplete, message) - True if incomplete files exist with descriptive message
        """
        try:
            model_cache_path = self.get_model_cache_path()
            if not model_cache_path or not model_cache_path.exists():
                return False, "No cache directory"

            blobs_dir = model_cache_path / "blobs"
            if not blobs_dir.exists():
                return False, "No blobs directory"

            incomplete_files = list(blobs_dir.glob("*.incomplete"))
            if not incomplete_files:
                return False, "No incomplete downloads"

            # Calculate total size of incomplete files
            total_size = sum(f.stat().st_size for f in incomplete_files)
            size_mb = total_size / (1024**2)

            message = (
                f"Found {len(incomplete_files)} incomplete download(s) ({size_mb:.1f} MB total). "
                f"These may be from interrupted downloads. "
                f"Files: {[f.name[:16] + '...' for f in incomplete_files[:3]]}"
            )

            return True, message

        except Exception as e:
            self._logger.debug(f"Error checking incomplete downloads: {e}")
            return False, f"Error: {str(e)}"

    def cleanup_incomplete_downloads(self) -> Tuple[int, List[str]]:
        """Detect and clean up incomplete downloads in the blobs directory.

        Removes .incomplete files that were created by interrupted HuggingFace downloads.
        This allows subsequent downloads to start fresh instead of failing validation.

        Returns:
            (count, file_list) - Number of incomplete files removed and their names
        """
        try:
            model_cache_path = self.get_model_cache_path()
            if not model_cache_path or not model_cache_path.exists():
                return 0, []

            blobs_dir = model_cache_path / "blobs"
            if not blobs_dir.exists():
                return 0, []

            incomplete_files = []
            removed_count = 0

            # Find all .incomplete files
            for incomplete_file in blobs_dir.glob("*.incomplete"):
                size_mb = incomplete_file.stat().st_size / (1024**2)
                incomplete_files.append(
                    f"{incomplete_file.name[:16]}... ({size_mb:.1f}MB)"
                )

                try:
                    incomplete_file.unlink()
                    removed_count += 1
                    self._logger.info(
                        f"Removed incomplete download: {incomplete_file.name} ({size_mb:.1f}MB)"
                    )
                except Exception as e:
                    self._logger.warning(
                        f"Failed to remove {incomplete_file.name}: {e}"
                    )

            if removed_count > 0:
                self._logger.info(
                    f"Cleanup complete: Removed {removed_count} incomplete file(s)"
                )

            return removed_count, incomplete_files

        except Exception as e:
            self._logger.warning(f"Error during incomplete file cleanup: {e}")
            return 0, []

    def is_cached(self) -> bool:
        """Check if model cache exists and is valid.

        Uses comprehensive validation to prevent loading corrupted caches.

        Returns:
            True if cache is valid, False otherwise
        """
        is_valid, _ = self.validate_cache()
        return is_valid

    def find_local_model_dir(self) -> Optional[Path]:
        """Locate the cached model directory if available.

        Returns the path to the snapshot directory containing the model files.
        Only returns path if cache is valid (uses validate_cache).

        Checks both custom cache and default HuggingFace cache for models with
        trust_remote_code=True.

        For split cache scenarios (config in custom, weights in default HF cache),
        returns the custom cache path so SentenceTransformer can find config.json
        and load weights from default cache automatically.

        Returns:
            Path to snapshot directory containing model files, or None if invalid
        """
        # Use validation to ensure cache is complete
        is_valid, reason = self.validate_cache()
        if not is_valid:
            self._logger.debug(f"Cache not valid: {reason}")
            return None

        try:
            # Check if this is a split cache scenario for trust_remote_code models
            model_config = self._get_model_config()
            requires_trust_remote_code = model_config.get("trust_remote_code", False)

            if requires_trust_remote_code:
                custom_cache_path = self.get_model_cache_path()
                default_cache_path = self.get_default_hf_cache_path()

                # Check for split cache: config in custom, weights in default
                custom_has_config = self.check_config_at_location(custom_cache_path)
                default_has_weights = self.check_weights_at_location(default_cache_path)

                if custom_has_config and default_has_weights:
                    # SPLIT CACHE: Ensure symlink exists for split cache
                    self.ensure_split_cache_symlink()
                    # Return custom snapshot path
                    custom_snapshots = [
                        s
                        for s in custom_cache_path.glob("snapshots/*")
                        if list(s.iterdir())
                    ]
                    if custom_snapshots:
                        return max(custom_snapshots, key=lambda p: p.stat().st_mtime)

            # Helper to get latest snapshot from a cache path if validation passes
            def get_latest_snapshot_if_valid(cache_path: Path) -> Optional[Path]:
                # Check if this specific cache location is valid
                valid, _ = self.check_cache_at_location(cache_path)
                if not valid:
                    return None

                if cache_path and cache_path.exists():
                    snapshots = list(cache_path.glob("snapshots/*"))
                    # Filter out empty snapshots
                    valid_snapshots = [s for s in snapshots if list(s.iterdir())]
                    if valid_snapshots:
                        return max(valid_snapshots, key=lambda p: p.stat().st_mtime)
                return None

            # First try custom cache location
            model_cache_path = self.get_model_cache_path()
            custom_snapshot = get_latest_snapshot_if_valid(model_cache_path)
            if custom_snapshot:
                return custom_snapshot

            # Fallback: Check default HuggingFace cache for trust_remote_code models
            if requires_trust_remote_code:
                default_cache_path = self.get_default_hf_cache_path()
                default_snapshot = get_latest_snapshot_if_valid(default_cache_path)
                if default_snapshot:
                    return default_snapshot

        except Exception as e:
            self._logger.debug(f"Error during find_local_model_dir: {e}")
            return None

        return None
