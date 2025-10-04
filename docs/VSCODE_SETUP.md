# VSCode Setup Guide

Complete guide for configuring Visual Studio Code with Ruff linting and auto-formatting for this project.

## Table of Contents

- [Quick Start](#quick-start)
- [Workspace Settings](#workspace-settings)
- [Global Settings Updates](#global-settings-updates)
- [Global vs Workspace Settings](#global-vs-workspace-settings)
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

### Recommended Global Configuration

To enable Ruff across **all Python projects**, add these settings to your global configuration:

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

  // Ruff global configuration (works across all Python projects)
  "ruff.enable": true,
  "ruff.organizeImports": true,
  "ruff.fixAll": true,
  "ruff.importStrategy": "fromEnvironment",  // Auto-detect Ruff from active Python environment
  "ruff.configurationPreference": "filesystemFirst",  // Projects override global settings
  "ruff.nativeServer": "on",  // Use native Rust-based server
  "ruff.showSyntaxErrors": true,  // Display syntax errors
  "ruff.codeAction.disableRuleComment.enable": true,  // Quick Fix: Add noqa comments
  "ruff.codeAction.fixViolation.enable": true,  // Quick Fix: Auto-fix violations

  // Global code actions (for non-Python files)
  "editor.codeActionsOnSave": {
    "source.fixAll.markdownlint": "explicit"
  }
}
```

### What These Settings Do

**Python File Behavior:**
- **`[python]` section**: Enables auto-formatting and auto-fix on save for all Python files
  - `editor.defaultFormatter: "charliermarsh.ruff"` - Use Ruff as formatter
  - `editor.formatOnSave: true` - Auto-format on save
  - `editor.codeActionsOnSave` - Auto-fix and organize imports on save

**Core Ruff Settings:**
- **`ruff.enable`**: Activates Ruff extension globally
- **`ruff.organizeImports`**: Enables import sorting feature
- **`ruff.fixAll`**: Enables auto-fix for all fixable issues
- **`ruff.importStrategy: "fromEnvironment"`**: Automatically finds Ruff in your project's virtual environment or system Python

**Advanced Settings:**
- **`ruff.configurationPreference: "filesystemFirst"`**: **CRITICAL** - Ensures project `pyproject.toml` files override global settings (respects project-specific rules)
- **`ruff.nativeServer: "on"`**: Forces use of modern Rust-based language server (faster, more features)
- **`ruff.showSyntaxErrors: true`**: Displays syntax errors in real-time
- **`ruff.codeAction.disableRuleComment.enable`**: Enables Quick Fix to add `# noqa: E501` comments to suppress specific rules
- **`ruff.codeAction.fixViolation.enable`**: Enables Quick Fix menu to manually fix individual violations via right-click

### Understanding `configurationPreference` (Critical Setting)

The `ruff.configurationPreference` setting controls how VSCode and project configuration files interact:

**Options:**
1. **`"editorFirst"`** (default) - VSCode settings override `pyproject.toml`
2. **`"filesystemFirst"`** (recommended) - `pyproject.toml` overrides VSCode settings
3. **`"editorOnly"`** - Ignore `pyproject.toml` completely

**Why `"filesystemFirst"` is Recommended:**

```
❌ "editorFirst" (Default Behavior):
Global settings.json → OVERRIDES → Project pyproject.toml
Problem: Global rules override project-specific configuration!

✅ "filesystemFirst" (Recommended):
Project pyproject.toml → OVERRIDES → Global settings.json
Benefit: Projects control their own rules, global acts as fallback
```

**Example Scenario:**
- Global settings: `ruff.lint.select = ["E", "F"]` (hypothetical)
- Project `pyproject.toml`: `select = ["E", "F", "B", "C4"]`

With `"editorFirst"`: Project gets only `["E", "F"]` ❌
With `"filesystemFirst"`: Project gets `["E", "F", "B", "C4"]` ✅

**Recommendation:** Always use `"filesystemFirst"` to respect project-specific configuration.

---

### System Python Installation (Recommended)

For consistent Ruff behavior across all projects, install Ruff in your system Python:

```bash
# Install in system Python (provides fallback when project has no .venv)
pip install ruff

# Verify installation
ruff --version  # Should show: ruff 0.13.3 or later
```

**Benefits:**
- ✅ Consistent Ruff version across projects without `.venv`
- ✅ Works immediately in new Python projects
- ✅ Fallback when project-specific Ruff not found

---

## Global vs Workspace Settings

Understanding how VSCode settings interact is crucial for managing Ruff across multiple projects.

### Settings Priority Order

**Highest to Lowest Priority:**
```
Workspace Settings (.vscode/settings.json)
    ↓
User Settings (global: AppData/Roaming/Code/User/settings.json)
    ↓
Default Settings
```

**Key Rule:** Workspace settings completely override user settings for primitives and arrays. Objects are merged.

### Behavior in Different Scenarios

#### **Scenario 1: Project WITH Workspace Settings** (This Project)

**Settings Source:**
- Workspace: `.vscode/settings.json` (project-specific)
- User: Global settings (ignored for overridden values)

**Ruff Executable:**
- Explicitly defined: `${workspaceFolder}/.venv/Scripts/ruff.exe`
- Uses project's Ruff version from `.venv`

**Configuration:**
- Project's `pyproject.toml` (explicit path in settings)
- Full control over Ruff rules

**Result:** ✅ Perfect isolation, project-specific configuration

---

#### **Scenario 2: Project WITH .venv, NO Workspace Settings**

**Settings Source:**
- User: Global settings only

**Ruff Executable:**
- Auto-detected via `importStrategy: "fromEnvironment"`
- VSCode detects `.venv` and looks for Ruff there
- If found in `.venv/Scripts/ruff.exe` → uses it
- If not found → falls back to system Python or bundled Ruff

**Configuration:**
- ❌ No explicit `pyproject.toml` reference (global settings can't use `${workspaceFolder}`)
- ⚠️ Ruff will search for `pyproject.toml` in project root automatically
- ✅ Will use project config if `pyproject.toml` exists

**Result:** ⚠️ Works well if project has `pyproject.toml` in root and Ruff in `.venv`

---

#### **Scenario 3: Project WITHOUT .venv, NO Workspace Settings**

**Settings Source:**
- User: Global settings only

**Ruff Executable:**
- System Python's Ruff (if installed globally: `pip install ruff`)
- OR bundled Ruff (comes with VSCode extension)

**Configuration:**
- ❌ No project-specific configuration
- Uses Ruff's default rules

**Result:** ⚠️ Works but no project customization

---

### How Ruff Extension Finds the Executable

**Detection Order:**

1. **Explicit `ruff.path`** (highest priority)
   - Workspace setting: `"ruff.path": ["${workspaceFolder}/.venv/Scripts/ruff.exe"]`
   - Global setting: `"ruff.path": ["C:\\Python311\\Scripts\\ruff.exe"]`

2. **`importStrategy: "fromEnvironment"`** (default)
   - Checks active Python interpreter's environment
   - If VSCode detects `.venv` → looks in `.venv/Scripts/` or `.venv/bin/`
   - If found → uses project's Ruff
   - If not found → next step

3. **System Python**
   - Checks system Python's `Scripts` directory
   - If `ruff.exe` found → uses it

4. **Bundled Ruff** (final fallback)
   - Extension ships with Ruff binary
   - Always available as last resort
   - Version may differ from project requirements

### Recommendations by Project Type

#### **Python Projects with Virtual Environments** (Best Practice)

```json
// .vscode/settings.json (workspace)
{
  "ruff.enable": true,
  "ruff.path": ["${workspaceFolder}/.venv/Scripts/ruff.exe"],
  "ruff.configuration": "${workspaceFolder}/pyproject.toml",
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe"
}
```

**Why:** Full control, isolated dependencies, reproducible across team.

---

#### **Quick Python Scripts** (No .venv)

- Rely on global settings + system Python Ruff
- No workspace settings needed
- Works immediately with minimal setup

---

#### **New Python Projects** (Template Approach)

1. Create project directory
2. Copy `.vscode/settings.json` template
3. Create `.venv` and install dependencies
4. Customize `pyproject.toml`

---

### Common Questions

**Q: Do I need Ruff in system Python?**
- **A:** No, but recommended for consistency. The extension has a bundled Ruff as fallback.

**Q: Will workspace settings break global settings?**
- **A:** No, they only override conflicting values. Non-conflicting global settings still apply.

**Q: Can I use `${workspaceFolder}` in global settings?**
- **A:** No, workspace variables only work in workspace settings. Use absolute paths in global settings.

**Q: What if my project has a different Ruff version than system Python?**
- **A:** Use workspace settings with explicit `ruff.path` pointing to project's `.venv`. Workspace settings override global.

**Q: How do I ensure team members get the same setup?**
- **A:** Commit `.vscode/settings.json` to git. Each developer gets identical workspace settings.

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

### Legacy Ruff Settings (Deprecated)

**Issue**: VSCode shows warnings about deprecated `ruff.lint.run` or `ruff.lint.args`

**Solution**: The legacy `ruff-lsp` server has been replaced by the native Rust-based server.

**Migration steps**:
1. Remove deprecated settings from `.vscode/settings.json`:
   - `"ruff.lint.run": "onSave"` (no longer needed; native server runs on every keystroke)
   - `"ruff.lint.args": ["--unsafe-fixes"]` (move to `pyproject.toml`)

2. Add to `pyproject.toml` under `[tool.ruff.lint]`:
   ```toml
   unsafe-fixes = true
   ```

3. Reload VSCode: `Ctrl+Shift+P` → "Developer: Reload Window"

**Reference**: [Migration Guide](https://docs.astral.sh/ruff/editors/migration/)

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
1. **Unsafe fixes disabled**: Check `pyproject.toml` has `unsafe-fixes = true` under `[tool.ruff.lint]`
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
unsafe-fixes = true  # Enable unsafe fixes (e.g., unused variable removal)
```

VSCode automatically reads this file when using the workspace settings.

**Note**: `unsafe-fixes` enables more aggressive automatic fixes that are safe in most cases but might occasionally need review.

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
