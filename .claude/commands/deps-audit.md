---
model: claude-sonnet-4-5
---

# Practical Dependency Audit for Python/ML Projects

**Purpose**: Quick, actionable dependency review for Python projects with ML/AI dependencies.
**Time**: 10 minutes initial setup + 5 minutes quarterly review
**Focus**: Known vulnerabilities, license compliance, ML-specific compatibility

## When to Use This Command

✅ **Good use cases:**

- Quarterly security review
- Before major releases
- After adding new ML dependencies
- Investigating known CVEs

❌ **Don't use for:**

- Daily/weekly monitoring (overkill for local tools)
- Internet-exposed production services (need enterprise security)
- Projects with < 10 dependencies (just review manually)

## Arguments

This command takes no arguments. Run directly with `/deps-audit` to audit the current project's dependencies.

**Requirements:**

- Active Python virtual environment (`.venv` or similar)
- Project with `pyproject.toml` or `requirements.txt`
- Internet connection for vulnerability database queries

---

## Setup: Audit Reports Directory

**IMPORTANT**: All audit outputs should be saved to the `audit_reports/` directory to keep the project root clean.

```bash
# Directory already exists in project root
# Structure:
audit_reports/
├── README.md                          # Usage guide
├── YYYY-MM-DD-audit.json             # Regular audits
├── before-fixes-YYYY-MM-DD.json      # Baseline before updates
├── after-fixes-YYYY-MM-DD.json       # Verification after updates
└── archive/                           # Historical reports (optional)
```

**Why this matters:**

- ✅ Git-ignored by default (no sensitive data committed)
- ✅ Organized history for tracking improvements
- ✅ Clean project root
- ✅ Easy to archive/delete old reports

---

## Phase 1: Quick Vulnerability Scan (1 minute)

### Use pip-audit (Official PyPA Tool)

**Why pip-audit?**

