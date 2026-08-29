#!/usr/bin/env python3
"""
NetDoctor diagnostics – pure Python standard library.
"""

from __future__ import annotations

import concurrent.futures
import http.client
import socket
import ssl
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse


@dataclass
class CheckResult:
    name: str
    success: bool
    detail: str
    latency_ms: Optional[float] = None
    severity: str = "info"          # critical | warning | info
    diagnosis: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Individual checks
# ----------------------------------------------------------------------

def resolve_dns(host: str, timeout: float = 3.0) -> CheckResult:
    start = time.perf_counter()
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        addrs = sorted({info[4][0] for info in infos})
        latency = (time.perf_counter() - start) * 1000

        ipv4 = [a for a in addrs if ":" not in a]
        ipv6 = [a for a in addrs if ":" in a]

        detail_parts = []
        if ipv4:
            detail_parts.append(f"IPv4: {', '.join(ipv4)}")
        if ipv6:
            detail_parts.append(f"IPv6: {', '.join(ipv6)}")

        return CheckResult(
            name="DNS",
            success=True,
            detail=" | ".join(detail_parts),
            latency_ms=round(latency, 1),
            severity="info",
            diagnosis="DNS resolution successful",
            extra={"addresses": addrs, "ipv4": ipv4, "ipv6": ipv6},
        )
    except socket.gaierror as e:
        return CheckResult(
            name="DNS",
            success=False,
            detail=str(e),
            severity="critical",
            diagnosis="Hostname could not be resolved. Check spelling or DNS server.",
        )
    except Exception as e:
        return CheckResult(
            name="DNS",
            success=False,
            detail=str(e),
            severity="critical",
            diagnosis="Unexpected DNS error",
        )


def tcp_connect(host: str, port: int, timeout: float = 3.0) -> CheckResult:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            latency = (time.perf_counter() - start) * 1000
            peer = sock.getpeername()
            return CheckResult(
                name=f"TCP:{port}",
                success=True,
                detail=f"Connected → {peer[0]}:{peer[1]}",
                latency_ms=round(latency, 1),
                severity="info",
                diagnosis=f"Port {port} is open and accepting connections",
            )
    except socket.timeout:
        return CheckResult(
            name=f"TCP:{port}",
            success=False,
            detail="Timeout",
            severity="warning",
            diagnosis=f"Port {port} filtered or host unreachable (timeout)",
        )
    except ConnectionRefusedError:
        return CheckResult(
            name=f"TCP:{port}",
            success=False,
            detail="Connection refused",
            severity="warning",
            diagnosis=f"Port {port} is closed (actively refused)",
        )
    except OSError as e:
        return CheckResult(
            name=f"TCP:{port}",
            success=False,
            detail=str(e),
            severity="warning",
            diagnosis=f"Network error on port {port}",
        )


def udp_dns_check(host: str, timeout: float = 2.0) -> CheckResult:
    """
    Real DNS check over UDP/53.
    We send a minimal DNS query and see if we get any response.
    """
    # Minimal DNS query for "example.com" A record (just to elicit a response)
    # This is a raw DNS packet – pure stdlib, no dnspython needed.
    query = (
        b"\x12\x34"          # Transaction ID
        b"\x01\x00"          # Flags: standard query
        b"\x00\x01"          # Questions: 1
        b"\x00\x00"          # Answer RRs
        b"\x00\x00"          # Authority RRs
        b"\x00\x00"          # Additional RRs
        b"\x07example\x03com\x00"  # Name: example.com
        b"\x00\x01"          # Type: A
        b"\x00\x01"          # Class: IN
    )

    start = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(query, (host, 53))
        data, _ = sock.recvfrom(512)
        sock.close()
        latency = (time.perf_counter() - start) * 1000

        return CheckResult(
            name="UDP:53",
            success=True,
            detail=f"DNS response received ({len(data)} bytes)",
            latency_ms=round(latency, 1),
            severity="info",
            diagnosis="Host is responding to DNS queries on UDP/53",
        )
    except socket.timeout:
        return CheckResult(
            name="UDP:53",
            success=False,
            detail="Timeout",
            severity="info",  # many public websites don't run DNS
            diagnosis="No DNS response (normal for most websites)",
        )
    except Exception as e:
        return CheckResult(
            name="UDP:53",
            success=False,
            detail=str(e),
            severity="info",
            diagnosis="UDP/53 not reachable (expected for most web hosts)",
        )


