# Git Workflow for claude-context-local

## Overview

This repository uses a **Local-First Privacy Model** where certain development files remain strictly on your local machine and are never committed to any git branch. This ensures your development context stays private while maintaining a clean, professional public repository.

## 🔒 Local-Only Files (NEVER Committed)

| File/Directory | Size | Purpose | Status |
|----------------|------|---------|---------|
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
- **Validation**: Both `validate_branches.bat` and `merge_with_validation.bat` check this policy

### Development-Only Documentation

These files exist only on the development branch:

- **docs/VSCODE_SETUP.md** - VSCode configuration and Ruff setup
- **docs/TESTING_GUIDE.md** - Test suite documentation
- **docs/PRE_COMMIT_HOOKS.md** - Pre-commit hook documentation
- **docs/GPU_MEMORY_LEAK_FIX.md** - GPU memory optimization details
- **docs/PER_MODEL_INDICES_IMPLEMENTATION.md** - Per-model index technical details
- **docs/PER_MODEL_INDICES_PLAN.md** - Per-model index planning document
- **docs/Current_State.md** - Current development state tracking
- **docs/GIT_WORKFLOW_ENHANCEMENT_PLAN.md** - Workflow enhancement planning
- **docs/GIT_WORKFLOW_CRITICAL_REVIEW.md** - Critical workflow review

These are automatically excluded from main branch via `.gitattributes` merge strategy.

## 🚀 Workflow Scripts

All workflow scripts are located in `scripts/git/` directory.

### Core Workflow Scripts (6)

#### commit_enhanced.bat - Enhanced Commit Workflow

```batch
commit_enhanced.bat "Your commit message"
```

**Features:**
- Automatically excludes local-only files
- Code quality checks (lint validation)
- Branch-specific validations (no tests/ on main)
- Conventional commit format checking
- Interactive staging prompts
- Shows preview before committing

#### check_lint.bat - Code Quality Validation

```batch
scripts\git\check_lint.bat
```

**Checks:**
- Ruff linting (Python code style)
- Black formatting (code consistency)
- isort import sorting

#### fix_lint.bat - Auto-fix Linting Issues

```batch
scripts\git\fix_lint.bat
```

**Fixes:**
- Runs isort → black → ruff --fix
- Verifies fixes with check_lint.bat

#### merge_with_validation.bat - Safe Merge Workflow

```batch
scripts\git\merge_with_validation.bat
```

**Features:**
- Pre-merge validation (via validate_branches.bat)
- Creates backup tags before merge
- Automatic conflict resolution for modify/delete conflicts
- Handles development-only file exclusion
- Returns to original branch on error

#### validate_branches.bat - Pre-merge Validation

```batch
scripts\git\validate_branches.bat
```

**Checks:**
- Both branches exist
- No uncommitted changes
- .gitattributes exists
- merge.ours driver configured
- Branches in sync with remote

#### install_hooks.bat - Hook Installation

```batch
scripts\git\install_hooks.bat
```

**Installs:**
- Pre-commit hook from `.githooks/pre-commit`
- Linting validation
- Privacy protection checks

### Advanced/Safety Scripts (3)

#### rollback_merge.bat - Emergency Merge Rollback

```batch
scripts\git\rollback_merge.bat
```

**Options:**
- Rollback to latest backup tag
- Rollback to HEAD~1
- Rollback to specific commit hash
- Interactive confirmation required

#### cherry_pick_commits.bat - Hotfix Workflow

```batch
scripts\git\cherry_pick_commits.bat
```

**Features:**
- Cherry-pick specific commits from development → main
- Validates development-only file exclusions
- Creates backup tags
- Interactive commit selection

#### merge_docs.bat - Documentation-Only Merge

```batch
scripts\git\merge_docs.bat
```

**Features:**
- Merges ONLY docs/ directory changes
- Excludes development-only docs
- Creates backup tags
- Useful for documentation updates

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

**Purpose**: Safe merge workflow with validation and backup support

**Merge Types**:

- `full` - Full merge from development to main (default)
- `docs` - Documentation-only merge

**Usage**:

```bash
# Full merge workflow
/run-merge full
# Runs: scripts\git\merge_with_validation.bat

# Documentation-only merge
/run-merge docs
# Runs: scripts\git\merge_docs.bat
```

