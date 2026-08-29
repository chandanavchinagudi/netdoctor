#!/usr/bin/env python3
"""
NetDoctor – Health Score Engine
Pure standard library.
"""

from __future__ import annotations
from typing import List, Dict, Any

# We import CheckResult only for type hints
from diagnostics import CheckResult


def calculate_health_score(results: List[CheckResult]) -> Dict[str, Any]:
    """
    Calculate a 0–100 health score based on check results.

    Scoring philosophy:
    - DNS failure          → very heavy penalty
    - TLS / HTTPS failure  → heavy penalty
    - Port 80 / 443 / HTTP → medium penalty
    - Port 22              → tiny penalty (normal for public websites)
    - UDP/53               → almost no penalty (most websites don't run DNS)
    """
    score = 100
    notes: List[str] = []

    for r in results:
        if r.success:
            continue

        name = r.name

        if name == "DNS":
            score -= 50
            notes.append("DNS resolution failed – critical")
        elif name in ("HTTPS/TLS", "TLS"):
            score -= 30
            notes.append("TLS/Certificate problem")
        elif name in ("TCP:80", "TCP:443", "HTTP"):
            score -= 15
            notes.append(f"{name} unreachable")
        elif name == "TCP:22":
            score -= 2
            notes.append("SSH port closed (normal for most public websites)")
        elif name in ("UDP:53", "TCP:53"):
            score -= 1
            notes.append("No public DNS service (expected for most websites)")
        else:
            # Any other failed check
            score -= 5
            notes.append(f"{name} failed")

    score = max(0, min(100, score))

    # Letter grade
    if score >= 90:
        grade, label = "A", "Excellent"
    elif score >= 75:
        grade, label = "B", "Good"
    elif score >= 60:
        grade, label = "C", "Fair"
    elif score >= 40:
        grade, label = "D", "Poor"
    else:
        grade, label = "F", "Critical"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "notes": notes,
    }