# VSCode Setup Guide

Complete guide for configuring Visual Studio Code with Ruff linting and auto-formatting for this project.

## Table of Contents

- [Quick Start](#quick-start)
- [Workspace Settings](#workspace-settings)
- [Global Settings Updates](#global-settings-updates)
- [Extensions](#extensions)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

1. **Open this project in VSCode**
2. **Install recommended extensions** (VSCode will prompt you)
   - Primary: `charliermarsh.ruff`
   - Optional: See `.vscode/extensions.json`
3. **Update your global settings** (see below)
4. **Reload VSCode**: `Ctrl+Shift+P` → "Reload Window"

---

## Workspace Settings

The project includes `.vscode/settings.json` with optimal configuration:

### Key Features:

- ✅ **Auto-fix on save**: Ruff automatically fixes linting issues when you save
- ✅ **Auto-format on save**: Code formatted with Ruff (Black-compatible)
- ✅ **Auto-organize imports**: Import statements sorted automatically
- ✅ **Project .venv**: Uses project's virtual environment, not system Python
- ✅ **pyproject.toml**: Respects project's Ruff configuration

### What Happens on Save:

1. **Import organizing**: isort-compatible import sorting
2. **Code formatting**: Black-compatible formatting (88 char line length)
3. **Linting fixes**: Auto-fixes safe issues (unused imports, whitespace, etc.)
4. **Unsafe fixes enabled**: Also fixes more complex issues (configurable)

---

## Global Settings Updates

**Location**: `C:\Users\Inter\AppData\Roaming\Code\User\settings.json`

### Current Issues:

1. **Duplicate `codeActionsOnSave`**: Present in both `[python]` and global scope
2. **Per-file ignores**: Should be in `pyproject.toml`, not VSCode settings
3. **Missing Ruff path**: Extension may not find project's Ruff installation

### Recommended Changes:

Replace your Python-specific settings with:

```json
{
  // Python specific settings
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },

  // Global code actions (for non-Python files)
  "editor.codeActionsOnSave": {
    "source.fixAll.markdownlint": "explicit"
  },

  // Remove this section entirely (handled by pyproject.toml):
  // "ruff.configuration": { ... }
}
```

### Before & After Comparison:

**Before** (Your current global settings):
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll.ruff": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "ruff.configuration": {
    "lint": {
      "per-file-ignores": {
        "*.py": ["F821"]
      }
    }
  },
  "editor.codeActionsOnSave": {  // DUPLICATE!
    "source.fixAll.ruff": "explicit",
    "source.fixAll.markdownlint": "explicit",
    "source.organizeImports": "explicit"
  }
}
```

**After** (Recommended):
```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  },
  "editor.codeActionsOnSave": {
    "source.fixAll.markdownlint": "explicit"
  }
}
```

**Changes Explained**:
- ✅ Removed duplicate `codeActionsOnSave`
- ✅ Changed `source.fixAll.ruff` → `source.fixAll` (workspace handles Ruff-specific)
- ✅ Removed `ruff.configuration` (now in `pyproject.toml`)
- ✅ Kept Markdown linting in global scope

---

## Extensions

### Required:

- **charliermarsh.ruff** (v2024.x or later)
  - Linting + formatting in one extension
  - Replaces: black, isort, flake8, pylint

### Recommended:

- **ms-python.python** - Python language support
- **ms-python.vscode-pylance** - Fast Python language server
- **slevesque.shader** - GLSL syntax highlighting (for this project)

### Not Needed (Ruff replaces these):

- ❌ ms-python.black-formatter
- ❌ ms-python.isort
- ❌ ms-python.flake8

---

## Troubleshooting

### Ruff Not Auto-Fixing on Save

**Check 1**: Verify Ruff extension is installed
```
Extensions sidebar → Search "Ruff" → Install charliermarsh.ruff
```

**Check 2**: Verify Ruff path is correct
```
Ctrl+Shift+P → "Preferences: Open Workspace Settings (JSON)"
Verify: "ruff.path": ["${workspaceFolder}/.venv/Scripts/ruff.exe"]
```

**Check 3**: Check Ruff is installed in .venv
```batch
.venv\Scripts\ruff.exe --version
# Should show: ruff 0.13.3 or later
```

**Check 4**: Reload VSCode window
```
Ctrl+Shift+P → "Developer: Reload Window"
```

### Import Sorting Not Working

**Issue**: Imports not being organized on save

**Solution**: Ensure both settings are enabled:
```json
"ruff.organizeImports": true,
"editor.codeActionsOnSave": {
  "source.organizeImports": "explicit"
}
```

### Ruff Using Wrong Configuration

**Issue**: Ruff not respecting `pyproject.toml` rules

**Solution**: Point Ruff to config file explicitly:
```json
"ruff.configuration": "${workspaceFolder}/pyproject.toml"
```

### Format on Save Not Working

**Check settings priority**:
1. Workspace settings (`.vscode/settings.json`) override global
2. User settings (`settings.json`) override defaults
3. Check for conflicting extensions (Black, isort, etc.)

**Verify**:
```json
"[python]": {
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "charliermarsh.ruff"
}
```

### Ruff Extension Shows Errors But Doesn't Auto-Fix

**Issue**: Red squiggles visible but not fixed on save

**Possible causes**:
1. **Unsafe fixes disabled**: Add `"ruff.lint.args": ["--unsafe-fixes"]`
2. **Manual fix required**: Some errors need manual intervention
3. **Syntax errors**: Ruff can't fix code that doesn't parse

**Check VSCode Output**:
```
View → Output → Select "Ruff" from dropdown
```

---

## Testing Your Setup

### Test 1: Format on Save

1. Open any Python file (e.g., `mcp_server/server.py`)
2. Add extra whitespace or misaligned code
3. Save file (`Ctrl+S`)
4. Code should auto-format immediately

### Test 2: Import Sorting

1. Open a Python file with imports
2. Scramble the import order (put third-party before stdlib)
3. Save file
4. Imports should reorganize automatically

### Test 3: Auto-Fix Linting

1. Open a Python file
2. Add unused import: `import os`
3. Save file
4. Unused import should be removed automatically

### Test 4: Unsafe Fixes

1. Open a Python file
2. Add: `if x == True:` (should be `if x:`)
3. Save file
4. Should auto-fix to `if x:`

---

## Project-Specific Configuration

This project's Ruff configuration is in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88
target-version = "py311"
exclude = ["_archive", "tests/test_data"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4"]
ignore = ["E501"]  # Line too long (handled by formatter)
```

VSCode automatically reads this file when using the workspace settings.

---

## Summary

**Workflow**:
1. Edit Python file
2. Save (`Ctrl+S`)
3. Ruff automatically:
   - Sorts imports
   - Formats code
   - Fixes linting issues
4. Ready to commit!

**Consistency**:
- ✅ Same rules as `scripts/git/check_lint.bat`
- ✅ Same rules as GitHub Actions CI
- ✅ Same rules as team members

**Performance**:
- 🚀 Instant formatting (<100ms)
- 🚀 Real-time error highlighting
- 🚀 No manual linting needed