def https_tls_check(host: str, timeout: float = 5.0) -> CheckResult:
    """Full TLS handshake + certificate inspection."""
    start = time.perf_counter()
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                latency = (time.perf_counter() - start) * 1000
                cert = ssock.getpeercert()

                # Extract useful cert info
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer = dict(x[0] for x in cert.get("issuer", []))
                not_after = cert.get("notAfter", "unknown")

                return CheckResult(
                    name="HTTPS/TLS",
                    success=True,
                    detail=f"TLS OK | CN={subject.get('commonName', '?')} | Issuer={issuer.get('organizationName', issuer.get('commonName', '?'))}",
                    latency_ms=round(latency, 1),
                    severity="info",
                    diagnosis="Valid TLS certificate and successful handshake",
                    extra={
                        "cipher": ssock.cipher(),
                        "version": ssock.version(),
                        "not_after": not_after,
                        "subject": subject,
                        "issuer": issuer,
                    },
                )
    except ssl.SSLCertVerificationError as e:
        return CheckResult(
            name="HTTPS/TLS",
            success=False,
            detail=str(e),
            severity="critical",
            diagnosis="Certificate validation failed (expired, self-signed, or hostname mismatch)",
        )
    except ssl.SSLError as e:
        return CheckResult(
            name="HTTPS/TLS",
            success=False,
            detail=str(e),
            severity="critical",
            diagnosis="TLS handshake failed",
        )
    except socket.timeout:
        return CheckResult(
            name="HTTPS/TLS",
            success=False,
            detail="Timeout",
            severity="critical",
            diagnosis="Could not complete TLS handshake (timeout)",
        )
    except Exception as e:
        return CheckResult(
            name="HTTPS/TLS",
            success=False,
            detail=str(e),
            severity="critical",
            diagnosis="HTTPS/TLS connection failed",
        )


def http_head(url: str, timeout: float = 5.0) -> CheckResult:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    scheme = parsed.scheme or "https"
    host = parsed.hostname
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"

    if not host:
        return CheckResult(
            name="HTTP",
            success=False,
            detail="Invalid URL",
            severity="critical",
            diagnosis="Could not parse hostname",
        )

    start = time.perf_counter()
    try:
        if scheme == "https":
            context = ssl.create_default_context()
            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=context)
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("HEAD", path, headers={"User-Agent": "NetDoctor/2.0"})
        resp = conn.getresponse()
        latency = (time.perf_counter() - start) * 1000
        conn.close()

        ok = 200 <= resp.status < 400
        return CheckResult(
            name="HTTP",
            success=ok,
            detail=f"{resp.status} {resp.reason}",
            latency_ms=round(latency, 1),
            severity="info" if ok else "warning",
            diagnosis="HTTP endpoint responded" if ok else "Unexpected HTTP status",
            extra={"status": resp.status},
        )
    except Exception as e:
        return CheckResult(
            name="HTTP",
            success=False,
            detail=str(e),
            severity="warning",
            diagnosis="HTTP request failed",
        )


# ----------------------------------------------------------------------
# Orchestration + Health Score
# ----------------------------------------------------------------------

def full_diagnosis(
    target: str,
    ports: Optional[List[int]] = None,
    timeout: float = 3.0,
    check_http: bool = True,
    check_tls: bool = True,
) -> List[CheckResult]:

    results: List[CheckResult] = []

    # 1. DNS (critical)
    results.append(resolve_dns(target, timeout=timeout))

    # 2. UDP/53 – real DNS service check (informational for most sites)
    results.append(udp_dns_check(target, timeout=min(timeout, 2.0)))

    # 3. TCP ports
    if ports is None:
        ports = [80, 443, 22]          # 53 moved to UDP check

    def _tcp(p: int) -> CheckResult:
        return tcp_connect(target, p, timeout=timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        tcp_results = list(pool.map(_tcp, ports))
    results.extend(tcp_results)

    # 4. HTTPS / TLS (proper certificate check)
    if check_tls:
        results.append(https_tls_check(target, timeout=timeout))

    # 5. HTTP HEAD (optional)
    if check_http:
        results.append(http_head(f"https://{target}", timeout=timeout))

    return results


def calculate_health_score(results: List[CheckResult]) -> Dict[str, Any]:
    """
    Health score design:
    - DNS failure          → very heavy penalty
    - TLS / HTTPS failure  → heavy penalty
    - Port 80/443 failure  → medium penalty
    - Port 22 / UDP53      → almost no penalty (informational)
    """
    score = 100
    notes = []

    for r in results:
        if r.success:
            continue

        if r.name == "DNS":
            score -= 50
            notes.append("DNS resolution failed")
        elif r.name == "HTTPS/TLS":
            score -= 30
            notes.append("TLS/Certificate problem")
        elif r.name in ("TCP:80", "TCP:443", "HTTP"):
            score -= 15
            notes.append(f"{r.name} unreachable")
        elif r.name == "TCP:22":
            score -= 2          # almost irrelevant for public web hosts
            notes.append("SSH port closed (normal for most websites)")
        elif r.name == "UDP:53":
            score -= 1          # expected for non-DNS servers
            notes.append("No public DNS service (normal)")

    score = max(0, min(100, score))

    if score >= 90:
        grade = "A"
        label = "Excellent"
    elif score >= 75:
        grade = "B"
        label = "Good"
    elif score >= 60:
        grade = "C"
        label = "Fair"
    elif score >= 40:
        grade = "D"
        label = "Poor"
    else:
        grade = "F"
        label = "Critical"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "notes": notes,
    }