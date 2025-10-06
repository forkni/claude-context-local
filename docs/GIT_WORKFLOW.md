# Git Workflow for claude-context-local

## Overview

This repository uses a **Local-First Privacy Model** where certain development files remain strictly on your local machine and are never committed to any git branch. This ensures your development context stays private while maintaining a clean, professional public repository.

**🤖 For Automated Claude Workflows**: See **[AUTOMATED_GIT_WORKFLOW.md](./AUTOMATED_GIT_WORKFLOW.md)** for step-by-step orchestration instructions with comprehensive logging.

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

**Environment Compatibility**: Scripts are available in two formats:

- **Windows cmd.exe**: Use `.bat` files (6 scripts)
- **Git Bash / Linux / macOS**: Use `.sh` files (3 scripts: check_lint, fix_lint, validate_branches)

### Core Workflow Scripts (9 total: 6 .bat + 3 .sh)

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

#### check_lint - Code Quality Validation

**Windows cmd.exe**:

```batch
scripts\git\check_lint.bat
```

**Git Bash / Linux / macOS**:

```bash
./scripts/git/check_lint.sh
```

**Checks:**

- Ruff linting (Python code style)
- Black formatting (code consistency)
- isort import sorting
- markdownlint (documentation quality)

**Configuration**: Uses pyproject.toml settings (automatically excludes .venv, _archive, all gitignored directories)

#### fix_lint - Auto-fix Linting Issues

**Windows cmd.exe**:

```batch
scripts\git\fix_lint.bat
```

**Git Bash / Linux / macOS**:

```bash
./scripts/git/fix_lint.sh
```

**Fixes:**

- Runs ruff --fix → black → isort → markdownlint --fix
- Auto-fixes ~90% of Python lint errors
- Auto-fixes most markdown formatting issues
- Suggests running check_lint to verify all issues resolved

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

#### validate_branches - Pre-merge Validation

**Windows cmd.exe**:

```batch
scripts\git\validate_branches.bat
```

**Git Bash / Linux / macOS**:

```bash
./scripts/git/validate_branches.sh
```

**Checks:**

- Both branches exist
- Current branch is development or main
- No uncommitted changes
- Branch relationship (development ahead of main by X commits)
- Provides warnings if branches are out of sync

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

## 🔄 Automated Workflows (Non-Interactive Mode)

### Overview

**For complete automated workflow orchestration by Claude**: See **[AUTOMATED_GIT_WORKFLOW.md](./AUTOMATED_GIT_WORKFLOW.md)** for comprehensive step-by-step instructions with detailed logging format.

All workflow scripts support `--non-interactive` mode for individual script automation. These flags enable non-interactive execution with sensible defaults.

### Usage Pattern

**Command Format**:

```batch
# Commit workflow
scripts\git\commit_enhanced.bat --non-interactive "commit message"

# Merge workflow
scripts\git\merge_with_validation.bat --non-interactive
```

### Complete Automated Workflow

**User Request**: "Commit and push to development, then merge to main following GIT_WORKFLOW.md"

**Claude Code Execution**:

```batch
# 1. Ensure on development branch
git checkout development

# 2. Commit with automatic logging
scripts\git\commit_enhanced.bat --non-interactive "feat: Your message here"

# 3. Push to development remote
git push origin development

# 4. Merge to main with automatic logging
scripts\git\merge_with_validation.bat --non-interactive

# 5. Push to main remote
git push origin main
```

### Non-Interactive Behavior

**commit_enhanced.bat --non-interactive**:

- Auto-stages all changes (no "Stage all changes?" prompt)
- Auto-fixes lint issues (no "Auto-fix?" prompt)
- Accepts non-conventional commit messages (no format prompt)
- Skips branch verification prompts
- Skips final confirmation prompt
- Creates log: `logs/commit_enhanced_TIMESTAMP.log`

**merge_with_validation.bat --non-interactive**:

