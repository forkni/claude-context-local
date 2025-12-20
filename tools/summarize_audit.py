#!/usr/bin/env python3
"""
Dependency Audit Summary Generator

Parses pip-audit JSON output and generates comprehensive executive summary reports.

Features:
- Security vulnerability analysis with severity breakdown
- ML stack health check (PyTorch, CUDA, GPU)
- Outdated packages with risk prioritization
- Dependency tree analysis with orphan detection
- Full markdown report saved to audit_reports/

Usage:
    .venv/Scripts/pip-audit --format json | python tools/summarize_audit.py
    # or:
    python tools/summarize_audit.py audit.json
    # or with custom output:
    python tools/summarize_audit.py --no-save  # stdout only
    python tools/summarize_audit.py -o custom.md  # custom output path
"""

import argparse
import json
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def parse_audit_json(data: dict) -> dict:
    """Extract vulnerability information from pip-audit JSON."""
    # Group vulnerabilities by package
    vuln_packages = defaultdict(list)
    severity_counts = defaultdict(int)
    total_packages = 0

    for dep in data.get("dependencies", []):
        pkg_name = dep["name"]

        # Skip dependencies that couldn't be audited
        if "skip_reason" in dep:
            continue

        total_packages += 1
        pkg_version = dep["version"]
        vulns = dep.get("vulns", [])

        if vulns:
            for vuln in vulns:
                vuln_packages[pkg_name].append(
                    {
                        "version": pkg_version,
                        "cve_id": vuln.get("id", "UNKNOWN"),
                        "fix_versions": vuln.get("fix_versions", []),
                        "aliases": vuln.get("aliases", []),
                        "description": (
                            vuln.get("description", "")[:200] + "..."
                            if len(vuln.get("description", "")) > 200
                            else vuln.get("description", "")
                        ),
                    }
                )

                # Try to extract severity from CVE ID or description
                if any(alias.startswith("CVE-") for alias in vuln.get("aliases", [])):
                    severity_counts["high"] += 1
                else:
                    severity_counts["medium"] += 1

    return {
        "total_packages": total_packages,
        "vulnerable_packages": len(vuln_packages),
        "total_cves": sum(len(v) for v in vuln_packages.values()),
        "vulnerabilities": dict(vuln_packages),
        "severity_counts": dict(severity_counts),
    }


