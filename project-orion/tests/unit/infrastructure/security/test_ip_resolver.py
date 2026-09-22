"""Unit tests for ClientIpResolver (network security & trusted proxy resolution)."""

from __future__ import annotations

from unittest.mock import MagicMock

from starlette.datastructures import Headers

from libraries.infrastructure.security.ip_resolver import ClientIpResolver


def _create_mock_request(
    client_host: str | None = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a minimal Starlette/FastAPI request mock."""
    request = MagicMock()
    if client_host is not None:
        client = MagicMock()
        client.host = client_host
        request.client = client
    else:
        request.client = None

    request.headers = Headers(headers or {})
    return request


class TestClientIpResolver:
    """Test suite for trusted proxy IP resolution and anti-spoofing."""

    def test_direct_socket_ipv4(self) -> None:
        """Direct connection without proxy returns client socket IP."""
        resolver = ClientIpResolver(trusted_proxies=("127.0.0.1", "::1"))
        req = _create_mock_request(client_host="198.51.100.10")
        assert resolver.resolve_client_ip(req) == "198.51.100.10"

    def test_direct_socket_ipv6(self) -> None:
        """Direct IPv6 connection returns normalized IPv6 address."""
        resolver = ClientIpResolver(trusted_proxies=("127.0.0.1", "::1"))
        req = _create_mock_request(client_host="2001:0db8:0000:0000:0000:0000:0000:0001")
        assert resolver.resolve_client_ip(req) == "2001:db8::1"

    def test_untrusted_proxy_ignores_spoofed_headers(self) -> None:
        """Untrusted client sending X-Forwarded-For cannot spoof IP."""
        resolver = ClientIpResolver(trusted_proxies=("127.0.0.1", "::1"))
        req = _create_mock_request(
            client_host="198.51.100.10",
            headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
        )
        # Since 198.51.100.10 is NOT trusted, headers are ignored
        assert resolver.resolve_client_ip(req) == "198.51.100.10"

    def test_trusted_proxy_single_upstream(self) -> None:
        """Trusted proxy with single upstream IP correctly extracts upstream IP."""
        resolver = ClientIpResolver(trusted_proxies=("127.0.0.1", "::1"))
        req = _create_mock_request(
            client_host="127.0.0.1",
            headers={"X-Forwarded-For": "203.0.113.195"},
        )
        assert resolver.resolve_client_ip(req) == "203.0.113.195"

    def test_trusted_proxy_chain_picks_rightmost_untrusted(self) -> None:
        """Multi-hop trusted proxy chain traverses right-to-left to find first untrusted."""
        resolver = ClientIpResolver(trusted_proxies=("127.0.0.1", "10.0.0.1"))
        req = _create_mock_request(
            client_host="127.0.0.1",
            # Traversal order: client.host (127.0.0.1, trusted) -> 10.0.0.1 (trusted) -> 198.51.100.42 (UNTRUSTED => client!)
            headers={"X-Forwarded-For": "spoofed.ip.attacker, 198.51.100.42, 10.0.0.1"},
        )
        assert resolver.resolve_client_ip(req) == "198.51.100.42"

    def test_cidr_trusted_proxies(self) -> None:
        """Subnet CIDR specifications in trusted_proxies are supported."""
        resolver = ClientIpResolver(trusted_proxies=("10.0.0.0/8", "172.16.0.0/12"))
        req = _create_mock_request(
            client_host="10.254.1.1",
            headers={"X-Forwarded-For": "203.0.113.50"},
        )
        assert resolver.resolve_client_ip(req) == "203.0.113.50"

    def test_malformed_ip_in_headers_falls_back_to_socket(self) -> None:
        """Malformed or non-IP strings in headers fall back safely to socket IP."""
        resolver = ClientIpResolver(trusted_proxies=("127.0.0.1",))
        req = _create_mock_request(
            client_host="127.0.0.1",
            headers={"X-Forwarded-For": "not-a-valid-ip, @#$%, <script>alert(1)</script>"},
        )
        assert resolver.resolve_client_ip(req) == "127.0.0.1"

    def test_missing_client_host_defaults_safely(self) -> None:
        """Missing request.client defaults safely to 127.0.0.1."""
        resolver = ClientIpResolver(trusted_proxies=())
        req = _create_mock_request(client_host=None)
        assert resolver.resolve_client_ip(req) == "127.0.0.1"
