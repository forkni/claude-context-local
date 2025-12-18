#!/usr/bin/env python3
"""
Dependency Audit Summary Generator

Parses pip-audit JSON output and generates human-readable security summary.

Usage:
    .venv/Scripts/pip-audit --format json | python tools/summarize_audit.py
    # or:
    python tools/summarize_audit.py audit.json
"""

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


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Read from file
        json_file = Path(sys.argv[1])
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

    summary = parse_audit_json(data)
    print_summary(summary)

    # Add dependency tree analysis
    tree_data = get_dependency_tree_json()
    direct_deps = get_direct_dependencies()
    print_dependency_analysis(tree_data, direct_deps)


if __name__ == "__main__":
    main()
