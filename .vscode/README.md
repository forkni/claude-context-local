# VSCode Workspace Configuration

This directory contains VSCode-specific configuration for optimal development experience.

## Files

### `settings.json`

Workspace-specific settings that override global VSCode configuration:

- Python interpreter: Project's `.venv`
- Ruff linter/formatter: Auto-fix on save
- File exclusions: `__pycache__`, `_archive`, etc.

### `extensions.json`

Recommended extensions for this project:

- **Required**: Ruff (charliermarsh.ruff)
- **Recommended**: Python, Pylance, GLSL shader support

### `GLOBAL_SETTINGS_UPDATE.md`

Instructions for updating your global VSCode settings to work optimally with this project.

## Quick Setup

1. **Install Ruff extension**: VSCode will prompt when you open the project
2. **Update global settings**: Follow `GLOBAL_SETTINGS_UPDATE.md`
3. **Reload VSCode**: `Ctrl+Shift+P` → "Reload Window"

## How It Works

When you save a Python file (`Ctrl+S`):

1. **Imports organized** (isort-compatible)
2. **Code formatted** (Black-compatible, 88 chars)
3. **Linting issues fixed** (Ruff auto-fix)

All using the same rules as:

- `scripts/git/check_lint.bat`
- `scripts/git/fix_lint.bat`
- GitHub Actions CI

## Documentation

See `docs/VSCODE_SETUP.md` for comprehensive guide and troubleshooting.

## Configuration Source

All Ruff rules come from `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py311"
exclude = ["_archive", "tests/test_data"]
```

No need to configure rules in VSCode settings - they're centralized in `pyproject.toml`.
