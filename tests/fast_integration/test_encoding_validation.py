#!/usr/bin/env python3
"""
Encoding Validation Test
Tests all files for ASCII compatibility and emoji detection.
"""

import sys
from pathlib import Path
from typing import Dict


def test_file_encoding() -> None:
    """Test encoding validation using _all_files_check function."""
    success = _all_files_check()
    assert success, "Encoding validation failed for some files"


def _test_file_encoding_detailed(file_path: Path) -> Dict:
    """Test a single file for encoding issues."""
    result = {
        "file": str(file_path),
        "ascii_compatible": False,
        "errors": [],
        "emojis_found": [],
    }

    try:
        # Test ASCII compatibility
        try:
            with open(file_path, "r", encoding="ascii") as f:
                f.read()
            result["ascii_compatible"] = True
        except UnicodeDecodeError as e:
            result["ascii_compatible"] = False
            result["errors"].append(
                f"ASCII decode error at {e.start}-{e.end}: {e.reason}"
            )

        # Read as UTF-8 to check for emojis
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()

            # Check for common emoji ranges and specific problematic characters
            emoji_ranges = [
                (0x1F600, 0x1F64F),  # Emoticons
                (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
                (0x1F680, 0x1F6FF),  # Transport and Map
                (0x1F1E0, 0x1F1FF),  # Regional indicators
                (0x2600, 0x26FF),  # Miscellaneous symbols
                (0x2700, 0x27BF),  # Dingbats
                (0xFE00, 0xFE0F),  # Variation selectors
                (0x1F900, 0x1F9FF),  # Supplemental symbols
            ]

            # Common emoji characters we're replacing
            common_emojis = {
                "\u2713": "checkmark",  # ✓
                "\u274c": "cross mark",  # ❌
                "\u2705": "green check",  # ✅
                "\u26a0": "warning",  # ⚠
                "\ufe0f": "variation sel",  # ️
                "\u2139": "info",  # ℹ
                "📋": "clipboard",
                "🚀": "rocket",
                "🔧": "wrench",
                "🔍": "magnifier",
                "🛑": "stop",
            }

            for i, char in enumerate(text_content):
                char_code = ord(char)

                # Check specific emoji characters
                if char in common_emojis:
                    result["emojis_found"].append(
                        {
                            "char": char,
                            "unicode": f"U+{char_code:04X}",
                            "position": i,
                            "description": common_emojis[char],
                        }
                    )
                    continue

                # Check emoji ranges
                for start, end in emoji_ranges:
                    if start <= char_code <= end:
                        result["emojis_found"].append(
                            {
                                "char": char,
                                "unicode": f"U+{char_code:04X}",
                                "position": i,
                                "description": "emoji range",
                            }
                        )
                        break

        except Exception as e:
            result["errors"].append(f"Text processing error: {e}")

    except Exception as e:
        result["errors"].append(f"File read error: {e}")

    return result


def _all_files_check():
    """Test all relevant files for encoding issues."""
    project_root = Path(__file__).parent.parent

    # Files to test
    test_files = [
        # Python files
        "tools/search_helper.py",
        "tools/index_project.py",
        "mcp_server/server.py",
        "tests/integration/test_complete_workflow.py",
        "tests/integration/test_system.py",
        # PowerShell files - NOTE: configure_claude_code.ps1 and verify_claude_config.ps1 moved to _archive
        # "scripts/powershell/install-windows.ps1",  # Removed - functionality in install-windows.bat
        # "scripts/powershell/configure_claude_code.ps1",  # Moved to _archive/powershell_scripts/
        "scripts/powershell/hf_auth.ps1",  # Still in use
        # Batch files
        "start_mcp_server.bat",
        "scripts/batch/manual_configure.bat",  # New: Python-based configuration wrapper
        # "td_tools.bat", # Removed - functionality integrated into main launcher
    ]

    print("=" * 70)
    print("ENCODING VALIDATION TEST RESULTS")
    print("=" * 70)

    passed = 0
    failed = 0

    for file_path in test_files:
        full_path = project_root / file_path

        if not full_path.exists():
            print(f"[SKIP] {file_path} - File not found")
            continue

        result = _test_file_encoding_detailed(full_path)

        # Determine pass/fail
        is_ascii = result["ascii_compatible"]
        has_emojis = len(result["emojis_found"]) > 0
        has_errors = len(result["errors"]) > 0

        if is_ascii and not has_emojis and not has_errors:
            print(f"[PASS] {file_path}")
            print("       ASCII: OK")
            passed += 1
        else:
            print(f"[FAIL] {file_path}")
            if not is_ascii:
                print("       ASCII: FAILED")
            if has_emojis:
                print(f"       Emojis found: {len(result['emojis_found'])}")
                for emoji in result["emojis_found"][:5]:  # Show first 5
                    print(
                        f"         - {emoji['description']} ({emoji['unicode']}) at pos {emoji['position']}"
                    )
            if has_errors:
                print(f"       Errors: {len(result['errors'])}")
                for error in result["errors"]:
                    print(f"         - {error}")
            failed += 1

        print()

    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total files tested: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("[SUCCESS] All files are ASCII-compatible with no emojis!")
        return True
    else:
        print(f"[ERROR] {failed} files have encoding issues or emojis")
        return False


if __name__ == "__main__":
    success = _all_files_check()
    sys.exit(0 if success else 1)
