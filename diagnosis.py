#!/usr/bin/env python3
"""
NetDoctor – Intelligent Fault Classification & Advice
Pure standard library.
"""

from __future__ import annotations
from typing import List, Dict
from diagnostics import CheckResult


def classify_issues(results: List[CheckResult]) -> Dict[str, List[str]]:
    """
    Group failed checks into categories for clearer reporting.
    """
    categories = {
        "critical": [],
        "warning": [],
        "info": [],
    }

    for r in results:
        if r.success:
            continue

        entry = f"{r.name}: {r.diagnosis or r.detail}"
        severity = r.severity if r.severity in categories else "warning"
        categories[severity].append(entry)

    return categories


def generate_advice(results: List[CheckResult]) -> List[str]:
    """
    Generate human-friendly advice based on the results.
    """
    advice = []
    failed = {r.name: r for r in results if not r.success}
    succeeded = {r.name for r in results if r.success}

    # DNS problems
    if "DNS" in failed:
        advice.append(
            "• DNS resolution failed. Check the hostname spelling or try using a public DNS "
            "resolver (e.g. 8.8.8.8 or 1.1.1.1)."
        )

    # TLS / Certificate problems
    if "HTTPS/TLS" in failed:
        advice.append(
            "• TLS/Certificate issue detected. The certificate may be expired, self-signed, "
            "or the hostname does not match. This is a security risk."
        )

    # Web ports
    if "TCP:80" in failed and "TCP:443" in failed:
        advice.append(
            "• Both port 80 and 443 are unreachable. The web server may be down or firewalled."
        )
    elif "TCP:443" in failed and "TCP:80" in succeeded:
        advice.append(
            "• Port 443 (HTTPS) is closed but port 80 is open. The site may only support HTTP "
            "(not recommended)."
        )
    elif "TCP:80" in failed and "TCP:443" in succeeded:
        advice.append(
            "• Port 80 is closed but HTTPS works. This is normal and preferred (HTTPS-only)."
        )

    # SSH
    if "TCP:22" in failed:
        advice.append(
            "• Port 22 (SSH) is closed. This is completely normal for public websites."
        )
    elif "TCP:22" in succeeded:
        advice.append(
            "• Port 22 (SSH) is open. Make sure this is intentional and properly secured."
        )

    # DNS service
    if "UDP:53" in failed:
        advice.append(
            "• UDP/53 did not respond. This is expected — most websites do not run a public DNS server."
        )

    # HTTP status issues
    http_result = failed.get("HTTP")
    if http_result:
        advice.append(
            f"• HTTP check failed ({http_result.detail}). The server responded with an unexpected status."
        )

    # Everything looks good
    if not advice:
        advice.append("• All critical checks passed. The target appears healthy.")

    return advice


def print_diagnosis_report(results: List[CheckResult]) -> None:
    """
    Pretty-print a diagnosis summary (used when -v is passed).
    """
    categories = classify_issues(results)
    advice = generate_advice(results)

    print("\n  📋 Diagnosis Summary")
    print("  " + "─" * 50)

    if categories["critical"]:
        print("  🔴 Critical Issues:")
        for item in categories["critical"]:
            print(f"     • {item}")

    if categories["warning"]:
        print("  🟡 Warnings:")
        for item in categories["warning"]:
            print(f"     • {item}")

    if categories["info"]:
        print("  ℹ️  Informational:")
        for item in categories["info"]:
            print(f"     • {item}")

    print("\n  💡 Advice:")
    for line in advice:
        print(f"     {line}")