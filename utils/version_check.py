"""Runtime dependency version validation.

This module provides utilities to validate critical dependencies at startup,
ensuring clear error messages when versions don't meet requirements.
"""

import logging
from importlib.metadata import PackageNotFoundError, version


logger = logging.getLogger(__name__)

# Critical dependencies with minimum versions
CRITICAL_DEPS: dict[str, str] = {
    "torch": ">=2.8.0",
    "transformers": ">=4.30.0",
    "sentence-transformers": ">=2.2.0",
    "numpy": ">=1.24.0",
    "faiss-cpu": ">=1.7.0",
}


def parse_version_tuple(version_str: str) -> tuple[int, ...]:
    """Parse version string to tuple for comparison.

    Args:
        version_str: Version string like "2.8.0" or "2.8.0+cu128"

    Returns:
        Tuple of version numbers like (2, 8, 0), always at least 3 elements so
        that ``(2, 8) < (2, 8, 0)`` false-positive is avoided (#41).
    """
    # Remove build metadata (+cu128, etc.)
    version_str = version_str.split("+")[0]
    # Remove pre-release suffix robustly: find the first non-digit, non-dot
    # character after stripping build metadata, then truncate there.
    # The old ``split("a")[0].split("b")[0]`` approach wrongly truncates any
    # version segment that contains those letters (e.g. unlikely but fragile).
    import re

    version_str = re.split(r"[^0-9.]", version_str)[0].rstrip(".")
    # Parse into tuple and pad to at least 3 elements so that short versions
    # like "2.8" compare equal to "2.8.0" rather than less-than.
    parts = tuple(int(x) for x in version_str.split(".") if x.isdigit())
    while len(parts) < 3:
        parts = parts + (0,)
    return parts


def check_dependency(package: str, requirement: str) -> tuple[bool, str]:
    """Check if dependency meets requirement.

    Args:
        package: Package name (e.g., "torch")
        requirement: Version requirement (e.g., ">=2.0.0")

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        installed = version(package)
    except PackageNotFoundError:
        return False, (
            f"[FAIL] {package} is not installed\n"
            f"       Install with: pip install {package}"
        )

    # Parse requirement
    if requirement.startswith(">="):
        min_ver = requirement[2:].strip()
        try:
            installed_tuple = parse_version_tuple(installed)
            required_tuple = parse_version_tuple(min_ver)

            if installed_tuple < required_tuple:
                return False, (
                    f"[FAIL] {package}=={installed} is too old (required: {requirement})\n"
                    f"       Upgrade with: pip install --upgrade {package}"
                )
        except (ValueError, AttributeError) as e:
            # If parsing fails, log warning but don't fail
            logger.warning(f"Could not parse version for {package}: {e}")
            return True, f"[WARN] {package}=={installed} (version check skipped)"

    return True, f"[OK] {package}=={installed}"


def validate_critical_dependencies() -> tuple[bool, list[str]]:
    """Validate all critical dependencies at startup.

    Returns:
        Tuple of (all_valid: bool, messages: List[str])
    """
    all_valid = True
    messages = []

    for package, requirement in CRITICAL_DEPS.items():
        valid, message = check_dependency(package, requirement)
        if valid:
            logger.debug(message)
        else:
            logger.error(message)
            all_valid = False
        messages.append(message)

    return all_valid, messages


def print_validation_report() -> bool:
    """Print dependency validation report to stdout.

    Returns:
        True if all dependencies valid, False otherwise
    """
    print("=" * 60)
    print("Dependency Version Check")
    print("=" * 60)

    all_valid, messages = validate_critical_dependencies()

    for message in messages:
        print(message)

    print("=" * 60)

    if all_valid:
        print("[OK] All critical dependencies satisfied")
    else:
        print("[FAIL] Some dependencies have issues - functionality may be limited")

    print("=" * 60)

    return all_valid


if __name__ == "__main__":
    # Run validation report when executed directly
    import sys

    success = print_validation_report()
    sys.exit(0 if success else 1)