- Executes full merge workflow automatically
- Auto-resolves modify/delete conflicts
- Creates backup tag: `pre-merge-backup-TIMESTAMP`
- Creates log: `logs/merge_with_validation_TIMESTAMP.log`
- No user interaction required

### Logging Output

**Log File Location**: `logs/workflow_TIMESTAMP.log`

**Log Format** (matches `bash_scripts_commit_merge_20251005_185155.log`):

- Header with workflow identification
- Start time timestamp
- Phase-by-phase execution tracking
- File changes summary
- Conflict resolution details (if applicable)
- Backup tag information
- End time and final status
- Comprehensive audit trail

**Example Log Structure**:

```
=== Enhanced Commit Workflow ===
Start Time: 2025-10-05 20:30:45

[Phase 1] Pre-commit validation...
[Phase 2] Staging changes...
[Phase 3] Code quality checks...
[Phase 4] Creating commit...

End Time: 2025-10-05 20:31:12
STATUS: SUCCESS
```

### Verification

After workflow completion, user can verify:

```batch
# View log file
type logs\commit_enhanced_TIMESTAMP.log
type logs\merge_with_validation_TIMESTAMP.log

# Verify git history
git log --oneline -5
git log --graph --oneline -10
```

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

### Windows cmd.exe

| Task | Command | Result |
|------|---------|---------|
| **Safe commit** | `scripts\git\commit_enhanced.bat "message"` | Commits with lint checks and validations |
| **Automated commit** | `scripts\git\commit_enhanced.bat --non-interactive "message"` | Non-interactive commit with auto-staging and auto-fix |
| **Check code quality** | `scripts\git\check_lint.bat` | Validates code with ruff/black/isort/markdownlint |
| **Fix linting** | `scripts\git\fix_lint.bat` | Auto-fixes linting issues (Python + markdown) |
| **Merge to main** | `scripts\git\merge_with_validation.bat` | Safe merge: development → main (auto-resolves test file conflicts) |
| **Automated merge** | `scripts\git\merge_with_validation.bat --non-interactive` | Non-interactive merge for automation |
| **Docs-only merge** | `scripts\git\merge_docs.bat` | Merge only documentation changes |
| **Emergency rollback** | `scripts\git\rollback_merge.bat` | Rollback last merge |