**Safety Features**:

- Pre-merge validation via `validate_branches.bat`
- Automatic backup tags created
- Conflict resolution handling
- Post-merge verification
- Rollback script available (`rollback_merge.bat`)

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
- ❌ Adding tests/ to main branch (development-only)
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
|---------|-------------|
| **Interactive Help** | @claude mentions provide context-aware assistance |
| **Workflow Automation** | Custom commands standardize common tasks |
| **Quality Enforcement** | Validation prevents common mistakes |
| **Clean Commits** | Automatic checks ensure professional commit messages |
| **Safe Merging** | Guided workflows with rollback support |

## 📋 Daily Workflow

### 1. Normal Development

```batch
# Work with full context (CLAUDE.md, MEMORY.md, _archive/)
# Edit code, run tests, develop features

# Validate changes before committing
/validate-changes

# When ready to commit:
scripts\git\commit_enhanced.bat "feat: Add new search functionality"
```

### 2. Creating Pull Requests

```batch
# Stage your changes
git add <files>

# Use custom command for clean PR creation
/create-pr feature-name

# Or create manually with gh CLI
gh pr create --title "feat: ..." --body "..."
```

### 3. Public Release

```batch
# Use guided merge workflow
/run-merge full
# Or run directly:
scripts\git\merge_with_validation.bat

# Both branches now have identical public content
# Local files remain private
```

### 4. Fresh Clone Setup

```batch
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

| Task | Command | Result |
|------|---------|---------|
| **Safe commit** | `scripts\git\commit_enhanced.bat "message"` | Commits with lint checks and validations |
| **Check code quality** | `scripts\git\check_lint.bat` | Validates code with ruff/black/isort |
| **Fix linting** | `scripts\git\fix_lint.bat` | Auto-fixes linting issues |
| **Merge to main** | `scripts\git\merge_with_validation.bat` | Safe merge: development → main |
| **Docs-only merge** | `scripts\git\merge_docs.bat` | Merge only documentation changes |
| **Check status** | `git status` | Shows staged changes |
| **View branches** | `git branch -a` | Lists all branches |
| **Emergency rollback** | `scripts\git\rollback_merge.bat` | Rollback last merge |

## 🚨 Critical Rules

### ✅ DO

- Use `commit_enhanced.bat` for all commits (includes lint checks)
- Keep CLAUDE.md and MEMORY.md updated locally
- Use `merge_with_validation.bat` for releases
- Backup local files before major changes
- Run `check_lint.bat` before committing

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
|---------|---------|
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

           ↓ commit_enhanced.bat (with lint checks)

Development Branch:
├── Core application code
├── Test suites (all tests)
├── Documentation (public + TESTING_GUIDE.md)
├── Scripts and tools
├── pytest.ini
└── Configuration files

           ↓ merge_with_validation.bat (removes tests/, pytest.ini, TESTING_GUIDE.md)

Main Branch:
├── Core application code (no tests)
├── Documentation (public only)
├── Scripts and tools
├── Clean public release
└── User-ready repository
```

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

### Error: wmic Command Not Found

**Symptom**: merge_with_validation.bat fails at backup tag creation

**Example Error**:
```
'wmic' is not recognized as an internal or external command
fatal: 'pre-merge-backup-~0,8datetime:~8,6' is not a valid tag name
```

**Root Cause**:
- wmic deprecated in Windows 11
- Not available in Git Bash environment

