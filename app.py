#!/usr/bin/env python3
"""
NetDoctor Web Dashboard
Zero third-party dependencies – uses only http.server + standard library.
"""

from __future__ import annotations

import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Optional

# Add parent directory so we can import NetDoctor modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from diagnostics import full_diagnosis
from scoring import calculate_health_score
from diagnosis import generate_advice

PORT = 8080
TEMPLATES = Path(__file__).parent / "templates"
STATIC = Path(__file__).parent / "static"


def build_result_html(result: dict, advice: list) -> str:
    """Build the result section HTML."""
    health = result["health"]
    grade = health.get("grade", "F")
    score = health.get("score", 0)
    label = health.get("label", "")

    rows = ""
    for check in result["checks"]:
        status_class = "status-pass" if check["success"] else "status-fail"
        status_icon = "✓" if check["success"] else "✗"
        latency = f"{check['latency_ms']} ms" if check.get("latency_ms") is not None else "-"
        rows += f"""
        <tr>
          <td class="{status_class}">{status_icon}</td>
          <td>{check['name']}</td>
          <td>{check['detail']}</td>
          <td>{latency}</td>
        </tr>
        """

    advice_html = ""
    if advice:
        items = "".join(f"<li>{item.lstrip('• ').strip()}</li>" for item in advice)
        advice_html = f"""
        <h3 style="margin-top: 1.5rem;">Advice</h3>
        <ul class="advice">
          {items}
        </ul>
        """

    return f"""
    <div class="card">
      <div class="score grade-{grade}">
        {score}/100
        <span style="font-size: 1.2rem;">({grade} – {label})</span>
      </div>
      <p style="margin-top: 0.5rem; color: #94a3b8;">Target: <strong>{result['target']}</strong></p>

      <table>
        <thead>
          <tr>
            <th>Status</th>
            <th>Check</th>
            <th>Detail</th>
            <th>Latency</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>

      {advice_html}
    </div>
    """


def render_page(target: Optional[str] = None, result: Optional[dict] = None, advice: Optional[list] = None) -> str:
    html = (TEMPLATES / "dashboard.html").read_text(encoding="utf-8")

    # Fill target value
    html = html.replace("TARGET_VALUE", target or "")

    # Fill result section
    if result:
        result_html = build_result_html(result, advice or [])
        html = html.replace("RESULT_SECTION", result_html)
    else:
        html = html.replace("RESULT_SECTION", "")

    return html


class NetDoctorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Serve static files
        if path.startswith("/static/"):
            relative_path = path[len("/static/"):].lstrip("/")
            file_path = STATIC / relative_path

            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                if file_path.suffix == ".css":
                    self.send_header("Content-Type", "text/css; charset=utf-8")
                self.end_headers()
                self.wfile.write(file_path.read_bytes())
                return
            self.send_error(404)
            return

        # Dashboard
        if path == "/" or path == "":
            target = query.get("target", [None])[0]
            result = None
            advice = None

            if target:
                try:
                    checks = full_diagnosis(target)
                    health = calculate_health_score(checks)
                    result = {
                        "target": target,
                        "health": health,
                        "checks": [
                            {
                                "name": r.name,
                                "success": r.success,
                                "detail": r.detail,
                                "latency_ms": r.latency_ms,
                                "diagnosis": r.diagnosis,
                            }
                            for r in checks
                        ],
                    }
                    advice = generate_advice(checks)
                except Exception as e:
                    result = {
                        "target": target,
                        "health": {"score": 0, "grade": "F", "label": "Error"},
                        "checks": [],
                    }
                    advice = [f"Error running diagnosis: {e}"]

            html = render_page(target=target, result=result, advice=advice)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        self.send_error(404)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")


def main():
    server = HTTPServer(("", PORT), NetDoctorHandler)
    print(f"🩺 NetDoctor Dashboard running at: http://localhost:{PORT}")
    print("Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()