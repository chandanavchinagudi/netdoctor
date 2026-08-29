#!/usr/bin/env python3
"""
NetDoctor v2 – Zero-dependency Network Diagnostic CLI
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from diagnostics import full_diagnosis, CheckResult
from scoring import calculate_health_score
from diagnosis import generate_advice, print_diagnosis_report
from history import save_result, list_history
from reports.report_generator import save_report


def color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def print_result(r: CheckResult, verbose: bool = False) -> None:
    if r.success:
        status = color("✓", "32")
    else:
        status = color("✗", "31") if r.severity == "critical" else color("!", "33")

    latency = f"  ({r.latency_ms:.1f} ms)" if r.latency_ms is not None else ""
    print(f"  {status}  {r.name:<12} {r.detail}{latency}")

    if verbose and r.diagnosis:
        print(f"       → {r.diagnosis}")


def results_to_dict(results: List[CheckResult], health: dict, target: str) -> dict:
    return {
        "target": target,
        "health": health,
        "checks": [
            {
                "name": r.name,
                "success": r.success,
                "detail": r.detail,
                "latency_ms": r.latency_ms,
                "severity": r.severity,
                "diagnosis": r.diagnosis,
                "extra": r.extra,
            }
            for r in results
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NetDoctor – Concurrent network diagnostics (zero dependencies)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python netdoctor.py google.com
  python netdoctor.py github.com -v
  python netdoctor.py example.com --json
  python netdoctor.py cloudflare.com --save
  python netdoctor.py google.com --report html
  python netdoctor.py --history
        """,
    )

    parser.add_argument("target", nargs="?", help="Hostname or IP to diagnose")
    parser.add_argument("--ports", default="80,443,22", help="Comma-separated TCP ports")
    parser.add_argument("--timeout", type=float, default=3.0, help="Timeout in seconds")
    parser.add_argument("--no-http", action="store_true", help="Skip HTTP check")
    parser.add_argument("--no-tls", action="store_true", help="Skip TLS check")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed diagnosis")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", action="store_true", help="Save result to history")
    parser.add_argument("--report", choices=["text", "html"], help="Generate a report file")
    parser.add_argument("--history", action="store_true", help="Show recent history")

    args = parser.parse_args()

    # Show history and exit
    if args.history:
        entries = list_history(limit=15)
        if not entries:
            print("No history found.")
            return
        print(color("\n📜 Recent NetDoctor History", "1;36"))
        print("─" * 60)
        for e in entries:
            score = e.get("score", "?")
            grade = e.get("grade", "?")
            print(f"  {e['timestamp']}  |  {e['target']:<25}  |  {score}/100 ({grade})")
        print()
        return

    if not args.target:
        parser.print_help()
        sys.exit(1)

    # Parse ports
    try:
        ports: List[int] = [int(p.strip()) for p in args.ports.split(",") if p.strip()]
    except ValueError:
        print("Error: --ports must be comma-separated integers", file=sys.stderr)
        sys.exit(1)

    # Run diagnosis
    results = full_diagnosis(
        target=args.target,
        ports=ports,
        timeout=args.timeout,
        check_http=not args.no_http,
        check_tls=not args.no_tls,
    )

    health = calculate_health_score(results)
    payload = results_to_dict(results, health, args.target)

    # ---------- JSON output ----------
    if args.json:
        print(json.dumps(payload, indent=2))
        if args.save:
            path = save_result(args.target, payload)
            print(f"\nSaved to history: {path}", file=sys.stderr)
        return

    # ---------- Human output ----------
    print(color(f"\n🩺 NetDoctor diagnosing: {args.target}", "1;36"))
    print("─" * 60)

    for r in results:
        print_result(r, verbose=args.verbose)

    print("─" * 60)

    grade_color = {
        "A": "32", "B": "32", "C": "33", "D": "33", "F": "31"
    }.get(health["grade"], "0")

    print(
        f"  Health Score : {color(str(health['score']) + '/100', grade_color)}  "
        f"({color(health['grade'], grade_color)} – {health['label']})"
    )

    # Detailed diagnosis
    if args.verbose:
        print_diagnosis_report(results)

    # Save to history
    if args.save:
        path = save_result(args.target, payload)
        print(f"\n  💾 Saved to history: {path}")

    # Generate report
    if args.report:
        report_path = save_report(payload, format=args.report)
        print(f"  📄 Report saved: {report_path}")

    print()


if __name__ == "__main__":
    main()