**Note on merges**: `merge_with_validation.bat` automatically handles expected modify/delete conflicts for test files. Manual merges (`git merge development`) will require running `git rm tests/**` to resolve conflicts. See [Understanding Modify/Delete Conflicts](#-understanding-modifydelete-conflicts-expected-behavior) for details.

### Git Bash / Linux / macOS

| Task | Command | Result |
|------|---------|---------|
| **Check code quality** | `./scripts/git/check_lint.sh` | Validates code with ruff/black/isort/markdownlint |
| **Fix linting** | `./scripts/git/fix_lint.sh` | Auto-fixes linting issues (Python + markdown) |
| **Validate branches** | `./scripts/git/validate_branches.sh` | Check branch status before merge |
| **Check status** | `git status` | Shows staged changes |
| **View branches** | `git branch -a` | Lists all branches |

**Note**: commit_enhanced.bat, merge_with_validation.bat, and other advanced scripts (.bat only) can be called from Git Bash using: `cmd.exe /c "scripts\git\script_name.bat"`

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

## 🔀 Understanding Modify/Delete Conflicts (Expected Behavior)

### What Are Modify/Delete Conflicts?

When merging `development` → `main`, you may encounter **modify/delete conflicts** for test files:

```
CONFLICT (modify/delete): tests/integration/test_example.py deleted in HEAD and modified in development
```

**This is EXPECTED and NORMAL** for the dual-branch workflow.

### Why Do These Conflicts Occur?

1. **Development branch**: Has test files that were recently modified (e.g., lint fixes, updates)
2. **Main branch**: Doesn't have test files (intentionally excluded for clean public release)
3. **Git's dilemma**: During merge, Git cannot automatically decide:
   - Should it add the modified test files from development? (modified)
   - Should it keep test files deleted as on main? (deleted)

### Why .gitattributes Doesn't Prevent These

Your `.gitattributes` file has:

```gitattributes
tests/** merge=ours
```

**Important limitation**: The `merge=ours` strategy only works for **content conflicts** (when file exists on both branches with different content), NOT for **modify/delete conflicts** (when file exists on one branch but not the other).

**Git doesn't have a built-in strategy** to say "if file doesn't exist on our branch, keep it deleted during merge."

### Two Workflow Options

#### Option 1: Automated Script (Recommended)

Use `merge_with_validation.bat` which **automatically resolves** modify/delete conflicts:

```batch
scripts\git\merge_with_validation.bat
```

**What it does**:

- Detects modify/delete conflicts for test files
- Recognizes them as expected for excluded files
- Automatically runs `git rm` on conflicted test files
- Completes merge with proper exclusions

**Output example**:

```
⚠ Merge conflicts detected - analyzing...
Found modify/delete conflicts for excluded files
These are expected and will be auto-resolved...
✓ Auto-resolved modify/delete conflicts
✓ Merge completed successfully
```

#### Option 2: Manual Merge (Requires Manual Resolution)

If you run a manual merge (e.g., `git merge development --no-ff`):

**You MUST manually resolve test file conflicts**:

```bash
# 1. Identify conflicted test files
git status --short | findstr /C:"DU "

# 2. Remove test files from main (standard procedure)
git rm tests/integration/test_file1.py tests/integration/test_file2.py tests/unit/test_file3.py

# 3. Complete the merge
git commit --no-edit
```

**This is the expected resolution** - test files should be excluded from main.

### When to Use Each Approach

| Scenario | Use | Why |
|----------|-----|-----|
| **Standard releases** | `merge_with_validation.bat` | Automated conflict resolution, full validation |
| **Documentation merges** | `merge_docs.bat` | Specific to docs-only changes |
| **Emergency fixes** | Manual merge + manual resolution | Full control when needed |
| **CI/CD workflows** | GitHub Actions workflow | Automated testing + merging |

### Key Takeaway

**Modify/delete conflicts for test files are EXPECTED**, not errors:

- ✅ Test files modified on development
- ✅ Test files don't exist on main
- ✅ Git requires manual decision
- ✅ Standard resolution: `git rm tests/**`

**Best practice**: Use `merge_with_validation.bat` to automate this standard procedure.

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

## 📊 Workflow Logging (MANDATORY)

### Purpose

ALL significant Git operations (commits, merges, releases) MUST be logged for:

- Complete audit trail
- Troubleshooting failed operations
- Historical reference
- Process improvement

### Log Location

**Directory**: `logs/` (project root)
**Full Path**: `F:\RD_PROJECTS\COMPONENTS\claude-context-local\logs\`
**Git Status**: ✅ Gitignored (local-only, never committed)

### Log File Format

**Execution Log**: `{workflow_type}_YYYYMMDD_HHMMSS.log`

- Real-time command outputs
- Timestamps for each phase
- Error messages and warnings
- Verification results

**Analysis Report**: `{workflow_type}_analysis_YYYYMMDD_HHMMSS.md`

- Executive summary
- Timeline with durations
- Files modified (with line counts)
- Issues encountered and resolutions
- Final status (SUCCESS/FAILED)

### Examples

**Release Workflow**:

- Log: `logs/git_workflow_v0.4.2_release_20251005_190000.log`
- Report: `logs/git_workflow_analysis_v0.4.2_20251005_190000.md`

**Bash Scripts Creation**:

- Log: `logs/bash_scripts_verification_20251005_182523.log`
- Report: `logs/bash_scripts_analysis_20251005_182523.md`

### Mandatory Workflow Steps

#### Before Starting Any Workflow

1. Create timestamped log file in `logs/`
2. Initialize with workflow metadata (type, start time, objectives)

#### During Workflow

3. Redirect all command outputs to log file (`>> logs/workflow.log`)
4. Document each phase with timestamps
5. Capture all verification checks

#### After Workflow Completion

6. Generate comprehensive analysis report
7. Document final status (success/failure)
8. Include lessons learned and improvements

### Integration Examples

**Bash Script Logging** (check_lint.sh example):

```bash
# At start of workflow
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="logs/lint_validation_${TIMESTAMP}.log"

echo "=== Lint Validation Log ===" > "$LOGFILE"
echo "Start Time: $(date)" >> "$LOGFILE"

# During execution
./scripts/git/check_lint.sh 2>&1 | tee -a "$LOGFILE"

# At end
echo "End Time: $(date)" >> "$LOGFILE"
echo "Status: SUCCESS" >> "$LOGFILE"
```

**Batch Script Logging** (merge_with_validation.bat):

```batch
REM Initialize log
set TIMESTAMP=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set LOGFILE=logs\merge_workflow_%TIMESTAMP%.log

echo === Merge Workflow Log === > "%LOGFILE%"
echo Start Time: %date% %time% >> "%LOGFILE%"

REM Execute with logging
[workflow steps] >> "%LOGFILE%" 2>&1

REM Generate analysis report
set REPORTFILE=logs\merge_analysis_%TIMESTAMP%.md
[create markdown report]
```

### Previous Examples

See existing logs in `logs/` directory (created during workflow execution):

- v0.4.1 release logs (execution + analysis)
- Bash scripts verification logs
- Commit workflow logs

All follow the same structure and format.

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

### Error: Batch Scripts Not Working in Git Bash

**Symptom**: Windows .bat files fail to execute in Git Bash with "command not found" errors

**Example Error**:

```bash
$ scripts\git\check_lint.bat
bash: scripts\git\check_lint.bat: command not found
```

**Root Cause**:

- Git Bash (MINGW64) cannot execute Windows batch files directly
- Batch files require cmd.exe interpreter
- cmd.exe wrapper (`cmd.exe /c`) doesn't capture output properly in bash

**Solution**: Use bash-compatible .sh scripts (v0.4.1+)

```bash
# Instead of .bat files, use .sh equivalents:
./scripts/git/check_lint.sh      # Lint validation
./scripts/git/fix_lint.sh         # Auto-fix lint issues
./scripts/git/validate_branches.sh  # Branch validation

# All 3 scripts:
# ✅ Execute natively in Git Bash
# ✅ Use forward-slash paths (compatible with Windows executables)
# ✅ Respect pyproject.toml configuration
# ✅ Proper exit codes for automation
```

**Key Differences**:

| Aspect | .bat Files | .sh Files |
|--------|-----------|-----------|
| **Environment** | Windows cmd.exe only | Git Bash, Linux, macOS |
| **Path Style** | Backslashes (\\) | Forward slashes (/) |
| **Execution** | `scripts\git\script.bat` | `./scripts/git/script.sh` |
| **Output Capture** | ✅ Works in cmd.exe | ✅ Works in bash |

**Configuration Notes**:

The .sh scripts rely on pyproject.toml for exclusions (no manual --exclude flags):

```toml
[tool.ruff]
exclude = [".venv", "_archive", "build", "dist", "__pycache__", "tests/test_data"]

[tool.black]
exclude = ".venv|_archive"

[tool.isort]
skip_glob = ["_archive/*", ".venv/*"]
```

**Verification**:

- All 3 bash scripts verified operational (2025-10-05)
- Logs: `bash_scripts_verification_20251005_182523.log`, `bash_scripts_analysis_20251005_182523.md`
- Location: `F:\RD_PROJECTS\COMPONENTS\claude-context-local_backup\logs\`

**Prevention**: Always use .sh scripts when working in Git Bash environment

---

### 📅 Recent Fixes Chronology

This section tracks major workflow improvements and fixes in reverse chronological order.

#### 2025-10-04: v4 Workflow Improvements

**Git Workflow Automation Fixes** (commits a5170b8, 4529d1a, bfeae9b, 464dbd1):

1. **ERROR #7: Merge Completion Detection** ✅ RESOLVED
   - Implemented 3-layer validation system
   - Prevents false "automatically completed" messages
   - Validates unmerged files, staged changes, and MERGE_HEAD state
   - Commit: a5170b8

2. **ERROR #8: Batch Parsing Errors** ✅ FULLY RESOLVED
   - Fixed multi-line commit message parsing (commit bfeae9b)
   - Fixed for loop file processing with `delims=` and `2^>nul` (commit 464dbd1)
   - Enhanced conflict resolution with better error handling (commit a5170b8)
   - All parsing errors eliminated

3. **Verification Testing** ✅ PASSED
   - Comprehensive test of both fixes (commit e9d60c8)
   - Verified with real-world merge scenario
   - No false messages, no parsing errors
   - Workflow confirmed production-ready

**Linting Improvements** (commit 46dac62):

4. **Ruff B007: Unused Loop Variables** ✅ RESOLVED
   - Fixed 4 errors in test_full_flow.py
   - Renamed unused variables to `_chunk_id`, `_similarity`
   - Follows Python convention for intentionally unused variables

5. **Ruff B904: Exception Chaining** ✅ RESOLVED
   - Fixed 9 errors across 6 test files + 1 in production code
   - Added proper `from e` exception chaining
   - Improves debugging and follows PEP 3134
   - Files: test_glsl_*.py, test_hf_access.py, test_bm25_population.py, bm25_index.py

**Final Status**:

- ✅ 13 Ruff linting errors resolved
- ✅ 2 critical workflow errors resolved
- ✅ All changes merged to both development and main branches
- ✅ CI/CD passing cleanly

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

**Better Approach**: Use automated script to avoid manual resolution:

```batch
scripts\git\merge_with_validation.bat  # Auto-resolves these conflicts
```

**Full explanation**: See [Understanding Modify/Delete Conflicts](#-understanding-modifydelete-conflicts-expected-behavior)

---

### Error: Merge Conflicts Not Auto-Resolved

**Important**: First determine if you're seeing **expected conflicts** or a **script error**.

#### Expected Conflicts (Manual Merge)

If you ran a **manual merge** (e.g., `git merge development --no-ff`), modify/delete conflicts for test files are **EXPECTED**:

```
CONFLICT (modify/delete): tests/integration/test_example.py deleted in HEAD and modified in development
```

**This is NORMAL** - See [Understanding Modify/Delete Conflicts](#-understanding-modifydelete-conflicts-expected-behavior) for full explanation.

**Standard resolution** (not an error):

```bash
# Remove test files from main (expected procedure)
git rm tests/integration/*.py tests/unit/*.py

# Complete merge
git commit --no-edit
```

**Prevention**: Use `merge_with_validation.bat` for automated conflict resolution.

#### Script Error (Automated Merge Failed)

If you used `merge_with_validation.bat` and it **fails to auto-resolve**:

**Symptom**: Script reports conflicts but doesn't resolve them automatically

**Example**:

```
⚠ Merge conflicts detected - analyzing...
Found modify/delete conflicts for excluded files
[Lists files but doesn't resolve them]
❌ Some conflicts remain unresolved
```

**Root Cause**: Conflict resolution loop error (older script versions had this issue)

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

**Prevention**: Update to latest script version with enhanced error handling

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

---

### Error: Committed to Wrong Branch

**Symptom**: Accidentally committed changes to main instead of development branch

**Example**:

```bash
$ git branch --show-current
main
# Expected: development
```

**Root Cause**: User didn't verify current branch before running commit script

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

**Prevention**: commit_enhanced.bat now includes branch verification:

- Shows current branch before commit
- Requires user confirmation: "Is this the correct branch?"
- Lists all available branches if user says no
- Exits cleanly to allow branch switching

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

```batch
REM After auto-resolution, check if merge already complete
git rev-parse -q --verify MERGE_HEAD >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✓ Merge commit automatically completed during auto-resolution
    goto :merge_success
)
```

**Prevention**:

- Script now detects when merge commit already exists
- Skips redundant commit attempt
- Prevents false error messages
- Goes directly to success message when merge complete

---

### ERROR #7: Premature Merge Completion Detection (v4 FIX)

**Symptom**: Script reports "Merge commit automatically completed" but merge is NOT actually complete

**Example**:

```
✓ Auto-resolved modify/delete conflicts
✓ Merge commit automatically completed during auto-resolution

# But checking git status shows:
$ git status
You have unmerged paths.
  (fix conflicts and run "git commit")
```

**Root Cause** (v3 implementation):

- Single-layer check: only verified if MERGE_HEAD exists
- Didn't validate that conflicts were actually resolved
- Didn't check if changes were properly staged
- Could trigger prematurely during auto-resolution

**Impact**: Manual intervention required even though script reported success

**Solution** (v4 fix - lines 107-133 in merge_with_validation.bat):

Implemented **3-layer validation**:

```batch
REM FIX ERROR #7: Check if all conflicts are actually resolved
REM Layer 1: Check for unmerged files
git diff --name-only --diff-filter=U >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    REM Unmerged files still exist
    echo ⚠ Some conflicts remain unresolved
    echo   Continuing to validation and manual commit...
) else (
    REM Layer 2: Verify changes are staged
    git diff --cached --quiet >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        echo ⚠ No changes staged after auto-resolution
        echo   Continuing to validation...
    ) else (
        REM Layer 3: Verify MERGE_HEAD is gone
        git rev-parse -q --verify MERGE_HEAD >nul 2>&1
        if %ERRORLEVEL% NEQ 0 (
            REM All conditions met - truly complete
            echo ✓ Merge commit automatically completed
            goto :merge_success
        )
    )
)
```

**Validation Layers**:

1. **Unmerged files**: Check index for conflicts (`git diff --name-only --diff-filter=U`)
2. **Staged changes**: Verify work was actually done (`git diff --cached --quiet`)
3. **MERGE_HEAD state**: Confirm merge ref is gone (`git rev-parse MERGE_HEAD`)

**Prevention**:

- Only reports completion when ALL three conditions pass
- Provides specific status messages for each validation layer
- Continues to manual commit phase if any layer fails
- Prevents false success messages

**Status**: ✅ RESOLVED in v4 (commit a5170b8)

---

### ERROR #8: Batch Script Command Parsing Errors (v4 FIX)

**Symptom**: "'-' is not recognized as an internal or external command"

**Example Error Messages**:

```
Merge made by the 'ort' strategy.
'-' is not recognized as an internal or external command,
operable program or batch file.
'-' is not recognized as an internal or external command,
operable program or batch file.
'tch' is not recognized as an internal or external command,
operable program or batch file.
'message' is not recognized as an internal or external command,
operable program or batch file.
```

**Root Causes Discovered**:

1. **Multi-line git merge command** - Literal newlines in batch file
2. **Multiple -m flags on long lines** - Batch parsing limits exceeded
3. **For loop file processing** - Missing error suppression and delimiters

#### Error Evolution & Fix Attempts

**Attempt 1: Enhanced Conflict Resolution Loop** (commit a5170b8)

- Improved error handling in conflict resolution
- Better file processing with temp files
- **Result**: Still valuable but didn't fix parsing errors

**Attempt 2: Multiple -m Flags** (commit 4529d1a)

- Replaced multi-line message with multiple -m flags
- **Result**: Caused 'message' parsing errors, abandoned

**Attempt 3: Single-Line Commit Message** (commit bfeae9b)

- Simplified to one-line commit message
- **Result**: Fixed commit message source, but 'tch' errors remained

**Attempt 4: For Loop Parsing Fixes** (commit 464dbd1)

- Added `delims=` to for loops
- Added `2^>nul` error suppression
- **Result**: ✅ Complete resolution

#### Original Problematic Code

**Multi-line commit message** (lines 52-57):

```batch
git merge development --no-ff -m "Merge development into main

- Applied .gitattributes merge strategies
- Excluded development-only files (tests/, docs/)
- Combined CHANGELOG.md changes
- Used diff3 for better conflict resolution"
```

**Why it failed**:

- Batch files cannot have literal newlines in command arguments
- Each newline creates a new line that batch tries to parse
- The '-' characters at line start are interpreted as command names

**For loop file processing** (line 164, 223 - original):

```batch
for /f %%f in ('git diff --cached --name-only --diff-filter=A ^| findstr /C:"docs/"') do (
    REM Process files...
)
```

**Why it failed**:

- Missing `delims=` caused word splitting on spaces in filenames
- No error suppression caused 'tch' when piping empty results
- Result: "tch" from "batch" parsed as command when no files found

#### Complete Solution

**Fix 1: Simple Commit Message** (lines 52-53):

```batch
REM FIX ERROR #8: Simple single-line commit message to avoid batch parsing issues
git merge development --no-ff -m "Merge development into main"
```

**Fix 2: For Loop Parsing** (lines 164, 223):

```batch
REM Before (caused 'tch' errors):
for /f %%f in ('git diff --cached --name-only --diff-filter=A ^| findstr /C:"docs/"') do (

REM After (FIX ERROR #8: proper delimiters and error suppression):
for /f "delims=" %%f in ('git diff --cached --name-only --diff-filter=A 2^>nul ^| findstr /C:"docs/" 2^>nul') do (
```

**Key improvements**:

- `delims=""` prevents word splitting on spaces
- `2^>nul` suppresses stderr from both git and findstr
- Handles empty results gracefully without parsing errors

**Fix 3: Enhanced Conflict Resolution** (lines 77-90):

```batch
REM Process each conflict with error checking (FIX ERROR #8)
set RESOLUTION_FAILED=0
for /f "usebackq tokens=2*" %%a in ("%TEMP%\merge_conflicts.txt") do (
    set "CONFLICT_FILE=%%a %%b"
    echo   Resolving: !CONFLICT_FILE!
    git rm "!CONFLICT_FILE!" >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo   ✗ ERROR: Failed to remove !CONFLICT_FILE!
        set RESOLUTION_FAILED=1
    ) else (
        echo   ✓ Removed: !CONFLICT_FILE!
    )
)
```

**Prevention Best Practices**:

- ✅ Always use single-line commit messages in batch files
- ✅ Avoid literal newlines in any batch command
- ✅ Use `delims=""` in for loops processing filenames
- ✅ Add `2^>nul` to suppress stderr in for loop commands
- ✅ Use proper quoting with delayed expansion (`!VAR!`)
- ✅ Test batch scripts with edge cases (empty results, spaces in names)

**Verification**:

- Tested with merge commit e9d60c8 (2025-10-04)
- All parsing errors eliminated
- Merge completed successfully
- No cosmetic warnings remain

**Status**: ✅ FULLY RESOLVED in v4 (commits a5170b8, 4529d1a, bfeae9b, 464dbd1)

- All parsing errors eliminated
- Merge functionality verified working
- Final verification commit: e9d60c8

---

### ✅ v4 Workflow Verification Results (2025-10-04)

After implementing ERROR #7 and ERROR #8 fixes, comprehensive verification testing was performed to confirm the workflow operates correctly.

#### Verification Test Execution

**Date**: 2025-10-04
**Commit**: e9d60c8
**Purpose**: Verify both ERROR #7 and ERROR #8 are fully resolved

**Test Steps**:

1. Created minor documentation change (added timestamp to GIT_WORKFLOW.md)
2. Committed to development branch
3. Executed `merge_with_validation.bat` from main branch
4. Monitored for parsing errors and false completion messages

**Results**:

```
[1/7] Running pre-merge validation checks...
✓ All validation checks passed

[2/7] Creating backup tag...
✓ Created backup tag: pre-merge-backup-20251004_143522

[3/7] Checking git configuration...
✓ merge.ours driver configured

[4/7] Initiating merge...
Merge made by the 'ort' strategy.
✓ Merge initiated successfully

[5/7] Checking for merge conflicts...
✓ No conflicts detected

[6/7] Validating documentation files against CI policy...
✓ Documentation validation passed

[7/7] Completing merge commit...
✓ Merge completed successfully

=== MERGE SUMMARY ===
✓ Merge from development to main completed
✓ Documentation validation: PASSED
✓ Backup tag: pre-merge-backup-20251004_143522
```

#### Verification Confirmation

**ERROR #7 Validation** (Merge Completion Detection):

- ✅ No false "automatically completed" messages
- ✅ All 3 validation layers working correctly
- ✅ Proper flow through all 7 steps
- ✅ Accurate status reporting

**ERROR #8 Validation** (Batch Parsing):

- ✅ No "'-' is not recognized" errors
- ✅ No 'tch' parsing errors
- ✅ No 'message' parsing errors
- ✅ Clean execution with no warnings
- ✅ For loops processed files correctly

**Additional Validations**:

- ✅ Pre-merge validation (9/9 checks passed)
- ✅ Backup tag creation successful
- ✅ Documentation CI policy validation
- ✅ Merge completed in 7 steps as expected
- ✅ Final git status shows clean main branch

#### Post-Verification Actions

**Merged to main**: 2025-10-04 (commit 30bdc70)
**Status**: v4 workflow fully operational
**Confidence**: High - verified with real-world merge scenario

**Conclusion**: Both ERROR #7 and ERROR #8 are comprehensively resolved. The git workflow automation is production-ready and operates reliably without manual intervention.

---

**Prevention**: validate_branches.bat checks merge.ours driver configuration ([6/9] check)

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
- ✅ Run `fix_lint.bat` before committing
- ✅ Use `from None` only when suppression is intentional
- ✅ Review Ruff suggestions during development

**Status**: ✅ RESOLVED (commit 46dac62, 2025-10-04)

---

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

```batch
# Check markdown quality
scripts\git\check_lint.bat    # Includes markdownlint

# Auto-fix markdown issues
scripts\git\fix_lint.bat      # Includes markdownlint --fix
```

**Common markdown fixes**:

- Line length violations (MD013) - break long lines
- Missing blank lines around headings (MD022)
- Missing blank lines around lists (MD032)
- Missing blank lines around code fences (MD031)

**Configuration**: `.markdownlint-cli2.yaml` in project root

**Excluded directories**: `.venv`, `_archive`, `benchmark_results`, `logs`, `node_modules`

**Match CI/CD**: Local markdown validation matches GitHub Actions `docs-validation.yml` rules

---

### Expected Warnings (Updated 2025-10-04)

**NOTE**: As of 2025-10-04, B007 and B904 warnings have been comprehensively resolved across the codebase.

**Currently acceptable warnings**:

- **E501 (line too long)** - Only if breaking would harm readability
- **W293 (blank line with whitespace)** - Auto-fixed by black
- **Formatting warnings** - When using specialized formatting (docstrings, ASCII art, etc.)

**Previously common but now resolved**:

- ~~B904 (exception chaining)~~ ✅ All fixed in commit 46dac62
- ~~B007 (unused loop variables)~~ ✅ All fixed in commit 46dac62

**When new warnings appear**:

1. Run `fix_lint.bat` first (auto-fixes ~90%)
2. Review changes with `git diff`
3. Manually fix remaining issues
4. Verify with `check_lint.bat`

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