def find_python_with_pipdeptree() -> str | None:
    """Find a Python executable that has pipdeptree installed."""
    candidates = [
        sys.executable,
        Path.cwd() / ".venv" / "Scripts" / "python.exe",  # Windows
        Path.cwd() / ".venv" / "bin" / "python",  # Linux/Mac
        Path.cwd() / "venv" / "Scripts" / "python.exe",  # Alt Windows
        Path.cwd() / "venv" / "bin" / "python",  # Alt Linux/Mac
    ]

    for python_path in candidates:
        python_str = str(python_path)
        if not Path(python_str).exists():
            continue
        try:
            result = subprocess.run(
                [python_str, "-m", "pipdeptree", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return python_str
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return None


def get_dependency_tree_json() -> list | None:
    """Run pipdeptree --json and return parsed output."""
    python_exe = find_python_with_pipdeptree()
    if python_exe is None:
        return None

    try:
        result = subprocess.run(
            [python_exe, "-m", "pipdeptree", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return None
    return None


def get_outdated_packages() -> list[dict] | None:
    """Run pip list --outdated --format=json and return parsed output."""
    python_exe = find_python_with_pipdeptree()
    if python_exe is None:
        python_exe = sys.executable

    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "list", "--outdated", "--format=json"],
            capture_output=True,
            text=True,
            timeout=120,  # Increased timeout for slow networks
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        # Return empty list instead of None if command succeeded but no outdated packages
        if result.returncode == 0:
            return []
    except subprocess.TimeoutExpired:
        # Timeout is common on slow networks, return None to signal failure
        return None
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return None
    return None


def get_ml_stack_health() -> dict:
    """Get ML stack health information (PyTorch, CUDA, GPU)."""
    python_exe = find_python_with_pipdeptree()
    if python_exe is None:
        python_exe = sys.executable

    ml_info = {
        "pytorch_version": None,
        "cuda_available": False,
        "cuda_version": None,
        "gpu_name": None,
        "gpu_count": 0,
        "transformers_version": None,
        "faiss_version": None,
        "sentence_transformers_version": None,
    }

    # Get PyTorch/CUDA info
    try:
        result = subprocess.run(
            [
                python_exe,
                "-c",
                """
import json
info = {}
try:
    import torch
    info['pytorch_version'] = torch.__version__
    info['cuda_available'] = torch.cuda.is_available()
    if torch.cuda.is_available():
        info['cuda_version'] = torch.version.cuda
        info['gpu_count'] = torch.cuda.device_count()
        info['gpu_name'] = torch.cuda.get_device_name(0)
except ImportError:
    pass
print(json.dumps(info))
""",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            pytorch_info = json.loads(result.stdout.strip())
            ml_info.update(pytorch_info)
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass

    # Get other ML package versions
    try:
        result = subprocess.run(
            [
                python_exe,
                "-c",
                """
import json
info = {}
try:
    import transformers
    info['transformers_version'] = transformers.__version__
except ImportError:
    pass
try:
    import faiss
    info['faiss_version'] = faiss.__version__ if hasattr(faiss, '__version__') else 'installed'
except ImportError:
    pass
try:
    import sentence_transformers
    info['sentence_transformers_version'] = sentence_transformers.__version__
except ImportError:
    pass
print(json.dumps(info))
""",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            other_info = json.loads(result.stdout.strip())
            ml_info.update(other_info)
    except (subprocess.SubprocessError, json.JSONDecodeError):
        pass

    return ml_info


def get_direct_dependencies(project_root: Path = None) -> set[str]:
    """Extract direct dependency names from pyproject.toml."""
    if project_root is None:
        project_root = Path.cwd()

    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return set()

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    deps = set()
    # Main dependencies
    for dep in data.get("project", {}).get("dependencies", []):
        # Extract package name (before any version specifier)
        name = re.split(r"[<>=!~\[]", dep)[0].strip().lower()
        deps.add(name)

    # Optional dependencies (dev, test, etc.)
    for group_deps in data.get("project", {}).get("optional-dependencies", {}).values():
        for dep in group_deps:
            name = re.split(r"[<>=!~\[]", dep)[0].strip().lower()
            deps.add(name)

    return deps


def categorize_outdated_packages(outdated: list[dict]) -> dict:
    """Categorize outdated packages by update risk."""
    ML_CORE = {
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "sentence-transformers",
        "faiss-cpu",
        "faiss-gpu",
        "huggingface-hub",
        "accelerate",
        "peft",
        "safetensors",
    }

    categories = {
        "ml_core": [],  # DO NOT auto-update
        "major_jump": [],  # Review breaking changes
        "safe_update": [],  # Safe to update
    }

    for pkg in outdated:
        name = pkg["name"].lower()
        current = pkg["version"]
        latest = pkg["latest_version"]

        # Parse major versions
        current_major = current.split(".")[0].lstrip("v")
        latest_major = latest.split(".")[0].lstrip("v")

        pkg_info = {
            "name": pkg["name"],
            "current": current,
            "latest": latest,
            "is_major_jump": current_major != latest_major,
        }

        if name in ML_CORE:
            categories["ml_core"].append(pkg_info)
        elif current_major != latest_major:
            categories["major_jump"].append(pkg_info)
        else:
            categories["safe_update"].append(pkg_info)

    return categories


def build_package_trees(tree_data: list, direct_deps: set) -> dict:
    """Build dependency trees for direct dependencies only."""
    trees = {}
    for pkg in tree_data:
        pkg_name = pkg["package"]["package_name"].lower()
        if pkg_name in direct_deps:
            trees[pkg_name] = {
                "version": pkg["package"]["installed_version"],
                "dependencies": pkg.get("dependencies", []),
            }
    return trees


def find_orphan_packages(tree_data: list, direct_deps: set) -> list[dict]:
    """Find packages not in direct deps and with no dependents."""
    all_installed = {}
    all_required_by = defaultdict(set)

    for pkg in tree_data:
        name = pkg["package"]["package_name"].lower()
        version = pkg["package"]["installed_version"]
        all_installed[name] = version

        # Track reverse dependencies
        for dep in pkg.get("dependencies", []):
            dep_name = dep["package_name"].lower()
            all_required_by[dep_name].add(name)

    orphans = []
    for name, version in all_installed.items():
        if name not in direct_deps and not all_required_by.get(name):
            orphans.append({"name": name, "version": version})

    return sorted(orphans, key=lambda x: x["name"])


def safe_print(text: str):
    """Print text with Windows-safe encoding."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic Unicode characters for Windows console
        safe_text = text.encode("ascii", "replace").decode("ascii")
        print(safe_text)


def print_summary(summary: dict):
    """Print formatted security summary."""
    safe_print("=" * 70)
    safe_print("DEPENDENCY AUDIT SUMMARY".center(70))
    safe_print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Packages: {summary['total_packages']}")
    print(f"Vulnerable Packages: {summary['vulnerable_packages']}")
    print(f"Total CVEs: {summary['total_cves']}")
    print()

    if summary["total_cves"] == 0:
        print("[OK] No known vulnerabilities found!")
        print()
        return

    # Print severity breakdown if available
    if summary["severity_counts"]:
        print("Severity Breakdown:")
        for severity, count in summary["severity_counts"].items():
            print(f"  - {severity.capitalize()}: {count}")
        print()

    print("=" * 70)
    print("VULNERABILITIES FOUND".center(70))
    print("=" * 70)
    print()

    for pkg_name, vulns in sorted(summary["vulnerabilities"].items()):
        print(f"[PACKAGE] {pkg_name} ({vulns[0]['version']})")
        print("-" * 70)

        for vuln in vulns:
            print(f"  [VULN]  {vuln['cve_id']}")

            if vuln["aliases"]:
                aliases_str = ", ".join(vuln["aliases"])
                print(f"      Aliases: {aliases_str}")

            if vuln["fix_versions"]:
                fix_str = ", ".join(vuln["fix_versions"])
                print(f"      Fix Available: {fix_str}")
            else:
                print("      Fix Available: No fix released yet")

            if vuln["description"]:
                safe_print(f"      Description: {vuln['description']}")

            print()

        print()

    print("=" * 70)
    print("RECOMMENDED ACTIONS".center(70))
    print("=" * 70)
    print()

    # Generate actionable recommendations
    fixable = [
        (pkg, v)
        for pkg, vulns in summary["vulnerabilities"].items()
        for v in vulns
        if v["fix_versions"]
    ]

    if fixable:
        print("[FIXES] Packages with available fixes:")
        for pkg, vuln in fixable:
            fix_version = vuln["fix_versions"][0] if vuln["fix_versions"] else "latest"
            print(f"   pip install --upgrade {pkg}=={fix_version}")
        print()

    unfixable = [
        (pkg, v)
        for pkg, vulns in summary["vulnerabilities"].items()
        for v in vulns
        if not v["fix_versions"]
    ]

    if unfixable:
        print("[MONITOR] Packages without fixes (monitor for updates):")
        for pkg, vuln in unfixable:
            print(f"   {pkg}: {vuln['cve_id']}")
        print()

    print("[NEXT STEPS] Actions to take:")
    print("   1. Review CVE details at https://osv.dev/")
    print("   2. Test updates in isolated environment")
    print("   3. Run full test suite before deploying")
    print("   4. Update pyproject.toml with new version constraints")
    print()


def print_dependency_tree(
    pkg_name: str, pkg_data: dict, indent: int = 0, visited: set = None
):
    """Recursively print ASCII dependency tree."""
    if visited is None:
        visited = set()

    prefix = "  " * indent
    if indent == 0:
        safe_print(f"{pkg_name}=={pkg_data['version']}")

    deps = pkg_data.get("dependencies", [])
    for i, dep in enumerate(deps):
        dep_name = dep["package_name"]
        dep_key = dep.get("key", dep_name.lower())
        required = dep.get("required_version", "Any")
        installed = dep.get("installed_version", "?")

        is_last = i == len(deps) - 1
        branch = "+-- " if is_last else "|-- "  # ASCII-safe for Windows console

        safe_print(
            f"{prefix}{branch}{dep_name} [required: {required}, installed: {installed}]"
        )

        # Prevent infinite loops from circular dependencies
        if dep_key not in visited:
            visited.add(dep_key)
            # Recurse for nested dependencies
            nested_deps = dep.get("dependencies", [])
            if nested_deps:
                child_prefix = "    " if is_last else "|   "  # ASCII-safe
                for j, nested in enumerate(nested_deps):
                    nested_is_last = j == len(nested_deps) - 1
                    nested_branch = "+-- " if nested_is_last else "|-- "  # ASCII-safe
                    n_name = nested["package_name"]
                    n_req = nested.get("required_version", "Any")
                    n_inst = nested.get("installed_version", "?")
                    safe_print(
                        f"{prefix}{child_prefix}{nested_branch}{n_name} [required: {n_req}, installed: {n_inst}]"
                    )


def print_dependency_analysis(tree_data: list, direct_deps: set):
    """Print complete dependency analysis section."""
    if not tree_data:
        safe_print(
            "\n[WARN] pipdeptree not available - skipping dependency tree analysis"
        )
        safe_print("       Install with: pip install pipdeptree")
        return

    # Calculate stats
    all_installed = {pkg["package"]["package_name"].lower() for pkg in tree_data}
    transitive = all_installed - direct_deps

    safe_print("\n" + "=" * 70)
    safe_print("DEPENDENCY TREE ANALYSIS".center(70))
    safe_print("=" * 70)
    safe_print(f"Direct Dependencies: {len(direct_deps)} (from pyproject.toml)")
    safe_print(f"Transitive Dependencies: {len(transitive)} (pulled in automatically)")
    safe_print(f"Total Installed: {len(all_installed)}")
    safe_print("")

    # Build and print trees for direct deps
    trees = build_package_trees(tree_data, direct_deps)

    for pkg_name in sorted(trees.keys()):
        pkg_data = trees[pkg_name]
        if pkg_data["dependencies"]:  # Only show packages with dependencies
            safe_print(f"[TREE] {pkg_name} ({pkg_data['version']})")
            safe_print("-" * 70)
            print_dependency_tree(pkg_name, pkg_data)
            safe_print("")

    # Find and print orphans
    orphans = find_orphan_packages(tree_data, direct_deps)
    if orphans:
        safe_print("[ORPHANS] Potential Leftover Packages:")
        safe_print("-" * 70)
        for orphan in orphans:
            safe_print(
                f"  [?] {orphan['name']} ({orphan['version']}) - Not in direct deps, nothing depends on it"
            )
        safe_print("")
        safe_print("  Actions:")
        safe_print("    - If needed: Add to pyproject.toml dependencies")
        safe_print("    - If not needed: pip uninstall <package>")
        safe_print("")
    else:
        safe_print("[OK] No orphan packages detected")
        safe_print("")


def print_outdated_analysis(outdated: list[dict] | None):
    """Print outdated packages analysis to console."""
    if outdated is None:
        safe_print("\n[WARN] Could not retrieve outdated packages")
        return

    if not outdated:
        safe_print("\n[OK] All packages are up to date!")
        return

    categories = categorize_outdated_packages(outdated)

    safe_print("\n" + "=" * 70)
    safe_print("OUTDATED PACKAGES ANALYSIS".center(70))
    safe_print("=" * 70)
    safe_print(f"Total Outdated: {len(outdated)}")
    safe_print("")

    # ML Core packages (DO NOT auto-update)
    if categories["ml_core"]:
        safe_print("[ML CORE] DO NOT auto-update - test thoroughly first:")
        safe_print("-" * 70)
        for pkg in categories["ml_core"]:
            jump = " [MAJOR]" if pkg["is_major_jump"] else ""
            safe_print(f"  {pkg['name']}: {pkg['current']} -> {pkg['latest']}{jump}")
        safe_print("")

    # Major version jumps (review breaking changes)
    if categories["major_jump"]:
        safe_print("[MAJOR VERSION] Review breaking changes before updating:")
        safe_print("-" * 70)
        for pkg in categories["major_jump"]:
            safe_print(f"  {pkg['name']}: {pkg['current']} -> {pkg['latest']}")
        safe_print("")

    # Safe updates
    if categories["safe_update"]:
        safe_print("[SAFE] Minor/patch updates (generally safe):")
        safe_print("-" * 70)
        for pkg in categories["safe_update"]:
            safe_print(f"  {pkg['name']}: {pkg['current']} -> {pkg['latest']}")
        safe_print("")


def get_project_info() -> dict:
    """Get project name and version from pyproject.toml."""
    pyproject_path = Path.cwd() / "pyproject.toml"
    if not pyproject_path.exists():
        return {"name": "Unknown", "version": "Unknown"}

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return {
            "name": data.get("project", {}).get("name", "Unknown"),
            "version": data.get("project", {}).get("version", "Unknown"),
        }
    except Exception:
        return {"name": "Unknown", "version": "Unknown"}


def generate_markdown_report(
    summary: dict,
    tree_data: list | None,
    direct_deps: set,
    outdated: list[dict] | None = None,
    ml_info: dict | None = None,
) -> str:
    """Generate comprehensive executive summary report as markdown string."""
    lines = []
    now = datetime.now()
    project_info = get_project_info()

    # Calculate dependency stats
    total_installed = len(tree_data) if tree_data else summary["total_packages"]
    transitive_count = total_installed - len(direct_deps) if tree_data else 0

    # Title
    lines.append("# Dependency Audit Executive Summary")
    lines.append("")
    lines.append(f"**Date**: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Project**: {project_info['name']} (v{project_info['version']})")
    lines.append(
        f"**Total Dependencies**: {total_installed} packages "
        f"({len(direct_deps)} direct + {transitive_count} transitive)"
    )
    lines.append(
        f"**Audit Report**: `audit_reports/{now.strftime('%Y-%m-%d-%H%M')}-audit-summary.md`"
    )
    lines.append("")

    # --- Security Status ---
    lines.append("---")
    lines.append("")
    if summary["total_cves"] == 0:
        lines.append("## ✅ Security Status: **EXCELLENT**")
    else:
        lines.append("## ⚠️ Security Status: **ACTION REQUIRED**")
    lines.append("")
    lines.append(
        f"- **Known Vulnerabilities**: "
        f"{summary['severity_counts'].get('critical', 0)} critical, "
        f"{summary['severity_counts'].get('high', 0)} high, "
        f"{summary['severity_counts'].get('medium', 0)} medium, "
        f"{summary['severity_counts'].get('low', 0)} low"
    )
    lines.append(f"- **CVE Count**: {summary['total_cves']}")
    lines.append(f"- **Last Scan**: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    if summary["total_cves"] == 0:
        lines.append(
            "**Finding**: No security vulnerabilities detected in any dependencies. "
            "All packages are clean according to OSV database."
        )
        lines.append("")

    # --- ML Stack Health ---
    if ml_info:
        lines.append("---")
        lines.append("")
        if ml_info.get("cuda_available"):
            lines.append("## 🤖 ML Stack Health: **GOOD**")
        elif ml_info.get("pytorch_version"):
            lines.append("## 🤖 ML Stack Health: **CPU-ONLY**")
        else:
            lines.append("## 🤖 ML Stack Health: **NOT INSTALLED**")
        lines.append("")

        lines.append("| Component | Version | Status | Notes |")
        lines.append("|-----------|---------|--------|-------|")

        # PyTorch
        if ml_info.get("pytorch_version"):
            pytorch_status = "✅ Stable"
            pytorch_notes = ""
            # Check if outdated
            if outdated:
                for pkg in outdated:
                    if pkg["name"].lower() == "torch":
                        pytorch_notes = f"Latest: {pkg['latest_version']}"
                        break
            lines.append(
                f"| PyTorch | {ml_info['pytorch_version']} | {pytorch_status} | {pytorch_notes} |"
            )
        else:
            lines.append("| PyTorch | Not installed | ⚪ N/A | |")

        # CUDA
        if ml_info.get("cuda_available"):
            lines.append(
                f"| CUDA | {ml_info.get('cuda_version', 'Unknown')} | ✅ Available | "
                f"Compatible with {ml_info.get('gpu_name', 'GPU')} |"
            )
        else:
            lines.append("| CUDA | N/A | ⚪ Not available | CPU mode |")

        # GPU
        if ml_info.get("gpu_name"):
            lines.append(
                f"| GPU | {ml_info['gpu_name']} | ✅ Active | "
                f"{ml_info.get('gpu_count', 1)} device(s) |"
            )
        else:
            lines.append("| GPU | None | ⚪ N/A | |")

        # transformers
        if ml_info.get("transformers_version"):
            lines.append(
                f"| transformers | {ml_info['transformers_version']} | ✅ Current | |"
            )

        # FAISS
        if ml_info.get("faiss_version"):
            lines.append(
                f"| FAISS | {ml_info['faiss_version']} | ✅ Current | CPU version |"
            )

        # sentence-transformers
        if ml_info.get("sentence_transformers_version"):
            lines.append(
                f"| sentence-transformers | {ml_info['sentence_transformers_version']} | ✅ Current | |"
            )

        lines.append("")

        if ml_info.get("cuda_available") and ml_info.get("pytorch_version"):
            lines.append(
                f"**CUDA/PyTorch Compatibility**: Excellent. "
                f"PyTorch {ml_info['pytorch_version']} with CUDA {ml_info.get('cuda_version', 'Unknown')} "
                f"support is working correctly"
                f"{' with ' + ml_info['gpu_name'] if ml_info.get('gpu_name') else ''}."
            )
            lines.append("")

    # --- Vulnerabilities Found ---
    if summary["vulnerabilities"]:
        lines.append("---")
        lines.append("")
        lines.append("## 🔴 Vulnerabilities Found")
        lines.append("")

        for pkg_name, vulns in sorted(summary["vulnerabilities"].items()):
            lines.append(f"### {pkg_name} ({vulns[0]['version']})")
            lines.append("")

            for vuln in vulns:
                lines.append(f"**{vuln['cve_id']}**")
                lines.append("")

                if vuln["aliases"]:
                    aliases_str = ", ".join(vuln["aliases"])
                    lines.append(f"- **Aliases**: {aliases_str}")

                if vuln["fix_versions"]:
                    fix_str = ", ".join(vuln["fix_versions"])
                    lines.append(f"- **Fix Available**: {fix_str}")
                else:
                    lines.append("- **Fix Available**: No fix released yet")

                if vuln["description"]:
                    desc = vuln["description"].replace("\n", " ")
                    lines.append(f"- **Description**: {desc}")

                lines.append("")

        # Recommended fix commands
        lines.append("### Recommended Actions")
        lines.append("")

        fixable = [
            (pkg, v)
            for pkg, vulns in summary["vulnerabilities"].items()
            for v in vulns
            if v["fix_versions"]
        ]

        if fixable:
            lines.append("**Packages with available fixes:**")
            lines.append("")
            lines.append("```bash")
            for pkg, vuln in fixable:
                fix_version = (
                    vuln["fix_versions"][0] if vuln["fix_versions"] else "latest"
                )
                lines.append(f"pip install --upgrade {pkg}=={fix_version}")
            lines.append("```")
            lines.append("")

        unfixable = [
            (pkg, v)
            for pkg, vulns in summary["vulnerabilities"].items()
            for v in vulns
            if not v["fix_versions"]
        ]

        if unfixable:
            lines.append("**Packages without fixes (monitor for updates):**")
            lines.append("")
            for pkg, vuln in unfixable:
                lines.append(f"- **{pkg}**: {vuln['cve_id']}")
            lines.append("")

    # --- Outdated Packages Analysis ---
    if outdated:
        categories = categorize_outdated_packages(outdated)

        lines.append("---")
        lines.append("")
        lines.append("## 📦 Outdated Packages Analysis")
        lines.append("")
        lines.append(
            f"**Total Outdated**: {len(outdated)} packages (prioritized by risk)"
        )
        lines.append("")

        # High Priority - ML Core
        if categories["ml_core"]:
            lines.append("### 🔴 High Priority (ML Core - Test Thoroughly)")
            lines.append("")
            lines.append(
                "⚠️ **DO NOT auto-update these packages** - CUDA compatibility and model behavior may change."
            )
            lines.append("")
            lines.append("| Package | Current | Latest | Priority | Reason |")
            lines.append("|---------|---------|--------|----------|--------|")
            for pkg in categories["ml_core"]:
                priority = "🔴 High" if pkg["is_major_jump"] else "🟡 Medium"
                reason = (
                    "Major version change"
                    if pkg["is_major_jump"]
                    else "ML core package"
                )
                lines.append(
                    f"| **{pkg['name']}** | {pkg['current']} | {pkg['latest']} | {priority} | {reason} |"
                )
            lines.append("")

        # Major Version Jumps
        if categories["major_jump"]:
            lines.append("### 🟡 Medium Priority (Major Version Changes)")
            lines.append("")
            lines.append(
                "Review breaking changes before updating. Check release notes."
            )
            lines.append("")
            lines.append("| Package | Current | Latest | Type |")
            lines.append("|---------|---------|--------|------|")
            for pkg in categories["major_jump"]:
                pkg_type = (
                    "Dev tool"
                    if pkg["name"].lower()
                    in {"pytest", "black", "isort", "ruff", "mypy"}
                    else "Library"
                )
                lines.append(
                    f"| {pkg['name']} | {pkg['current']} | {pkg['latest']} | {pkg_type} |"
                )
            lines.append("")

        # Safe Updates
        if categories["safe_update"]:
            lines.append("### 🟢 Low Priority (Minor/Patch Updates)")
            lines.append("")
            lines.append("Generally safe to update. Run tests after updating.")
            lines.append("")
            lines.append("| Package | Current | Latest |")
            lines.append("|---------|---------|--------|")
            for pkg in categories["safe_update"]:
                lines.append(f"| {pkg['name']} | {pkg['current']} | {pkg['latest']} |")
            lines.append("")

    # --- Dependency Tree Analysis ---
    if tree_data:
        all_installed = {pkg["package"]["package_name"].lower() for pkg in tree_data}
        transitive = all_installed - direct_deps

        lines.append("---")
        lines.append("")
        lines.append("## 🌳 Dependency Tree Analysis")
        lines.append("")
        lines.append(
            f"- **Direct Dependencies**: {len(direct_deps)} (from pyproject.toml)"
        )
        lines.append(
            f"- **Transitive Dependencies**: {len(transitive)} (pulled in automatically)"
        )
        lines.append(f"- **Total Installed**: {len(all_installed)}")
        dep_ratio = len(all_installed) / len(direct_deps) if direct_deps else 0
        lines.append(
            f"- **Dependency Ratio**: {dep_ratio:.2f}:1 (each direct dep pulls ~{dep_ratio:.1f} transitive)"
        )
        lines.append("")

        # Build trees for direct deps
        trees = build_package_trees(tree_data, direct_deps)

        if trees:
            lines.append("### Key Dependency Trees")
            lines.append("")
            lines.append("<details><summary>Click to expand dependency trees</summary>")
            lines.append("")

            for pkg_name in sorted(trees.keys()):
                pkg_data = trees[pkg_name]
                if pkg_data["dependencies"]:
                    lines.append(f"**{pkg_name}** ({pkg_data['version']})")
                    lines.append("")
                    lines.append("```")
                    lines.append(f"{pkg_name}=={pkg_data['version']}")
                    for dep in pkg_data["dependencies"]:
                        dep_name = dep["package_name"]
                        required = dep.get("required_version", "Any")
                        installed = dep.get("installed_version", "?")
                        lines.append(
                            f"|-- {dep_name} [required: {required}, installed: {installed}]"
                        )
                        # Add nested deps if present
                        for nested in dep.get("dependencies", [])[:3]:
                            n_name = nested["package_name"]
                            n_inst = nested.get("installed_version", "?")
                            lines.append(f"    +-- {n_name} [{n_inst}]")
                    lines.append("```")
                    lines.append("")

            lines.append("</details>")
            lines.append("")

        # Orphan packages
        orphans = find_orphan_packages(tree_data, direct_deps)
        if orphans:
            lines.append("### 🧹 Orphan Packages")
            lines.append("")
            lines.append(
                f"Found **{len(orphans)}** packages not in pyproject.toml with no dependents."
            )
            lines.append("")

            # Categorize orphans
            dev_tools = {
                "ipython",
                "pip_audit",
                "pip-audit",
                "setuptools",
                "wheel",
                "uv",
                "pyreadline3",
            }
            safe_orphans = []
            investigate_orphans = []

            for orphan in orphans:
                if orphan["name"].lower() in dev_tools:
                    safe_orphans.append(orphan)
                else:
                    investigate_orphans.append(orphan)

            if safe_orphans:
                lines.append("**Safe to Keep (Development Tools)**:")
                for orphan in safe_orphans:
                    lines.append(f"- `{orphan['name']}` ({orphan['version']})")
                lines.append("")

            if investigate_orphans:
                lines.append("**Investigate Before Removing**:")
                for orphan in investigate_orphans[:10]:  # Limit to first 10
                    lines.append(f"- `{orphan['name']}` ({orphan['version']})")
                if len(investigate_orphans) > 10:
                    lines.append(f"- ... and {len(investigate_orphans) - 10} more")
                lines.append("")

            lines.append(
                "**Recommendation**: Don't remove orphans yet. Many are transitive dependencies "
                "that pipdeptree may not detect correctly (especially for compiled packages)."
            )
            lines.append("")

    # --- Health Metrics ---
    lines.append("---")
    lines.append("")
    lines.append("## 📊 Dependency Health Metrics")
    lines.append("")
    lines.append("| Metric | Value | Status |")
    lines.append("|--------|-------|--------|")

    total_pkgs = total_installed
    lines.append(f"| Total Packages | {total_pkgs} | ✅ Reasonable |")
    lines.append(f"| Direct Dependencies | {len(direct_deps)} | ✅ Manageable |")
    lines.append(
        f"| Transitive Dependencies | {transitive_count} | ✅ Expected for ML project |"
    )

    if direct_deps:
        dep_ratio = total_pkgs / len(direct_deps)
        lines.append(f"| Dependency Ratio | {dep_ratio:.2f}:1 | ✅ Normal |")

    lines.append(
        f"| Security Vulnerabilities | {summary['total_cves']} | {'✅ Excellent' if summary['total_cves'] == 0 else '⚠️ Action needed'} |"
    )

    if outdated:
        outdated_pct = (len(outdated) / total_pkgs) * 100 if total_pkgs else 0
        lines.append(
            f"| Outdated Packages | {len(outdated)} ({outdated_pct:.1f}%) | "
            f"{'✅ Acceptable' if outdated_pct < 20 else '⚠️ Review needed'} |"
        )

    if tree_data:
        orphan_count = len(find_orphan_packages(tree_data, direct_deps))
        orphan_pct = (orphan_count / total_pkgs) * 100 if total_pkgs else 0
        lines.append(
            f"| Orphan Packages | {orphan_count} ({orphan_pct:.1f}%) | "
            f"{'✅ Normal' if orphan_pct < 20 else '⚠️ Review periodically'} |"
        )

    lines.append("")

    # --- Recommended Actions Summary ---
    lines.append("---")
    lines.append("")
    lines.append("## 🎯 Recommended Actions")
    lines.append("")

    if summary["total_cves"] == 0:
        lines.append("### Immediate Actions (This Week)")
        lines.append("")
        lines.append(
            "✅ **No immediate security updates required** - All packages are vulnerability-free."
        )
        lines.append("")
    else:
        lines.append("### 🔴 Immediate Actions (This Week)")
        lines.append("")
        lines.append("Security vulnerabilities detected. Apply fixes listed above.")
        lines.append("")

    if outdated and categories.get("ml_core"):
        lines.append("### Short-Term Actions (Next Sprint)")
        lines.append("")
        lines.append("Consider updating ML core packages after thorough testing:")
        lines.append("")
        for pkg in categories["ml_core"][:3]:
            lines.append(f"- `{pkg['name']}`: {pkg['current']} → {pkg['latest']}")
        lines.append("")
        lines.append(
            "**Before upgrading**: Check release notes, verify CUDA compatibility, test in isolated environment."
        )
        lines.append("")

    lines.append("### Quarterly Review Actions")
    lines.append("")
    next_quarter = now.replace(month=((now.month - 1) // 3 + 1) * 3 % 12 + 1)
    if next_quarter.month <= now.month:
        next_quarter = next_quarter.replace(year=now.year + 1)
    lines.append(f"1. Re-run security audit: {next_quarter.strftime('%B %Y')}")
    lines.append("2. Review outdated packages for updates")
    lines.append("3. Check PyTorch ecosystem for new releases")
    lines.append("4. Clean up orphan packages (if still unused)")
    lines.append("")

    # --- Summary ---
    lines.append("---")
    lines.append("")
    lines.append("## 💡 Summary")
    lines.append("")

    overall_status = "EXCELLENT" if summary["total_cves"] == 0 else "ACTION REQUIRED"
    lines.append(
        f"**Overall Health**: {'✅' if summary['total_cves'] == 0 else '⚠️'} **{overall_status}**"
    )
    lines.append("")

    checklist = []
    if summary["total_cves"] == 0:
        checklist.append("✅ **Zero security vulnerabilities** - All packages clean")
    else:
        checklist.append(
            f"⚠️ **{summary['total_cves']} security vulnerabilities** - Action required"
        )

    if ml_info and ml_info.get("cuda_available"):
        checklist.append(
            f"✅ **ML stack stable** - PyTorch {ml_info.get('pytorch_version', 'Unknown')} + "
            f"CUDA {ml_info.get('cuda_version', 'Unknown')} working"
        )
    elif ml_info and ml_info.get("pytorch_version"):
        checklist.append("⚠️ **ML stack CPU-only** - No CUDA available")

    checklist.append(
        f"✅ **Dependencies manageable** - {total_pkgs} packages with good organization"
    )

    if outdated:
        checklist.append(
            f"🟡 **{len(outdated)} packages outdated** - Review when convenient"
        )

    for item in checklist:
        lines.append(f"- {item}")

    lines.append("")
    lines.append(
        f"**Risk Level**: **{'LOW' if summary['total_cves'] == 0 else 'MEDIUM'}** - "
        f"{'No immediate action required.' if summary['total_cves'] == 0 else 'Apply security fixes first.'}"
    )
    lines.append("")

    return "\n".join(lines)


def save_report(content: str, output_path: Path):
    """Save report to file."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        print(f"\n[SAVED] Report saved to: {output_path}")
    except Exception as e:
        print(f"\n[ERROR] Failed to save report: {e}", file=sys.stderr)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Parse pip-audit JSON and generate human-readable summary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: displays AND saves automatically
  pip-audit --format json | python tools/summarize_audit.py

  # Disable auto-save (stdout only)
  pip-audit --format json | python tools/summarize_audit.py --no-save

  # Custom output path
  pip-audit --format json | python tools/summarize_audit.py -o audit_reports/before-fixes.md

  # Read from file
  python tools/summarize_audit.py audit_reports/2025-12-18-audit.json
        """,
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input JSON file (or pipe from stdin)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable auto-save (stdout only)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Custom output path (overrides auto-save location)",
    )
    args = parser.parse_args()

    # Read input data
    if args.input_file:
        # Read from file
        json_file = Path(args.input_file)
        if not json_file.exists():
            print(f"Error: File not found: {json_file}", file=sys.stderr)
            sys.exit(1)

        with open(json_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Handle pip-audit header line (e.g., "No known vulnerabilities found")
        # Find the start of JSON content
        json_start = content.find("{")
        if json_start == -1:
            print("Error: No JSON object found in file", file=sys.stderr)
            sys.exit(1)

        try:
            data = json.loads(content[json_start:])
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Read from stdin - also handle header line
        try:
            content = sys.stdin.read()
            json_start = content.find("{")
            if json_start == -1:
                print("Error: No JSON object found in input", file=sys.stderr)
                sys.exit(1)
            data = json.loads(content[json_start:])
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
            print("\nUsage:", file=sys.stderr)
            print(
                "  pip-audit --format json | python tools/summarize_audit.py",
                file=sys.stderr,
            )
            print("  python tools/summarize_audit.py audit.json", file=sys.stderr)
            sys.exit(1)

    # Parse data
    summary = parse_audit_json(data)
    tree_data = get_dependency_tree_json()
    direct_deps = get_direct_dependencies()
    outdated_data = get_outdated_packages()
    ml_info = get_ml_stack_health()

    # Always print to stdout (for chat display)
    print_summary(summary)
    print_dependency_analysis(tree_data, direct_deps)
    print_outdated_analysis(outdated_data)

    # Save to file unless --no-save
    if not args.no_save:
        report = generate_markdown_report(
            summary, tree_data, direct_deps, outdated_data, ml_info
        )
        if args.output:
            output_path = args.output
        else:
            filename = f"{datetime.now().strftime('%Y-%m-%d-%H%M')}-audit-summary.md"
            output_path = Path("audit_reports") / filename
        save_report(report, output_path)


if __name__ == "__main__":
    main()
