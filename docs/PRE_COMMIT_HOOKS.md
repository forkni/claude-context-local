# Pre-Commit Hooks Guide

Automated code quality and validation checks that run before every commit.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [What Gets Checked](#what-gets-checked)
- [Installation](#installation)
- [Usage](#usage)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

Pre-commit hooks automatically validate your changes before creating a commit, catching issues early and preventing CI failures.

**Benefits:**

- ✅ Catches local-only file leaks
- ✅ Validates documentation structure
- ✅ Enforces code quality (Python)
- ✅ Offers auto-fix for lint errors
- ✅ Prevents CI failures
- ✅ Faster feedback than waiting for GitHub Actions

**Hook Location:**

- Template: `.githooks/pre-commit` (tracked in Git)
- Active hook: `.git/hooks/pre-commit` (local, not tracked)

---

## Quick Start

### First Time Setup

```batch
REM Install the hook
scripts\git\install_hooks.bat

REM Verify installation
dir .git\hooks\pre-commit
```

### Daily Usage

Just commit normally - the hook runs automatically:

```batch
git add .
git commit -m "feat: Add new feature"
```

If lint errors are detected, you'll be prompted:

```
⚠ Lint errors detected in Python files

Auto-fix lint issues? (yes/no/skip):
```

**Choices:**

- `yes` - Auto-fix errors, restage files, continue commit
- `no` - Abort commit, fix manually
- `skip` - Proceed with warning (not recommended)

---

## What Gets Checked

### 1. File Privacy Validation

**Prevents committing local-only files:**

- `CLAUDE.md` - Development context
- `MEMORY.md` - Session memory
- `_archive/` - Historical content (738+ files)
- `benchmark_results/` - Generated test data

**Behavior:**

- ❌ Blocks additions and modifications
- ✅ Allows deletions (removing from Git tracking)

### 2. Documentation Validation

**Ensures only authorized docs are public:**

**Allowed public docs** (10 files):

- `BENCHMARKS.md`
- `claude_code_config.md`
- `HYBRID_SEARCH_CONFIGURATION_GUIDE.md`
- `INSTALLATION_GUIDE.md`
- `MCP_TOOLS_REFERENCE.md`
- `MODEL_MIGRATION_GUIDE.md`
- `PYTORCH_COMPATIBILITY.md`
- `TESTING_GUIDE.md`
- `VSCODE_SETUP.md`
- `PRE_COMMIT_HOOKS.md`

**All other docs/** - Automatically blocked

### 3. Code Quality Checks (Python Only)

**Runs on staged `.py` files:**

**Tools used:**

1. **Ruff** - Linting (E, W, F, I, B, C4 rules)
2. **Black** - Formatting (88 char line length)
3. **isort** - Import sorting (Black-compatible)

**Same rules as:**

- `scripts/git/check_lint.bat`
- `scripts/git/fix_lint.bat`
- VSCode Ruff extension
- GitHub Actions CI

**What gets auto-fixed:**

- ✅ Unused imports
- ✅ Whitespace issues
- ✅ Import sorting
- ✅ Code formatting
- ✅ Simple linting issues (with `--unsafe-fixes`)

---

## Installation

### Option 1: Automated Install (Recommended)

```batch
scripts\git\install_hooks.bat
```

**What it does:**

1. Copies `.githooks/pre-commit` to `.git/hooks/pre-commit`
2. Verifies installation
3. Shows what the hook does

### Option 2: Manual Install

```batch
copy .githooks\pre-commit .git\hooks\pre-commit
```

### Verification

```batch
REM Check if hook is installed
dir .git\hooks\pre-commit

REM Should show:
REM pre-commit (no extension, executable)
```

---

## Usage

### Normal Commit Flow

```batch
# 1. Make changes
edit some_file.py

# 2. Stage changes
git add some_file.py

# 3. Commit (hook runs automatically)
git commit -m "feat: Add feature"
```

**Hook output:**

```
Checking for local-only files...
✓ No problematic local-only files detected
✓ Privacy protection active

Checking code quality...
✓ Code quality checks passed
```

### Commit with Lint Errors

```batch
git add file_with_errors.py
git commit -m "fix: Update logic"
```

**Hook output:**

```
Checking code quality...
⚠ Lint errors detected in Python files

Auto-fix lint issues? (yes/no/skip): yes

Running auto-fix...
✓ Files fixed and restaged
✓ Commit will proceed with fixed code
```

### Bypassing Hook (Emergency Only)

```batch
REM Skip all hooks (not recommended)
git commit --no-verify -m "message"

REM Or use alias
git commit -n -m "message"
```

**⚠ Warning:** Only bypass hooks if:

- Emergency hotfix needed
- You'll fix lint errors in next commit
- You know CI will fail (planned)

---

## Examples

### Example 1: Clean Commit

```batch
> git commit -m "feat: Add authentication"

Checking for local-only files...
✓ No problematic local-only files detected
✓ Privacy protection active

Checking code quality...
✓ Code quality checks passed

[development abc1234] feat: Add authentication
 2 files changed, 45 insertions(+)
```

**Result:** Commit succeeds immediately ✓

### Example 2: Auto-Fix Lint Errors

```batch
> git commit -m "fix: Update login logic"

Checking for local-only files...
✓ No problematic local-only files detected
✓ Privacy protection active

Checking code quality...
⚠ Lint errors detected in Python files

Auto-fix lint issues? (yes/no/skip): yes

Running auto-fix...

=== Code Quality Auto-Fixer ===
[1/3] Fixing import order with isort...
✓ isort completed

[2/3] Fixing code formatting with black...
✓ black completed

[3/3] Fixing code issues with ruff...
✓ ruff completed

✓ Files fixed and restaged
✓ Commit will proceed with fixed code

[development def5678] fix: Update login logic
 1 file changed, 12 insertions(+), 8 deletions(-)
```

**Result:** Errors auto-fixed, commit succeeds ✓

### Example 3: Abort on Lint Errors

```batch
> git commit -m "wip: Incomplete feature"

Checking code quality...
⚠ Lint errors detected in Python files

Auto-fix lint issues? (yes/no/skip): no

Commit aborted.

To fix lint errors, run:
  scripts\git\fix_lint.bat

Or to see errors:
  scripts\git\check_lint.bat
```

**Result:** Commit aborted, manual fix required ✓

### Example 4: Skip Lint Errors (Not Recommended)

```batch
> git commit -m "wip: Testing"

Checking code quality...
⚠ Lint errors detected in Python files

Auto-fix lint issues? (yes/no/skip): skip

⚠ Proceeding with lint warnings (not recommended)
⚠ CI may fail on push

[development ghi9012] wip: Testing
 1 file changed, 5 insertions(+), 2 deletions(-)
```

**Result:** Commit succeeds with warnings ⚠

### Example 5: Blocked - Local-Only File

```batch
> git add CLAUDE.md
> git commit -m "docs: Update context"

Checking for local-only files...
ERROR: Attempting to add or modify local-only files!

The following files must remain local only:
- CLAUDE.md (development context)
- MEMORY.md (session memory)
- _archive/ (764 historical files)
- benchmark_results/ (generated test data)

Problematic files:
A       CLAUDE.md

To fix this, reset the problematic files:
  git reset HEAD CLAUDE.md
```

**Result:** Commit blocked, file must be unstaged ✗

---

## Troubleshooting

### Hook Not Running

**Symptoms:** No output when committing, hook doesn't execute

**Solutions:**

1. **Check if hook is installed:**

   ```batch
   dir .git\hooks\pre-commit
   ```

   If missing, run: `scripts\git\install_hooks.bat`

2. **Check hook is executable:**
   Git hooks must be executable on Unix systems (not an issue on Windows)

3. **Verify you're in repo root:**

   ```batch
   cd /d F:\RD_PROJECTS\COMPONENTS\claude-context-local
   ```

### Auto-Fix Fails

**Symptoms:** Hook shows "Auto-fix encountered errors"

**Solutions:**

1. **Run fix manually to see errors:**

   ```batch
   scripts\git\fix_lint.bat
   ```

2. **Check for syntax errors:**
   Ruff can't fix files that don't parse correctly

3. **Manual fixes required:**
   Some issues need human intervention:
   - Complex logic errors
   - Undefined variables
   - Type mismatches

### Hook Takes Too Long

**Symptoms:** Commit waits 10-30 seconds

**Causes:**

- Large number of Python files staged
- Slow disk I/O
- Antivirus scanning `.bat` files

**Solutions:**

1. **Stage files incrementally:**

   ```batch
   git add specific_file.py
   git commit -m "message"
   ```

2. **Skip hook for WIP commits:**

   ```batch
   git commit --no-verify -m "wip: Quick save"
   ```

3. **Exclude `.venv` from antivirus:**
   Add `.venv/Scripts/` to antivirus exceptions

### "Invalid choice" Error

**Symptoms:** Hook shows "Invalid choice" when you type response

**Cause:** Typo in response

**Solution:** Type exactly:

- `yes` or `y` or `Y`
- `no` or `n` or `N`
- `skip` or `s` or `S`

### Python Files Not Detected

**Symptoms:** Hook says "No Python files to check" but you changed `.py` files

**Causes:**

1. Files not staged (still in working directory)
2. Only deleted Python files (hook skips deleted files)
3. Files in `_archive/` or `tests/test_data/` (excluded)

**Solutions:**

1. **Verify files are staged:**

   ```batch
   git status
   ```

2. **Stage Python files:**

   ```batch
   git add *.py
   ```

---

## Uninstalling

### Temporary Disable

```batch
REM Rename hook to disable
ren .git\hooks\pre-commit pre-commit.disabled

REM Re-enable later
ren .git\hooks\pre-commit.disabled pre-commit
```

### Permanent Removal

```batch
REM Delete the hook
del .git\hooks\pre-commit

REM Or delete all hooks
rmdir /s /q .git\hooks
mkdir .git\hooks
```

**Note:** You can reinstall anytime with `scripts\git\install_hooks.bat`

---

## Updating Hooks

When the hook template (`.githooks/pre-commit`) is updated:

1. **Pull latest changes:**

   ```batch
   git pull origin development
   ```

2. **Reinstall hook:**

   ```batch
   scripts\git\install_hooks.bat
   ```

3. **Verify new version:**

   ```batch
   type .git\hooks\pre-commit | head -5
   ```

---

## Summary

**Pre-commit hooks provide:**

- 🛡️ Privacy protection (local-only files)
- 📚 Documentation validation
- 🎨 Code quality enforcement
- 🔧 Auto-fix capabilities
- ⚡ Fast feedback (<5 seconds)
- ✅ CI failure prevention

**Consistency across:**

- Pre-commit hooks (this)
- `scripts/git/check_lint.bat`
- `scripts/git/fix_lint.bat`
- `scripts/git/commit_enhanced.bat`
- VSCode Ruff extension
- GitHub Actions CI

**All using the same rules from:** `pyproject.toml`