- ✅ Official Python Packaging Authority tool
- ✅ Free and actively maintained
- ✅ Queries OSV database (Google's Open Source Vulnerabilities)
- ❌ NOT "safety" (deprecated, moved to paid service)

```bash
# Install once (in your virtual environment)
.venv/Scripts/pip install pip-audit  # Windows
# or: .venv/bin/pip install pip-audit  # Linux/Mac

# Run vulnerability scan
.venv/Scripts/pip-audit --format json > audit_reports/2025-11-20-audit.json

# Check specific requirements file
.venv/Scripts/pip-audit -r requirements.txt --format json > audit_reports/requirements-audit.json
```

### ⚠️ Windows Users: Avoid Unicode Errors

**Issue**: The `--desc` flag causes `UnicodeEncodeError` on Windows consoles (cp1252 encoding).

**Solution**: Always use `--format json` on Windows:

```bash
# ✅ Windows-safe command
.venv/Scripts/pip-audit --format json > audit_reports/audit.json

# ❌ Avoid on Windows (crashes)
.venv/Scripts/pip-audit --desc
```

**Tip**: Parse JSON with the Python helper script at `tools/summarize_audit.py` (see Helper Script section) or use online JSON viewers.

### Interpret Results

**Priority Levels:**

| Severity | Action Required | Timeline |
|----------|----------------|----------|
| **Critical** | 🔴 Update immediately | Within 24 hours |
| **High** | 🟡 Update soon | Within 1 week |
| **Medium** | 🟢 Plan update | Next sprint |
| **Low** | ⚪ Consider update | Quarterly review |

**ML-Specific Red Flags:**

- PyTorch vulnerabilities (model deserialization, JIT compiler)
- transformers CVEs (arbitrary code execution in configs)
- FAISS issues (memory corruption in C++ layer)
- tree-sitter parser vulnerabilities

---

## Phase 2: License Compliance Check (10 minutes, ONE TIME)

### Generate License Report

```bash
# Install once
pip install pip-licenses

# Generate comprehensive report
pip-licenses --format=markdown --with-urls > docs/LICENSE_AUDIT.md

# Check for problematic licenses
pip-licenses --summary
```

### License Compatibility Matrix

**For GPL-3.0 Projects:**

| License | Compatible? | Notes |
|---------|-------------|-------|
| MIT | ✅ Yes | Most common, fully compatible |
| Apache-2.0 | ✅ Yes | Common for ML libs (torch, transformers) |
| BSD-3-Clause | ✅ Yes | Permissive, compatible |
| LGPL-3.0 | ✅ Yes | Library GPL, compatible |
| GPL-2.0 | ⚠️ Check | May need GPL-3.0+ |
| AGPL-3.0 | ⚠️ Review | Strong copyleft for network services |
| Proprietary | ❌ No | Cannot use without license |
| Unknown | ⚠️ Investigate | Contact maintainer |

**For MIT/Apache Projects:**

- MIT/Apache/BSD dependencies: ✅ All compatible
- GPL dependencies: ❌ Incompatible (forces GPL license)
- AGPL dependencies: ❌ Strong copyleft restriction

### One-Time License Audit Process

1. **Generate report** → Review all licenses
2. **Identify issues** → Flag GPL/AGPL/Unknown licenses
3. **Document compliance** → Commit LICENSE_AUDIT.md to repo
4. **Done** → Licenses don't change, no need to repeat

---

## Phase 3: ML Dependency Health Check (10 minutes)

### Critical ML Dependencies to Monitor

```bash
# Check core ML packages
pip list | grep -E "torch|transformers|faiss|sentence-transformers"

# Check for outdated critical packages
pip list --outdated | grep -E "torch|transformers|faiss|huggingface"
```

### PyTorch/CUDA Compatibility

**⚠️ CRITICAL for ML Projects:**

```python
# Verify PyTorch + CUDA compatibility
python -c "
import torch
print(f'PyTorch Version: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA Version: {torch.version.cuda}')
    print(f'GPU Count: {torch.cuda.device_count()}')
    print(f'GPU Name: {torch.cuda.get_device_name(0)}')
"
```

### ML Dependency Update Strategy

🚫 **NEVER auto-update these packages:**

- `torch`, `torchvision`, `torchaudio` (CUDA compatibility)
- `transformers` (model behavior changes)
- `faiss-cpu` / `faiss-gpu` (index format changes)
- `sentence-transformers` (embedding changes)

✅ **Safe to update (with testing):**

- `pytest`, `rich`, `click` (dev tools)
- `psutil`, `tqdm` (utilities)
- `nltk`, `tiktoken` (tokenizers)

### Manual Update Process for ML Packages

```bash
# 1. Check release notes
# Visit: https://github.com/pytorch/pytorch/releases
# Visit: https://github.com/huggingface/transformers/releases

# 2. Test in isolated environment
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# or: test_env\Scripts\activate  # Windows

# 3. Update and test
pip install torch==2.6.1  # Example version
python -m pytest tests/  # Run full test suite

# 4. Verify CUDA still works
python -c "import torch; print(torch.cuda.is_available())"

# 5. If all tests pass, update pyproject.toml
# If tests fail, investigate before updating
```

---

## Phase 4: Outdated Dependencies Review (5 minutes)

### Quick Check

```bash
# List all outdated packages
pip list --outdated

# Filter for security updates only
pip list --outdated --format=json | \
  python -c "import sys, json; \
  [print(f\"{p['name']}: {p['version']} → {p['latest_version']}\") \
   for p in json.load(sys.stdin)]"
```

### Prioritization Matrix

| Criteria | Score | Examples |
|----------|-------|----------|
| Has security CVE | +100 | Any package in pip-audit output |
| Core ML dependency | +50 | torch, transformers, faiss |
| >1 year old | +30 | Check version date on PyPI |
| Major version behind | +20 | 2.x → 3.x |
| Minor version behind | +10 | 2.5.x → 2.6.x |
| Patch version only | +5 | 2.6.0 → 2.6.1 |

**Priority Buckets:**

- **Score >100**: Update this week (security issue)
- **Score 50-100**: Update next sprint (ML core + old)
- **Score 20-50**: Update quarterly
- **Score <20**: Update if convenient

---

## Phase 5: Practical Security Hardening (Optional)

### Only Do This If You Actually Need It

**When you DON'T need this:**

- Local development tool
- Single developer/small team
- Trusted code sources only
- No internet exposure

**When you DO need this:**

- Public-facing API
- Multi-tenant service
- Processing untrusted input
- Enterprise deployment

### Basic Security Practices (Low Effort, High Value)

```python
# 1. Don't load untrusted models
# ❌ BAD: model = torch.load(untrusted_file)
# ✅ GOOD: Only load from official HuggingFace or verified sources

# 2. Validate input sizes (prevent OOM)
def parse_code(code_content: str, max_size_mb: int = 10) -> dict:
    if len(code_content) > max_size_mb * 1024 * 1024:
        raise ValueError(f"Input exceeds {max_size_mb}MB limit")
    # Parse with tree-sitter...

# 3. Pin major versions (prevent breaking changes)
# pyproject.toml:
# torch = ">=2.6.0,<3.0.0"  # NOT: ">=2.6.0"
# transformers = ">=4.51.0,<5.0.0"
```

---

## Phase 6: Apply Fixes Safely (30-60 minutes)

### Before/After Workflow

**Critical**: Always save baseline audits before applying security updates to track which CVEs were fixed.

```bash
# 1. Save baseline audit
.venv/Scripts/pip-audit --format json > audit_reports/before-fixes-2025-11-20.json

# 2. Review vulnerabilities
python tools/summarize_audit.py audit_reports/before-fixes-2025-11-20.json

# 3. Create feature branch (if using git)
git checkout -b security-fixes-2025-11-20

# 4. Apply updates ONE AT A TIME
pip install --upgrade authlib==1.6.5

# 5. Test after EACH update
python -m pytest tests/
python -c "import authlib; print(f'✓ authlib {authlib.__version__}')"

# 6. If tests pass, continue with next package
pip install --upgrade pip==25.3
python -m pytest tests/

# 7. Save post-fix audit
.venv/Scripts/pip-audit --format json > audit_reports/after-fixes-2025-11-20.json

# 8. Verify all CVEs resolved
python tools/summarize_audit.py audit_reports/after-fixes-2025-11-20.json
# Expected: "Total CVEs: 0" or reduced count

# 9. Update pyproject.toml/requirements.txt
# Document minimum versions that fix CVEs:
# authlib = ">=1.6.5"  # Fixes CVE-2025-59420
# pip = ">=25.3"       # Fixes CVE-2025-8869
```

### Update Strategy by Package Type

| Package Type | Strategy | Rationale |
|-------------|----------|-----------|
| **Security-critical** (authlib, cryptography) | Update immediately | CVEs in auth/crypto are high-risk |
| **ML core** (torch, transformers, faiss) | Test thoroughly first | CUDA/model compatibility fragile |
| **Dev tools** (pip, pytest, ruff) | Update with caution | Can break CI/CD workflows |
| **Utilities** (psutil, tqdm, click) | Safe to update | Low breaking change risk |

### Rollback Plan

If an update breaks functionality:

```bash
# 1. Check what broke
python -m pytest tests/ -v

# 2. Identify failing package
pip list --format=freeze | grep package-name

# 3. Rollback to previous version
pip install package-name==old.version.number

# 4. Re-run tests
python -m pytest tests/

# 5. Document issue
# Add note in audit_reports/after-fixes-2025-11-20.json:
# "authlib 1.6.5 breaks OAuth flow, keeping 1.6.3 until v1.6.6"

# 6. Accept security risk temporarily
# Update quarterly review to check for fixed version
```

### Testing Checklist

After applying security updates, verify:

- [ ] **Unit tests pass**: `pytest tests/unit/`
- [ ] **Integration tests pass**: `pytest tests/integration/`
- [ ] **ML functionality works**: Run sample inference/indexing
- [ ] **CUDA still available** (if ML project): `python -c "import torch; assert torch.cuda.is_available()"`
- [ ] **No new import errors**: `python -c "import main_module"`
- [ ] **CLI commands work**: Run your project's main entry points
- [ ] **Dependencies resolved**: `pip check` reports no conflicts

### When to Skip a Fix

**Legitimate reasons to defer a CVE fix:**

1. **No fixed version available yet** → Monitor for updates
2. **Fix breaks critical functionality** → Document and track
3. **CVE doesn't apply to your use case** → Example: network CVE but you run locally
4. **Requires major dependency upgrade** → Example: PyTorch 2.6→3.0 not stable yet

**Document all deferred fixes** in `audit_reports/deferred-cves-2025-11-20.md`:

```markdown
## Deferred CVE Fixes

### CVE-2025-59420 (authlib 1.6.3)
- **Reason**: v1.6.5 breaks OAuth flow (see issue #123)
- **Mitigation**: Running locally only, no untrusted JWS inputs
- **Review date**: 2025-12-20 (check for v1.6.6)
```

---

## Phase 7: Cleanup Audit Tools (Optional)

After completing your security updates, you have two options for managing the audit tools (`pip-audit`, `pip-licenses`):

### Option A: Keep Tools Installed (Recommended for Active Projects)

**When to choose this:**

- ✅ You plan quarterly maintenance reviews (every 3 months)
- ✅ You're actively developing/maintaining the project
- ✅ Disk space isn't a concern (~15-20 MB for both tools)
- ✅ You want instant access to audit commands

**What to do:**

```bash
# Nothing! Keep pip-audit and pip-licenses installed
# They'll be ready for your next quarterly review

# Optional: Document these as dev dependencies in pyproject.toml
# [tool.poetry.group.dev.dependencies]
# pip-audit = ">=2.7.3"
# pip-licenses = ">=5.0.0"
```

**Benefit**: 30-60 seconds saved every quarter (no reinstall time).

### Option B: Remove Tools After Audit (Cleaner Environment)

**When to choose this:**

- ✅ You rarely run audits (< 2 times/year)
- ✅ You want minimal virtual environment footprint
- ✅ You're archiving/freezing the project
- ✅ You use containerized builds (want lean images)

**What to do:**

```bash
# Remove audit tools after saving reports
pip uninstall pip-audit pip-licenses -y

# Verify removal
pip list | grep -E "pip-audit|pip-licenses"
# (should return nothing)

# Your audit reports remain safe in audit_reports/
ls audit_reports/*.json  # Confirms historical data preserved
```

**Benefit**: Cleaner virtual environment, ~15-20 MB disk space saved.

### Decision Matrix

| Factor | Keep Tools | Remove Tools |
|--------|-----------|-------------|
| **Quarterly reviews** | ✅ Best choice | ❌ Must reinstall |
| **Archived project** | ❌ Wastes space | ✅ Best choice |
| **Disk space critical** | ❌ ~20 MB used | ✅ Saves space |
| **Container builds** | ❌ Bloats image | ✅ Lean image |
| **Active development** | ✅ Always ready | ⚠️ Reinstall delay |

### If You Remove Tools: Quick Reinstall

**Next quarterly review:**

```bash
# Takes 30-60 seconds to reinstall
.venv/Scripts/pip install pip-audit pip-licenses

# Continue with audit workflow
.venv/Scripts/pip-audit --format json > audit_reports/quarterly-2025-02-20.json
```

**Bottom Line**: For most projects with regular maintenance, **keep the tools installed**. Only remove them for archived projects or when disk space is truly constrained.

---

## Output Format

**Executive Summary:**

```
=== Dependency Audit Summary ===
Date: 2025-11-20
Total Dependencies: 38
Known Vulnerabilities: 0 critical, 1 high, 2 medium
License Compliance: PASS (GPL-3.0 compatible)
Outdated Packages: 5 (2 high priority)
ML Stack Health: GOOD (PyTorch 2.6.0, CUDA 12.4)

Immediate Actions Required:
1. [None] or [Update package X for CVE-YYYY-NNNN]

Quarterly Review Actions:
1. Update pytest 8.4.2 → 8.5.0
2. Review transformers 4.51.0 → 4.52.0 (breaking changes?)
3. Re-run pip-audit in 3 months
```

---

## Quarterly Maintenance Workflow (5 minutes)

**Every 3 months, run this checklist:**

```bash
# ✅ 1. Vulnerability scan (1 minute)
.venv/Scripts/pip-audit --format json > audit_reports/quarterly-2025-11-20.json

# ✅ 2. Check outdated packages (1 minute)
pip list --outdated | grep -E "torch|transformers|faiss|pytest"

# ✅ 3. Review PyTorch/CUDA (30 seconds)
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA {torch.cuda.is_available()}')"

# ✅ 4. Check for breaking changes (2 minutes)
# - Visit PyTorch releases: https://github.com/pytorch/pytorch/releases
# - Visit transformers releases: https://github.com/huggingface/transformers/releases
# - Scan for security fixes or critical bugs

# ✅ 5. Update if needed (1 minute to decide, longer to test)
# - Review audit_reports/quarterly-2025-11-20.json for critical CVEs
# - Test in isolated environment first if updating
# - Run full test suite before committing

# ✅ 6. Cleanup old reports (30 seconds)
# - Keep current + previous 2 audits
# - Archive or delete reports older than 90 days
```

---

## What NOT to Do (Anti-Patterns)

❌ **Don't set up automated updates** → Breaks ML stacks
❌ **Don't run daily scans** → Alert fatigue for local tools
❌ **Don't implement model signing** → HTTPS from HuggingFace is sufficient
❌ **Don't monitor supply chain for torch/transformers** → Would be headline news
❌ **Don't set up Slack alerts** → Over-engineering for small projects
❌ **Don't auto-update via Dependabot** → ML dependencies need manual testing

---

## Real-World Risk Assessment

**Actual security risks for Python/ML projects:**

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Known CVE in dependency | Medium | High | pip-audit quarterly |
| PyTorch deserialization attack | Low | High | Only load trusted models |
| CUDA driver incompatibility | Medium | High | Test updates thoroughly |
| GPL license violation | Low | Medium | One-time license audit |
| Tree-sitter parser exploit | Very Low | Low | Keep updated |

**NOT actual risks:**

- HuggingFace model repository compromise (HTTPS + checksums built-in)
- Typosquatting "torsh" instead of "torch" (you'd notice immediately)
- Supply chain attack on PyTorch (millions of users, would be detected fast)

---

## Tools Reference

```bash
# Core tools (install once)
pip install pip-audit pip-licenses

# Vulnerability scanning
pip-audit --desc                    # Quick scan (Linux/Mac only, see Windows warning)
pip-audit --format json > audit_reports/audit.json  # Machine-readable (Windows-safe)

# License checking
pip-licenses --summary              # Quick overview
pip-licenses --format=markdown > licenses.md  # Full report

# Dependency analysis
pip list --outdated                 # Check for updates
pip show <package>                  # Package details
pip-licenses --packages <package>   # Package license

# Cleanup (optional, see Phase 7 for guidance)
pip uninstall pip-audit pip-licenses -y  # Remove audit tools after review
pip list | grep -E "pip-audit|pip-licenses"  # Verify removal (should be empty)
```

**Note**: These are **development tools**, not production dependencies. Consider adding to `[tool.poetry.group.dev.dependencies]` in `pyproject.toml` if using Poetry, or keep them in your virtual environment for quarterly maintenance.

---

## Summary: Practical vs Enterprise Approach

**This Command (Practical):**

- ✅ 10-min setup + 5-min quarterly
- ✅ Focuses on known CVEs and ML compatibility
- ✅ Manual updates with testing
- ✅ One-time license audit
- ✅ Low maintenance, high value

**Enterprise Security Theater (Don't Do This):**

- ❌ Weekly automated scans
- ❌ Model integrity checking
- ❌ Supply chain monitoring
- ❌ Automated updates
- ❌ Slack/email notifications
- ❌ High maintenance, marginal value

**Cost/Benefit Ratio:**

- Practical approach: 90% of security benefit, 5% of effort
- Enterprise approach: 100% of security benefit, 100% of effort (40+ hours/month)

---

## Helper Script: Human-Readable Summary

**Problem**: JSON output from pip-audit is 6,000+ characters and hard to parse manually.

**Solution**: Use the included Python helper script at `tools/summarize_audit.py` to generate executive summaries.

**Features**:

- ✅ Windows-safe (no Unicode crashes, uses ASCII formatting)
- ✅ Groups vulnerabilities by package
- ✅ Shows actionable fix commands
- ✅ Handles skipped dependencies (torch, local packages)
- ✅ Severity breakdown and CVE summaries

### Usage

```bash
# Option 1: Pipe directly (fastest)
.venv/Scripts/pip-audit --format json | python tools/summarize_audit.py

# Option 2: Save JSON first (recommended for archiving)
.venv/Scripts/pip-audit --format json > audit_reports/2025-11-20-audit.json
python tools/summarize_audit.py audit_reports/2025-11-20-audit.json
```

### Example Output

```
======================================================================
                    DEPENDENCY AUDIT SUMMARY
======================================================================
Date: 2025-11-20 15:30:45
Total Packages: 189
Vulnerable Packages: 4
Total CVEs: 7

Severity Breakdown:
  - High: 6
  - Medium: 1

======================================================================
                    VULNERABILITIES FOUND
======================================================================

[PACKAGE] authlib (1.6.3)
----------------------------------------------------------------------
  [VULN]  GHSA-9ggr-2464-2j32
      Aliases: CVE-2025-59420
      Fix Available: 1.6.4
      Description: JWS verification bypass via critical headers...

[PACKAGE] pip (25.2)
----------------------------------------------------------------------
  [VULN]  GHSA-4xh5-x5gv-qwph
      Aliases: CVE-2025-8869
      Fix Available: 25.3
      Description: Tarfile path traversal vulnerability...

======================================================================
                    RECOMMENDED ACTIONS
======================================================================

[FIXES] Packages with available fixes:
   pip install --upgrade authlib==1.6.4
   pip install --upgrade pip==25.3
   pip install --upgrade starlette==0.49.1
   pip install --upgrade uv==0.9.6

[NEXT STEPS] Actions to take:
   1. Review CVE details at https://osv.dev/
   2. Test updates in isolated environment
   3. Run full test suite before deploying
   4. Update pyproject.toml with new version constraints
```

**Benefits**: Windows-safe ASCII formatting, clear priority indicators, actionable fix commands, human-readable CVE summaries.

---

## Troubleshooting

### Issue: pip-audit command not found

**Cause**: Tool not installed in current environment.

**Fix**:

```bash
# Install in your virtual environment
.venv/Scripts/pip install pip-audit  # Windows
# or: .venv/bin/pip install pip-audit  # Linux/Mac
```

### Issue: UnicodeEncodeError on Windows

**Cause**: Windows console (cp1252) doesn't support Unicode characters in CVE descriptions.

**Fix**: Always use `--format json` on Windows (see Phase 1 instructions above).

### Issue: Wrong environment audited

**Symptom**: Warning message about different virtual environment.

**Fix**:

```bash
# Option 1: Use virtual environment's pip-audit directly
.venv/Scripts/pip-audit --format json

# Option 2: Set environment variable
set PIPAPI_PYTHON_LOCATION=F:\path\to\.venv\Scripts\python.exe
pip-audit --format json
```

### Issue: pip-licenses command not found

**Cause**: Tool not installed.

**Fix**:

```bash
.venv/Scripts/pip install pip-licenses
```

### Issue: PyTorch import fails in verification script

**Cause**: Virtual environment not activated or PyTorch not installed.

**Fix**:

```bash
# Activate environment first
.venv/Scripts/activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac

# Verify PyTorch installed
pip list | grep torch
```

### Issue: Audit takes >10 seconds

**Expected**: Should complete in 1-2 seconds for ~200 packages.

**Possible Causes**:

- Slow internet connection (queries OSV database)
- Large number of dependencies (>500 packages)
- Network proxy/firewall blocking requests

**Fix**: Check network connectivity, consider running during off-peak hours.

---

Focus on **high-value, low-effort** security practices. Ignore security theater that doesn't match your actual risk profile.
