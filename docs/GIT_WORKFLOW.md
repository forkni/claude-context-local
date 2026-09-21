# Git Workflow for claude-context-local

## Overview

This repository uses a **Local-First Privacy Model** where certain development files remain strictly on your local machine and are never committed to any git branch. This ensures your development context stays private while maintaining a clean, professional public repository.

**🤖 For Automated Claude Workflows**: See **[auto-git-workflow SKILL.md](../.claude/skills/auto-git-workflow/SKILL.md)** for step-by-step orchestration instructions with comprehensive logging.

## 🔒 Local-Only Files (NEVER Committed)

| File/Directory | Size | Purpose | Status |
| ---------------- | ------ | --------- | --------- |
| **CLAUDE.md** | ~50KB | Development context and instructions | 🔴 Local Only |
| **MEMORY.md** | ~5KB | Session memory and notes | 🔴 Local Only |
| **_archive/** | 7.3MB (764 files) | Historical TouchDesigner documentation | 🔴 Local Only |
| **benchmark_results/** | Variable | Generated test data and results | 🔴 Local Only |

**Total saved from repository: ~7.4MB + 764 files**

## 🏗️ Two-Tier File Structure

Since you're the sole developer, we use a simplified two-tier approach:

### 1. Local Machine (Working Directory)

- **Contains EVERYTHING** including private development files
- _archive/ provides complete historical context (764 TouchDesigner files)
- CLAUDE.md and MEMORY.md give full development context
- benchmark_results/ stores local test data

### 2. Git Branches (Both Development & Main)

- **Clean public releases** without development context
- No private files (automatically excluded by .gitignore)
- Professional presentation for users
- Both branches have identical content

## 🛡️ Protection Mechanisms

### 1. .gitignore Protection

```gitignore
# Local-only content (NEVER commit to ANY branch)
_archive/
benchmark_results/
CLAUDE.md
MEMORY.md
```

### 2. Pre-commit Hook

Automatically blocks commits containing local-only files:

- Located: `.git/hooks/pre-commit`
- Scans staging area for protected files
- Prevents accidental exposure

## 📋 Authorized Documentation on Main Branch

**CRITICAL**: Only these 8 documentation files are allowed on main branch:

1. **BENCHMARKS.md** - Benchmark methodology and results
2. **claude_code_config.md** - Claude Code configuration guide
3. **GIT_WORKFLOW.md** - This workflow documentation (you're reading it)
4. **HYBRID_SEARCH_CONFIGURATION_GUIDE.md** - Search system configuration
5. **INSTALLATION_GUIDE.md** - Complete installation process
6. **MCP_TOOLS_REFERENCE.md** - Modular MCP tools reference
7. **MODEL_MIGRATION_GUIDE.md** - Model switching guide
8. **PYTORCH_COMPATIBILITY.md** - PyTorch compatibility guide

**All other docs/ files** (VSCODE_SETUP.md, TESTING_GUIDE.md, PRE_COMMIT_HOOKS.md, etc.) are **development-only** and must remain on development branch only.

### Why This Matters

- **CI Enforcement**: GitHub Actions validates this policy on every push to main
- **Automated Checks**: Unauthorized docs will fail CI/CD automatically
- **Prevention**: Development-only docs are listed in `.gitattributes` with `merge=ours` strategy
- **Validation**: `.github/workflows/branch-protection.yml` and `.github/workflows/merge-development-to-main.yml` enforce the current checks

### Development-Only Documentation

These files exist only on the development branch:

- **docs/VSCODE_SETUP.md** - VSCode configuration and Ruff setup
- **docs/PRE_COMMIT_HOOKS.md** - Pre-commit hook documentation
- **docs/GPU_MEMORY_LEAK_FIX.md** - GPU memory optimization details
- **docs/PER_MODEL_INDICES_IMPLEMENTATION.md** - Per-model index technical details
- **docs/PER_MODEL_INDICES_PLAN.md** - Per-model index planning document
- **docs/Current_State.md** - Current development state tracking
- **docs/GIT_WORKFLOW_ENHANCEMENT_PLAN.md** - Workflow enhancement planning
- **docs/GIT_WORKFLOW_CRITICAL_REVIEW.md** - Critical workflow review

**Note**: Testing documentation moved to `tests/TESTING_GUIDE.md` (production-ready, available on all branches).

These are automatically excluded from main branch via `.gitattributes` merge strategy.

## 🚀 Current Workflow Entry Points

The current checkout does not contain the previously documented `scripts/git/`
workflow-wrapper directory. Use the tracked commands and automation below
instead of commands copied from older versions of this guide.

### Local validation

After installing the development dependencies, the local commands matching the
branch-protection checks are:

```bash
uv run ruff check --output-format=github .
uv run ruff format --check .
uv run pyrefly check
uv run pre-commit run --all-files --show-diff-on-failure
./scripts/lint/check_shell.sh
```

The shell helper scans the current `scripts/` tree. It is not a replacement
for the Ruff, Pyrefly, or pre-commit checks.

### Commits and pull requests

Use standard Git commands to create a commit, push the branch, and open a pull
request:

```bash
git add <files>
git commit -m "docs: Describe the change"
git push origin <branch>
gh pr create --title "docs: Describe the change" --body "..."
```

### Merge development into main

Run `.github/workflows/merge-development-to-main.yml` from the GitHub Actions
interface. The manually dispatched workflow supports `create_backup` and
`dry_run` inputs, verifies `.gitattributes`, merges `origin/development` into
`main`, checks that the development history is present, and pushes `main` when
not running as a dry run.

For local test execution, use `./scripts/test/run_tests.sh`. For the repository's
configured Markdown table of contents, use `./scripts/docs/update_toc.sh`.

## 🤖 Claude Code GitHub Integration

### Overview

This repository includes GitHub Actions integration for Claude Code, enabling interactive AI assistance through `@claude` mentions in issues and pull requests. This is **complementary** to the CI/CD automation workflows.

### Interactive AI Features

**GitHub Actions Workflow**: `.github/workflows/claude.yml`

Responds to `@claude` mentions in:

- Issue comments
- Pull request review comments
- Pull request reviews
- New issues (in title or body)

**Permissions Required**:

- Read: contents, pull requests, issues
- Write: id-token (for authentication)

**Setup Requirement**: Add `ANTHROPIC_API_KEY` to repository secrets

### Custom Commands

Located in `.claude/commands/` directory, these are reusable command templates:

#### 1. `/create-pr` - Automated PR Creation

**Purpose**: Create pull requests with clean, professional descriptions

**Features**:

- Creates feature branch from current changes
- Commits staged changes with conventional format
- Pushes to remote and creates PR via GitHub CLI
- **Never includes Claude Code attribution** in PR descriptions

**Usage**:

```bash
# Stage your changes first
git add <files>

# Run command (optional: specify branch suffix)
/create-pr feature-name
# or
/create-pr  # Uses timestamp as branch suffix
```

**Good PR Examples**:

- `feat: Add semantic search caching for 93% token reduction`
- `fix: Escape parentheses in sync_status.bat echo statements`
- `docs: Update installation guide with PyTorch 2.6.0 requirements`

#### 2. `/run-merge` - Guided Merge Workflow

Use the tracked `.github/workflows/merge-development-to-main.yml` workflow
from GitHub Actions for the development-to-main merge. It exposes full and dry
run behavior through `workflow_dispatch` inputs, creates an optional backup tag,
verifies the merge, and pushes `main` only for a non-dry run.

#### 3. `/validate-changes` - Pre-Commit Validation

**Purpose**: Comprehensive pre-commit checklist to catch issues early

**Checks Performed**:

1. Verifies changes are staged
2. Blocks local-only files (CLAUDE.md, MEMORY.md, _archive/, benchmark_results/)
3. Branch-specific validations (no tests/ on main)
4. File count warnings (>50 files = large changeset)
5. Commit message format validation (conventional commits)
6. AI attribution detection (blocks commits with Claude/Generated/Co-Authored references)
7. .gitattributes consistency check

**Usage**:

```bash
# After staging changes, before committing
/validate-changes
```

**Prevents Common Mistakes**:

- ❌ Committing CLAUDE.md or MEMORY.md (local-only)
- ❌ Using AI attribution in commit messages
- ❌ Non-conventional commit message format

**Quick Fixes**:

```bash
# Unstage local files
git reset HEAD CLAUDE.md MEMORY.md _archive/ benchmark_results/

# Conventional commit format examples
feat: Add hybrid search with BM25 + semantic fusion
fix: Escape parentheses in batch file echo statements
docs: Update installation guide with PyTorch requirements
chore: Add GitHub Actions workflows for CI/CD
test: Add integration tests for incremental indexing
```

### CI/CD Workflows vs Claude Code Integration

**They are COMPLEMENTARY, not mutually exclusive:**

#### CI/CD Workflows (Automated)

- **branch-protection.yml** - Validates every push (test files, linting, local-only file checks)
- **merge-development-to-main.yml** - Manual merge workflow with .gitattributes support
- **docs-validation.yml** - Documentation quality checks (markdown lint, link checking)

**Purpose**: Automatic validation and quality assurance

#### Claude Code Integration (Interactive)

- **claude.yml** - Responds to @claude mentions in issues/PRs
- **Custom commands** - Reusable workflow templates

**Purpose**: Interactive AI assistance for development tasks

### Using @claude in GitHub

**In Issues**:

```markdown
@claude can you review this error message and suggest a fix?

[error log here]
```

**In Pull Requests**:

```markdown
@claude please review these changes for potential issues
```

**In PR Comments**:

```markdown
@claude what's the best way to implement caching for this function?
```

### Configuration Files

#### .gitignore Rules

```gitignore
# Claude Code user settings (local-only)
.claude/*
# But allow shared custom commands
!.claude/commands/
```

**This ensures**:

- User-specific settings remain private (`.claude/*`)
- Shared custom commands are version controlled (`.claude/commands/`)

#### Required Secrets

Add to repository settings → Secrets and variables → Actions:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Integration Benefits

| Benefit | Description |
| --------- | ------------- |
| **Interactive Help** | @claude mentions provide context-aware assistance |
| **Workflow Automation** | Custom commands standardize common tasks |
| **Quality Enforcement** | Validation prevents common mistakes |
| **Clean Commits** | Automatic checks ensure professional commit messages |
| **Safe Merging** | Guided workflows with rollback support |

## 🔄 Automated Workflows

### Continuous validation

The current branch-protection workflow runs the repository's quality gates in
GitHub Actions:

```bash
uv run ruff check --output-format=github .
uv run ruff format --check .
uv run pyrefly check
uv run pre-commit run --all-files --show-diff-on-failure
```

These commands are also suitable for local validation after the development
dependencies are installed. The workflow reports the individual gate results
together rather than delegating them to a repository-local wrapper script.

### Merge automation

The manually dispatched `.github/workflows/merge-development-to-main.yml`
workflow updates `main` from `origin/development`. A dry run previews the
changes and commits; a non-dry run can create a backup tag, performs the merge,
verifies ancestry, and pushes `main`. Inspect the corresponding GitHub Actions
run for command output and the merge summary.

### Verification

```bash
git status
git log --oneline --graph -10
```

## 📋 Daily Workflow

### 1. Normal Development

```bash
# Work with full context (CLAUDE.md, MEMORY.md, _archive/)
# Edit code, run tests, develop features

# Validate changes before committing
/validate-changes

# When ready to commit:
git add <files>
git commit -m "feat: Add new search functionality"
```

### 2. Creating Pull Requests

```bash
# Stage your changes
git add <files>

# Use custom command for clean PR creation
/create-pr feature-name

# Or create manually with gh CLI
gh pr create --title "feat: ..." --body "..."
```

### 3. Public Release

```bash
# Use guided merge workflow
/run-merge full
# Or run `.github/workflows/merge-development-to-main.yml` from GitHub Actions

# Both branches now have identical public content
# Local files remain private
```

### 4. Fresh Clone Setup

```bash
# After cloning repository:
git clone <repo-url>
cd claude-context-local

# Note: CLAUDE.md, MEMORY.md, and _archive/ are not tracked in git
# These files remain on your portable drive
```

## 🔄 File Lifecycle

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Local Work    │    │   Git Tracking   │    │ Public Release  │
│                 │    │                  │    │                 │
│ • CLAUDE.md     │───▶│ • Core code      │───▶│ • Clean repo    │
│ • MEMORY.md     │    │ • Tests          │    │ • Professional  │
│ • _archive/     │    │ • Scripts        │    │ • No dev files  │
│ • Full context  │    │ • Documentation  │    │ • User-ready    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
     ↑ Private               ↑ Tracked              ↑ Public
```

## ⚡ Quick Commands Reference

### Local command reference

| Task | Command | Result |
| ------ | --------- | --------- |
| **Check code quality** | `uv run ruff check --output-format=github .` | Runs the Ruff lint gate used by CI |
| **Check formatting** | `uv run ruff format --check .` | Checks Ruff formatting without changing files |
| **Check types** | `uv run pyrefly check` | Runs the repository type check |
| **Run pre-commit** | `uv run pre-commit run --all-files --show-diff-on-failure` | Runs configured repository hooks |
| **Check shell scripts** | `./scripts/lint/check_shell.sh` | Runs ShellCheck over `scripts/` |
| **Run tests** | `./scripts/test/run_tests.sh` | Runs pytest from `.venv` |
| **Merge to main** | `.github/workflows/merge-development-to-main.yml` | Manual GitHub Actions merge workflow |
| **Check status** | `git status` | Shows staged changes |
| **View branches** | `git branch -a` | Lists all branches |

## 🚨 Critical Rules

### ✅ DO

- Run the branch-protection checks before committing
- Keep CLAUDE.md and MEMORY.md updated locally
- Use the tracked GitHub Actions merge workflow for releases
- Backup local files before major changes
- Review `git diff` before committing

### ❌ NEVER

- Manually add local files to git: `git add CLAUDE.md` ❌
- Skip lint checks when committing ❌
- Push local files to any branch ❌
- Force merge without validation ❌

## 🔧 Troubleshooting

### "Local files in staging area" Error

```bash
# Remove local files from staging:
git reset HEAD CLAUDE.md MEMORY.md
git reset HEAD _archive/ benchmark_results/
```

### Missing Local Files

```bash
# If working from a fresh clone, recreate minimal versions:
echo "# Development context" > CLAUDE.md
echo "# Session memory" > MEMORY.md
```

Note: If working from a portable drive, local files remain with the repository.

### Pre-commit Hook Not Working

```bash
# Ensure hook is executable:
chmod +x .git/hooks/pre-commit

# Test hook manually:
.git/hooks/pre-commit
```

## 📊 Benefits

| Benefit | Impact |
| --------- | --------- |
| **Privacy** | Development context never exposed |
| **Clean repo** | Professional public presentation |
| **Space efficiency** | 7.4MB + 764 files excluded |
| **Fail-safe** | Multiple protection layers |
| **Easy workflow** | Automated scripts reduce errors |
| **Solo development** | Optimized for single developer |

## 🔄 Branch Strategy

```
Local Machine:
├── CLAUDE.md (private context)
├── MEMORY.md (private notes)
├── _archive/ (764 historical files)
└── Public code files

           ↓ git add / git commit / git push

Development Branch:
├── Core application code
├── Test suites (all tests)
├── Documentation (all public docs)
├── Scripts and tools
├── pytest.ini
└── Configuration files

           ↓ merge-development-to-main.yml (GitHub Actions)

Main Branch:
├── Core application code
├── Test suites (all tests)
├── Documentation (public docs only)
├── Scripts and tools
├── pytest.ini
└── User-ready repository (with tests for verification)
```

**Note**: Tests are now included in both branches following standard Python project conventions. Users can run `pytest` to verify their installation works correctly.

---

## 📝 Implementation Summary

✅ **Complete Setup:**

- .gitignore excludes all local-only files
- Pre-commit hook prevents accidental commits
- Backup system preserves local files
- Automation scripts ensure correct workflow
- Documentation provides clear guidance

✅ **Protection Layers:**

1. .gitignore (automatic exclusion)
2. Pre-commit hook (staging area check)
3. Backup system (recovery mechanism)
4. Automated scripts (reduce human error)

✅ **Benefits Achieved:**

- **100% privacy** for development context
- **Professional repository** presentation
- **Minimal overhead** for daily workflow
- **Fail-safe protection** against exposure
- **Easy maintenance** for solo development

## 📝 Commit Message Guidelines

### IMPORTANT: Clean Commit Messages

When writing commit messages, they should be clean and simple. Never add any reference to being created by Claude Code, or add yourself as a co-author, as this can lead to confusion.

### Good Examples

- `fix: Add test_evaluation folder for benchmark support`
- `feat: Implement hybrid search functionality`
- `chore: Update dependencies`

### Bad Examples (AVOID)

- Messages with "Generated with Claude Code"
- Messages with "Co-Authored-By: Claude"
- Any AI-related attribution

## 📋 CHANGELOG & Versioning

### CHANGELOG.md Maintenance

- **Location**: Root directory (`CHANGELOG.md`)
- **Format**: Follows [Keep a Changelog](https://keepachangelog.com/) standard
- **Update timing**: Update with each significant change or release
- **Structure**: Organized by version with Added/Changed/Fixed/Removed sections

### Version Bumping Strategy

This project follows [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **PATCH (0.1.x)**: Bug fixes, documentation corrections, small improvements
  - Example: 0.1.0 → 0.1.1 for fixing documentation typos

- **MINOR (0.x.0)**: New features, significant enhancements, backward-compatible changes
  - Example: 0.1.0 → 0.2.0 for adding auto-tuning feature

- **MAJOR (x.0.0)**: Breaking changes, major architecture updates
  - Example: 0.9.0 → 1.0.0 for first stable release

### Release Workflow

1. Update `CHANGELOG.md` with new version section
2. Bump version in `pyproject.toml`
3. Commit changes: `docs: Prepare v0.x.0 release`
4. Push to development branch
5. Sync to main branch
6. Create annotated git tag: `git tag -a v0.x.0 -m "Release notes"`
7. Push tag: `git push origin v0.x.0`
8. Create GitHub release (optional, via web interface)

### Current Version

Check `pyproject.toml` for the current version number.

## 📊 Workflow Output

Local validation commands print their results to the terminal. CI output,
including the branch-protection gates, is available in the corresponding
GitHub Actions run. The merge workflow also prints its merge summary and any
backup tag it creates.

Use `git status` and `git log --oneline --graph -10` to inspect local repository
state after committing or updating a branch.

## 📦 Test Data Management

### test_evaluation/ Folder

- **Status**: ✅ Tracked in Git (NOT gitignored)
- **Purpose**: Required sample project for benchmarks
- **Contents**: Synthetic test project for evaluation
- **Critical**: Must be present for benchmarks to work

### Files to Keep vs Ignore

- **Keep**: test_evaluation/ (required for benchmarks)
- **Ignore**: benchmark_results/ (generated output)
- **Ignore**: custom_evaluation_results/ (temporary results)

## ⚠️ Common Errors and Solutions

### Error: A workflow command cannot be found

**Symptom**: Running a script with a Windows-style backslash path fails with "command not found"

**Example Error**:

```bash
$ ./scripts/lint/check_shell.sh
No shell script is available at the requested path
```

**Root Cause**:

- Git Bash (MINGW64) treats `\` as an escape character, not a path separator
- The current checkout has no `scripts/git/` wrapper directory

**Solution**: Use forward-slash paths

```bash
uv run ruff check --output-format=github .
uv run ruff format --check .
uv run pyrefly check
uv run pre-commit run --all-files --show-diff-on-failure
./scripts/lint/check_shell.sh

# All scripts:
# ✅ Execute natively in Git Bash
# ✅ Use forward-slash paths (compatible with Windows executables)
# ✅ Respect the repository's tracked configuration
# ✅ Proper exit codes for automation
```

**Configuration Notes**:

The .sh scripts rely on pyproject.toml for exclusions (no manual --exclude flags):

```toml
[tool.ruff]
exclude = [".venv", "_archive", "build", "dist", "__pycache__", "tests/test_data"]

[tool.ruff.format]
# Ruff format replaces black

[tool.ruff.lint.isort]
# Ruff's built-in isort replaces standalone isort
```

Use forward-slash paths for the tracked shell helpers on Git Bash, Linux, and
macOS. The helper scripts resolve their project root from their own location.

---

### Error: Invalid pyproject.toml Configuration

**Symptom**: Ruff fails to parse pyproject.toml with error about unknown field

**Example Error**:

```
unknown field `unsafe-fixes`, expected one of [allowed fields list]
```

**Root Cause**: Invalid configuration field added to pyproject.toml (e.g., `unsafe-fixes = true`)

**Solution**:

1. Remove the invalid field from pyproject.toml
2. Use `--unsafe-fixes` as CLI flag only: `ruff check . --fix --unsafe-fixes`
3. Or enable in VSCode settings: `"ruff.codeAction.fixViolation.enable": true`

**Prevention**: Validate config fields against [Ruff documentation](https://docs.astral.sh/ruff/configuration/) before adding

---

### Error: CI/CD Failure - Unauthorized Docs

**Symptom**: GitHub Actions fails with unauthorized documentation message

**Example Error**:

```
❌ ERROR: Unauthorized documentation files found on main branch:
docs/VSCODE_SETUP.md

Only these 8 docs are allowed in main branch: [list]
```

**Root Cause**: Development-only doc file merged to main branch (violates CI policy)

**Solution**:

1. Remove unauthorized doc from main:

   ```bash
   git checkout main
   git rm docs/VSCODE_SETUP.md
   git commit -m "fix: Remove unauthorized doc from main"
   git push origin main
   ```

2. Add to .gitattributes if it's development-only:

   ```gitattributes
   docs/VSCODE_SETUP.md merge=ours
   ```

**Prevention**:

- `.github/workflows/branch-protection.yml` runs the current CI checks
- `.github/workflows/merge-development-to-main.yml` verifies the merge before pushing `main`

---

### Expected: Modify/Delete Conflicts for Test Files

**Symptom**: Test files show modify/delete conflicts when merging development → main

```
CONFLICT (modify/delete): tests/integration/test_example.py deleted in HEAD and modified in development
CONFLICT (modify/delete): tests/unit/test_example.py deleted in HEAD and modified in development
```

**Status**: ✅ **THIS IS NORMAL AND EXPECTED** - Not an error!

**Why**: Test files exist on development but are intentionally excluded from main branch. Git requires manual decision when file is modified on one branch but deleted on the other.

**Quick Resolution**:

```bash
# Remove test files from merge (standard procedure)
git rm tests/integration/*.py tests/unit/*.py

# Complete merge
git commit --no-edit
```

**Better Approach**: Run `.github/workflows/merge-development-to-main.yml`
from GitHub Actions. It aborts when the merge command fails instead of leaving
an unresolved local merge in progress.

**Full explanation**: See [Understanding Modify/Delete Conflicts](#expected-conflicts-manual-merge)

---

### Error: Merge Conflicts Not Auto-Resolved

**Important**: First determine if you're seeing **expected conflicts** or a **script error**.

#### Expected Conflicts (Manual Merge)

If you ran a **manual merge** (e.g., `git merge development --no-ff`), modify/delete conflicts for test files are **EXPECTED**:

```
CONFLICT (modify/delete): tests/integration/test_example.py deleted in HEAD and modified in development
```

**This is NORMAL** - See [Understanding Modify/Delete Conflicts](#expected-conflicts-manual-merge) for full explanation.

**Standard resolution** (not an error):

```bash
# Remove test files from main (expected procedure)
git rm tests/integration/*.py tests/unit/*.py

# Complete merge
git commit --no-edit
```

**Prevention**: Run the tracked merge workflow with `dry_run` first when a
preview is useful, then use a non-dry run after reviewing the proposed changes.

---

### Error: Missing --unsafe-fixes Flag

**Symptom**:

- Lint errors remain after running Ruff
- Ruff reports "hidden fixes can be enabled with --unsafe-fixes"

**Example**:

```
144 hidden fixes can be enabled with the `--unsafe-fixes` option
```

**Root Cause**: Ruff's hidden fixes require an explicit `--unsafe-fixes` flag

**Solution**: Use the Ruff CLI flag explicitly when those fixes are intended:

```bash
uv run ruff check . --fix --unsafe-fixes
```

**Prevention**: Review the diff after any auto-fix and run the branch-protection
checks before committing.

---

### Error: Merge Strategy Not Working

**Symptom**: Files that should be excluded from main still appear in merge conflicts

**Root Cause**: File not listed in .gitattributes or git config missing

**Solution**:

1. Check .gitattributes contains the file:

   ```gitattributes
   docs/VSCODE_SETUP.md merge=ours
   tests/** merge=ours
   ```

2. Verify git config:

   ```bash
   git config --get merge.ours.driver
   # Should return: true
   ```

3. If not configured:

   ```bash
   git config --global merge.ours.driver true
   ```

**Prevention**: The tracked merge workflow configures and verifies the `ours`
merge driver before merging.

---

### Error: Committed to Wrong Branch

**Symptom**: Accidentally committed changes to main instead of development branch

**Example**:

```bash
$ git branch --show-current
main
# Expected: development
```

**Root Cause**: User didn't verify the current branch before committing

**Impact**:

- Changes committed to wrong branch
- Need to undo commit and re-commit to correct branch

**Solution**:

1. If commit not yet pushed, undo and recommit:

   ```bash
   # Undo commit on wrong branch (keep changes)
   git reset --soft HEAD~1

   # Switch to correct branch
   git checkout development

   # Re-commit with same message
   git commit -m "Your commit message"
   ```

2. If already pushed to remote:

   ```bash
   # Revert the commit on wrong branch
   git checkout main
   git revert HEAD
   git push origin main

   # Cherry-pick to correct branch
   git checkout development
   git cherry-pick <commit-hash>
   git push origin development
   ```

**Prevention**: Check `git branch --show-current` before staging and committing.

---

### Error: False "Merge Failed" Message

**Symptom**: Script reports "Failed to complete merge commit" but merge actually succeeded

**Example**:

```
✓ Auto-resolved modify/delete conflicts
[6/7] Validating documentation files against CI policy...
✓ Documentation validation passed
[7/7] Completing merge commit...
✗ Failed to complete merge commit    ← FALSE ERROR

# But checking git log shows:
$ git log -1
commit 12649c2 (HEAD -> main)    ← Merge actually worked!
Merge development into main
```

**Root Cause**: Script logic issue

- Merge command at [4/7] creates commit when auto-resolution succeeds
- Script tries to commit again at [7/7] using `git commit --no-edit`
- Second commit fails with "nothing to commit" → false error message
- Merge was already complete, error message is misleading

**Impact**: Confusing output but no actual failure

**Solution**: Script has been fixed with merge completion detection:

```bash
# After auto-resolution, check if merge is already complete
if ! git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
    echo "✓ Merge commit automatically completed during auto-resolution"
fi
```

**Prevention**:

- Script now detects when merge commit already exists
- Skips redundant commit attempt
- Prevents false error messages
- Goes directly to success message when merge complete

---

### 📅 Historical Note: Windows Batch Era (2025-10-04)

Earlier revisions of this guide described local workflow-wrapper scripts and a
Windows batch implementation. Those wrappers are not part of the current
checkout; current validation and merge behavior is defined by the tracked
GitHub Actions workflows and helper paths documented above. This note is
retained only as historical context and is not an instruction to run those
older commands.

---

### Error: Ruff Linting Errors (B007, B904)

**Symptom**: GitHub Actions CI fails with Ruff linting errors

**Common Errors**:

#### B007: Unused Loop Variables

**Example Error**:

```
tests/integration/test_full_flow.py:162:9: B007 Loop control variable `chunk_id` not used within loop body
tests/integration/test_full_flow.py:169:9: B007 Loop control variable `similarity` not used within loop body
```

**Root Cause**: Loop variables declared but not used in loop body

**Problematic Code**:

```python
# Before (2 B007 errors):
for chunk_id, similarity, metadata in function_results:
    assert metadata["chunk_type"] == "function"

for chunk_id, similarity, metadata in class_results:
    assert metadata["chunk_type"] == "class"
```

**Solution**: Rename unused variables with underscore prefix

```python
# After (fixed):
for _chunk_id, _similarity, metadata in function_results:
    assert metadata["chunk_type"] == "function"

for _chunk_id, _similarity, metadata in class_results:
    assert metadata["chunk_type"] == "class"
```

**Convention**: Python convention uses `_` or `_variablename` for intentionally unused variables

---

#### B904: Missing Exception Chaining

**Example Error**:

```
tests/integration/test_hf_access.py:41:9: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None`
tests/unit/test_bm25_population.py:140:9: B904 Within an `except` clause, raise exceptions with `raise ... from err`
```

**Root Cause**: Re-raising exceptions without proper chaining (PEP 3134)

**Problematic Code**:

```python
# Before (9 B904 errors across 6 files):
try:
    test_function()
except Exception as e:
    print(f"Error: {e}")
    raise AssertionError(f"Test failed: {e}")  # Missing 'from e'
```

**Solution**: Add exception chaining with `from e`

```python
# After (fixed):
try:
    test_function()
except Exception as e:
    print(f"Error: {e}")
    raise AssertionError(f"Test failed: {e}") from e  # Proper chaining
```

**Why it matters**:

- Preserves original exception traceback
- Helps with debugging
- Shows exception causality chain
- Python best practice (PEP 3134)

**Alternative**: Use `from None` to explicitly suppress chaining:

```python
raise AssertionError(f"Test failed: {e}") from None  # Explicit suppression
```

---

#### Comprehensive Fix (2025-10-04)

**Files Modified** (commit 46dac62):

1. **tests/integration/test_full_flow.py**
   - Fixed 2 B007 errors (lines 162, 169)
   - Renamed unused loop variables to `_chunk_id`, `_similarity`

2. **tests/integration/test_glsl_chunker_only.py**
   - Fixed 1 B904 error (line 103)
   - Added exception chaining: `from e`

3. **tests/integration/test_glsl_complete.py**
   - Fixed 1 B904 error (line 109)
   - Added exception chaining: `from e`

4. **tests/integration/test_glsl_without_embedder.py**
   - Fixed 1 B904 error (line 139)
   - Added exception chaining: `from e`

5. **tests/integration/test_hf_access.py**
   - Fixed 5 B904 errors (lines 41, 80, 120, 173, 271)
   - Added exception chaining: `from e`

6. **tests/unit/test_bm25_population.py**
   - Fixed 1 B904 error (line 140)
   - Added exception chaining: `from e`

7. **search/bm25_index.py** (production code)
   - Fixed 1 B904 error (line 240)
   - Added exception chaining: `from bm25_error`

**Total**: 13 errors fixed (4 B007 + 9 B904)

**Verification**:

```bash
$ .venv\Scripts\ruff.exe check .
All checks passed!
```

**Prevention**:

- ✅ Use underscore prefix for unused variables
- ✅ Always add `from e` when re-raising exceptions
- ✅ Run the branch-protection Ruff and pre-commit checks before committing
- ✅ Use `from None` only when suppression is intentional
- ✅ Review Ruff suggestions during development

**Status**: ✅ RESOLVED (commit 46dac62, 2025-10-04)

---

## 🔍 Lint Workflow Best Practices

### When to run validation

Run the same commands used by branch protection before committing changes:

- `uv run ruff check --output-format=github .`
- `uv run ruff format --check .`
- `uv run pyrefly check`
- `uv run pre-commit run --all-files --show-diff-on-failure`
- `./scripts/lint/check_shell.sh`

**Recommended workflow**:

```bash
# 1. Make your changes
# 2. Review and, if needed, apply an explicit Ruff fix
uv run ruff check . --fix

# 3. Review what was fixed
git diff

# 4. Final validation
uv run ruff check --output-format=github .
uv run ruff format --check .
uv run pyrefly check
uv run pre-commit run --all-files --show-diff-on-failure

# 5. Commit if all checks pass
git add <files>
git commit -m "fix: Describe the change"
```

### Understanding --unsafe-fixes

**What it does**:

- Enables comprehensive automatic code corrections
- Fixes 90%+ of lint errors automatically
- Includes transformations that change code semantics

**How to use**:

- ✅ **CLI flag**: `ruff check . --fix --unsafe-fixes`
- ✅ **VSCode setting**: `"ruff.codeAction.fixViolation.enable": true`
- ❌ **NOT a pyproject.toml field** - will cause parse errors

**Examples of unsafe fixes**:

- Removing unused imports
- Converting generators to comprehensions
- Removing unused variables
- Simplifying boolean expressions

**Safety**:

- Always review changes with `git diff`
- Run tests after auto-fixes
- Unsafe != dangerous (just means "changes semantics")

### Real-World Fix Examples (from 2025-10-04)

This section shows actual fixes applied during v4 workflow improvements.

#### B007: Unused Loop Variables - test_full_flow.py

**Before** (2 errors):

```python
for chunk_id, similarity, metadata in function_results:
    assert metadata["chunk_type"] == "function"
    # chunk_id and similarity not used!

for chunk_id, similarity, metadata in class_results:
    assert metadata["chunk_type"] == "class"
    # chunk_id and similarity not used!
```

**After** (fixed):

```python
for _chunk_id, _similarity, metadata in function_results:
    assert metadata["chunk_type"] == "function"
    # Underscore prefix signals intentional non-use

for _chunk_id, _similarity, metadata in class_results:
    assert metadata["chunk_type"] == "class"
    # Underscore prefix signals intentional non-use
```

**Lines changed**: 162, 169
**Commit**: 46dac62

#### B904: Exception Chaining - Multiple Files

**test_hf_access.py** (5 locations):

```python
# Before (lines 41, 80, 120, 173, 271):
except Exception as e:
    print(f"[ERROR] Authentication failed: {e}")
    raise AssertionError(f"Authentication failed: {e}")  # Missing 'from e'

# After:
except Exception as e:
    print(f"[ERROR] Authentication failed: {e}")
    raise AssertionError(f"Authentication failed: {e}") from e  # Added chaining
```

**test_bm25_population.py** (line 140):

```python
# Before:
except Exception as e:
    print(f"[TEST] Test failed with error: {e}")
    raise AssertionError(f"Test failed with error: {e}")

# After:
except Exception as e:
    print(f"[TEST] Test failed with error: {e}")
    raise AssertionError(f"Test failed with error: {e}") from e
```

**search/bm25_index.py** (production code, line 240):

```python
# Before:
except Exception as bm25_error:
    raise ValueError(f"BM25 index creation failed: {bm25_error}")

# After:
except Exception as bm25_error:
    raise ValueError(f"BM25 index creation failed: {bm25_error}") from bm25_error
```

**Total files modified**: 7 (6 test files + 1 production file)
**Total errors fixed**: 13 (4 B007 + 9 B904)
**Commit**: 46dac62

### Markdown Linting

**Installation** (one-time setup):

```bash
# Install markdownlint-cli2 globally
npm install -g markdownlint-cli2

# Verify installation
markdownlint-cli2 --version
```

**Local validation** (before commit):

```bash
# Check markdown quality
uv run pre-commit run markdownlint --all-files --show-diff-on-failure
```

**Common markdown fixes**:

- Line length violations (MD013) - break long lines
- Missing blank lines around headings (MD022)
- Missing blank lines around lists (MD032)
- Missing blank lines around code fences (MD031)

**Configuration**: `.markdownlint-cli2.yaml` in project root

**Excluded directories**: `.venv`, `_archive`, `benchmark_results`, `logs`, `node_modules`

**Match CI/CD**: Local markdown validation matches GitHub Actions `docs-validation.yml` rules

### Shell Script Linting (ShellCheck)

**Installation** (project-local):

- ShellCheck v0.10.0 bundled in `tools/bin/shellcheck.exe`
- Auto-detected by `scripts/lint/check_shell.sh`
- Cross-platform: Windows (Git Bash), Linux, macOS

**Local validation** (before commit):

```bash
# Check all shell scripts
./scripts/lint/check_shell.sh

# Output shows pass/fail for each .sh file
# Validates tracked shell scripts under scripts/
```

**What ShellCheck detects**:

- Unquoted variables (SC2086) - prevents word-splitting bugs
- Unsafe `cd` commands (SC2164) - missing `|| exit` error handling
- Command substitution style (SC2006) - enforces `$(...)` over backticks
- POSIX compliance issues
- Unused variables (SC2034)
- Syntax errors

**Common fixes**:

```bash
# Bad: Unquoted variable
cd $PROJECT_ROOT

# Good: Quoted variable
cd "$PROJECT_ROOT" || exit

# Bad: Backticks
result=`command`

# Good: Modern syntax
result=$(command)
```

**Configuration**: Excludes SC2154 (sourced variables from `_common.sh`)

**Reference**: See `BASH_STYLE_GUIDE.md` Section 5.4 for complete ShellCheck error codes and fixes

---

### Expected Warnings (Updated 2025-10-04)

**NOTE**: As of 2025-10-04, B007 and B904 warnings have been comprehensively resolved across the codebase.

**Currently acceptable warnings**:

- **E501 (line too long)** - Only if breaking would harm readability
- **W293 (blank line with whitespace)** - Auto-fixed by ruff format
- **Formatting warnings** - When using specialized formatting (docstrings, ASCII art, etc.)

**Previously common but now resolved**:

- ~~B904 (exception chaining)~~ ✅ All fixed in commit 46dac62
- ~~B007 (unused loop variables)~~ ✅ All fixed in commit 46dac62

**When new warnings appear**:

1. Run `uv run ruff check . --fix` first when an automatic fix is appropriate
2. Review changes with `git diff`
3. Manually fix remaining issues
4. Verify with the branch-protection commands in [Current Workflow Entry Points](#-current-workflow-entry-points)

### Error Code Categories

| Category | Examples | Auto-fixable | Severity |
| ---------- | ---------- | -------------- | ---------- |
| **Imports** | F401, F811, I001 | ✅ Yes (ruff check) | Low |
| **Formatting** | W293, E501 | ✅ Yes (ruff format) | Low |
| **Code Style** | C401, C414, B007 | ✅ Yes (ruff --unsafe-fixes) | Low |
| **Logic Errors** | F821, F841 | ⚠️ Partial | High |
| **Exception Handling** | B904 | ❌ Manual recommended | Medium |
| **Security** | S608, S307 | ❌ Manual required | Critical |

### Lint Workflow Troubleshooting

**Problem**: "Ruff not found"

Solution: Activate the virtual environment first, or call the venv's ruff directly

```bash
source .venv/Scripts/activate
# or, without activating:
.venv/Scripts/ruff.exe --version
```

**Problem**: "Ruff would reformat X files"

Solution: Let ruff format them

```bash
.venv/Scripts/ruff.exe format .
```

**Problem**: "Ruff would fix X import order issues"

Solution: Let ruff fix them

```bash
.venv/Scripts/ruff.exe check --fix .
```

**Problem**: Lint passes locally but fails in CI

Possible causes:

1. Different Python versions (CI uses 3.11)
2. Different tool versions (CI uses latest)
3. Files not committed (check git status)

Solution: Check `.github/workflows/branch-protection.yml` for CI config

This workflow ensures your development context remains completely private while maintaining a clean, professional public repository suitable for users and collaborators.