**Solution**: Script has been updated to use PowerShell instead
```batch
REM NEW (FIXED):
for /f "usebackq" %%i in (`powershell -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set datetime=%%i
```

**Prevention**: Use PowerShell for cross-platform Windows compatibility

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
- validate_branches.bat now checks CI policy pre-merge ([9/9] check)
- merge_with_validation.bat validates docs before completing merge ([6/7] check)

---

### Error: Merge Conflicts Not Auto-Resolved

**Symptom**: Script reports conflicts but doesn't resolve them automatically

**Example**:
```
⚠ Merge conflicts detected - analyzing...
Found modify/delete conflicts for excluded files
[Lists files but doesn't resolve them]
```

**Root Cause**: Conflict resolution loop error handling issue in older script version

**Solution**:
1. Manual resolution:
   ```bash
   # For test files (exclude from main)
   git rm tests/fixtures/sample_code.py tests/integration/*.py tests/unit/*.py

   # For docs (check if allowed on main)
   git add docs/ALLOWED_FILE.md  # If in CI policy
   git rm docs/DEV_ONLY_FILE.md  # If NOT in CI policy

   # Complete merge
   git commit --no-edit
   ```

2. Script has been improved with:
   - Temp file approach for better parsing
   - Error checking for each file
   - Verification after resolution

**Prevention**: Updated script with enhanced error handling and validation

---

### Error: Missing --unsafe-fixes Flag

**Symptom**:
- Lint errors remain after running fix_lint.bat
- Ruff reports "hidden fixes can be enabled with --unsafe-fixes"

**Example**:
```
144 hidden fixes can be enabled with the `--unsafe-fixes` option
```

**Root Cause**: fix_lint.bat missing --unsafe-fixes flag

**Solution**: Script has been updated:
```batch
REM NEW (FIXED):
call .venv\Scripts\ruff.exe check . --fix --unsafe-fixes
```

**Prevention**: Script now includes --unsafe-fixes by default (91% auto-fix success rate)

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

**Prevention**: validate_branches.bat checks merge.ours driver configuration ([6/9] check)

## 🔍 Lint Workflow Best Practices

### When to Run check_lint.bat vs fix_lint.bat

**check_lint.bat** (Read-only validation):
- Before committing changes
- During code review
- To check current code quality
- **Does NOT modify files**

**fix_lint.bat** (Auto-fix issues):
- After making changes
- When you want to clean up code
- Before final commit
- **Modifies files in place**

**Recommended workflow**:
```batch
# 1. Make your changes
# 2. Auto-fix issues
scripts\git\fix_lint.bat

# 3. Review what was fixed
git diff

# 4. Final validation
scripts\git\check_lint.bat

# 5. Commit if all checks pass
scripts\git\commit_enhanced.bat "fix: Your commit message"
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

### Expected Warnings

Some warnings are expected and can be safely ignored or committed:

**B904: Exception handling without chaining**
```python
# Ruff suggests this pattern:
try:
    something()
except ValueError as e:
    raise TypeError("message") from e  # Chaining with 'from e'

# Or explicit suppression:
try:
    something()
except ValueError:
    raise TypeError("message") from None  # Explicit 'from None'
```

- **Impact**: Stylistic preference, not a critical error
- **Location**: Primarily in tests/ directory
- **Action**: Safe to proceed with commit
- **Fix**: Optional - add exception chaining if desired

**Other safe-to-ignore warnings**:
- E501 (line too long) - if breaking would harm readability
- W293 (blank line with whitespace) - auto-fixed by black
- Formatting warnings when using specialized formatting

### Error Code Categories

| Category | Examples | Auto-fixable | Severity |
|----------|----------|--------------|----------|
| **Imports** | F401, F811, I001 | ✅ Yes (isort) | Low |
| **Formatting** | W293, E501 | ✅ Yes (black) | Low |
| **Code Style** | C401, C414, B007 | ✅ Yes (--unsafe-fixes) | Low |
| **Logic Errors** | F821, F841 | ⚠️ Partial | High |
| **Exception Handling** | B904 | ❌ Manual recommended | Medium |
| **Security** | S608, S307 | ❌ Manual required | Critical |

### Lint Workflow Troubleshooting

**Problem**: "Ruff not found"
```batch
Solution: Activate virtual environment first
call .venv\Scripts\activate.bat
```

**Problem**: "Black would reformat X files"
```batch
Solution: Let black reformat them
.venv\Scripts\black.exe .
```

**Problem**: "isort would reorder imports"
```batch
Solution: Let isort fix them
.venv\Scripts\isort.exe .
```

**Problem**: Lint passes locally but fails in CI
```batch
Possible causes:
1. Different Python versions (CI uses 3.11)
2. Different tool versions (CI uses latest)
3. Files not committed (check git status)

Solution: Check .github/workflows/branch-protection.yml for CI config
```

This workflow ensures your development context remains completely private while maintaining a clean, professional public repository suitable for users and collaborators.
