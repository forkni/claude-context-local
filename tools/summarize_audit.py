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
import sys
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


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Read from file
        json_file = Path(sys.argv[1])
        if not json_file.exists():
            print(f"Error: File not found: {json_file}", file=sys.stderr)
            sys.exit(1)

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # Read from stdin
        try:
            data = json.load(sys.stdin)
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


if __name__ == "__main__":
    main()
