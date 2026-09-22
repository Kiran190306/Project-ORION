"""Trusted-proxy-aware client IP resolution for Project ORION.

Prevents X-Forwarded-For spoofing by strictly verifying the immediate socket
connection against configured trusted proxies and CIDRs before evaluating headers.
Supports IPv4, IPv6, and malformed header sanitization.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request

logger = logging.getLogger("trading_engine.security.ip_resolver")

DEFAULT_TRUSTED_PROXIES = (
    "127.0.0.1",
    "::1",
)


class ClientIpResolver:
    """Resolves true client IP safely behind reverse proxies."""

    def __init__(self, trusted_proxies: tuple[str, ...] | list[str] | None = None) -> None:
        raw_proxies = trusted_proxies if trusted_proxies is not None else DEFAULT_TRUSTED_PROXIES
        self._trusted_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []

        for p in raw_proxies:
            p = p.strip()
            if not p:
                continue
            try:
                # Support both single IP ("127.0.0.1") and CIDR ("10.0.0.0/8")
                net = ipaddress.ip_network(p, strict=False)
                self._trusted_networks.append(net)
            except ValueError:
                logger.warning("Invalid trusted proxy IP or CIDR configured: %s", p)

    def is_trusted(self, ip_str: str) -> bool:
        """Check if an IP string belongs to configured trusted proxies."""
        try:
            ip_obj = ipaddress.ip_address(ip_str.strip())
            return any(ip_obj in net for net in self._trusted_networks)
        except ValueError:
            return False

    def resolve_client_ip(self, request: Request) -> str:
        """Resolve the authenticated or public client IP address safely.

        Rules:
        1. If direct socket client is not present, returns '127.0.0.1'.
        2. If direct socket client is not in trusted_proxies, returns direct client IP.
           Arbitrary X-Forwarded-For headers from untrusted callers are strictly ignored.
        3. If direct socket client is in trusted_proxies, parses X-Forwarded-For from
           right to left, returning the first non-trusted upstream IP address.
        4. Validates all resolved addresses using ipaddress.
        """
        if request.client is None or not request.client.host:
            return "127.0.0.1"

        direct_ip = request.client.host.strip()

        # Sanitize IPv6 zone index if present (e.g. fe80::1%eth0)
        if "%" in direct_ip:
            direct_ip = direct_ip.split("%")[0]

        # If direct caller is not trusted, do NOT inspect X-Forwarded-For
        if not self.is_trusted(direct_ip):
            try:
                ip_obj = ipaddress.ip_address(direct_ip)
                return str(ip_obj)
            except ValueError:
                return "127.0.0.1"

        # Direct caller is trusted: inspect X-Forwarded-For
        xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if not xff:
            try:
                return str(ipaddress.ip_address(direct_ip))
            except ValueError:
                return "127.0.0.1"

        # Split and clean chain: "client, proxy1, proxy2"
        raw_ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
        if not raw_ips:
            try:
                return str(ipaddress.ip_address(direct_ip))
            except ValueError:
                return "127.0.0.1"

        # Traverse right-to-left to find first untrusted origin IP
        for candidate in reversed(raw_ips):
            if "%" in candidate:
                candidate = candidate.split("%")[0]
            try:
                ip_obj = ipaddress.ip_address(candidate)
                if not any(ip_obj in net for net in self._trusted_networks):
                    return str(ip_obj)
            except ValueError:
                # Malformed IP header component: skip and keep scanning
                continue

        # If all IPs in chain are trusted, return the leftmost valid IP
        try:
            leftmost = raw_ips[0].split("%")[0]
            ipaddress.ip_address(leftmost)
            return leftmost
        except ValueError:
            return direct_ip
