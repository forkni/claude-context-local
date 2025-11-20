# Dependency Audit Reports

This directory contains vulnerability scan outputs from `pip-audit`.

## Purpose

Organized storage for security audit artifacts, keeping the project root clean and ensuring audit history is preserved for compliance and tracking.

## Contents

- `before-fixes-YYYY-MM-DD.json`: Baseline audits before applying security updates
- `after-fixes-YYYY-MM-DD.json`: Verification audits after applying fixes
- `quarterly-YYYY-MM-DD.json`: Regular quarterly security reviews
- `archive/`: Compressed historical reports for compliance (created as needed)

## Usage

### Generate New Audit

```bash
# Windows
.venv/Scripts/pip-audit --format json > audit_reports/%date:~-4,4%-%date:~-10,2%-%date:~-7,2%-audit.json

# Linux/macOS
pip-audit --format json > audit_reports/$(date +%Y-%m-%d)-audit.json
```

### Generate Human-Readable Summary

```bash
# Parse JSON audit report
python tools/summarize_audit.py audit_reports/2025-11-20-audit.json

# Or pipe directly from pip-audit
.venv/Scripts/pip-audit --format json | python tools/summarize_audit.py
```

### Baseline Workflow (Before/After Fixes)

```bash
# 1. Save baseline before fixes
.venv/Scripts/pip-audit --format json > audit_reports/before-fixes-2025-11-20.json

# 2. Apply security updates
pip install --upgrade package==fixed-version

# 3. Verify fixes applied
.venv/Scripts/pip-audit --format json > audit_reports/after-fixes-2025-11-20.json

# 4. Compare results
python tools/summarize_audit.py audit_reports/after-fixes-2025-11-20.json
```

## Cleanup Policy

- **Keep**: Current audit + previous 2 audits (for comparison)
- **Archive**: Reports older than 90 days (compress to `archive/`)
- **Delete**: Archived reports older than 1 year (unless compliance requires longer retention)

## Git Ignore

All `*.json` files in this directory are git-ignored to prevent committing sensitive dependency information. Only this README is tracked.
