# Git Hooks

This directory contains Git hook templates that can be installed to `.git/hooks/`.

## Available Hooks

### pre-commit

Runs before creating a commit. Performs three types of checks:

1. **File Privacy Validation**
   - Prevents committing local-only files: `CLAUDE.md`, `MEMORY.md`, `_archive/`, `benchmark_results/`
   - Allows deletions (removing from tracking)
   - Blocks additions and modifications

2. **Documentation Validation**
   - Ensures only authorized documentation files are committed
   - Blocks unauthorized files in `docs/` directory
   - Maintains public/private doc separation

3. **Code Quality Checks** (Python files only)
   - Runs `scripts/git/check_lint.bat` on staged Python files
   - If errors found, prompts user:
     - **yes**: Auto-fixes with `fix_lint.bat`, restages files, continues commit
     - **no**: Aborts commit, shows fix instructions
     - **skip**: Allows commit with warning (not recommended)

## Installation

### Automatic (Recommended)

```batch
scripts\git\install_hooks.bat
```

This copies all hooks from `.githooks/` to `.git/hooks/` and makes them executable.

### Manual

Copy the hooks manually:

```batch
copy .githooks\pre-commit .git\hooks\pre-commit
```

## How It Works

When you run `git commit`:

1. Git automatically executes `.git/hooks/pre-commit` (if it exists)
2. The hook runs validation checks
3. If checks pass, commit proceeds
4. If checks fail, commit is aborted (or proceeds based on user choice)

## Bypassing Hooks

To skip hook execution (not recommended):

```batch
git commit --no-verify -m "message"
```

Use this sparingly - hooks exist to prevent issues in CI/CD.

## Customization

To modify hooks:

1. Edit the template in `.githooks/pre-commit`
2. Run `scripts\git\install_hooks.bat` to update your local copy
3. Commit the template so team members get the update

## Uninstalling

To remove a hook:

```batch
del .git\hooks\pre-commit
```

Or to remove all hooks:

```batch
rmdir /s /q .git\hooks
mkdir .git\hooks
```

## Why Hooks Are Not Tracked

Git hooks in `.git/hooks/` are **not tracked by Git** because:

- They're local to each developer's repository
- They contain executable code that could be malicious if auto-installed
- Different environments may need different hooks

That's why we provide templates in `.githooks/` that users must explicitly install.

## Team Consistency

To ensure all team members use the same hooks:

1. Update `.githooks/pre-commit` template
2. Commit to repository
3. Notify team to run `scripts\git\install_hooks.bat`

Alternatively, add hook installation to setup documentation or post-clone scripts.
