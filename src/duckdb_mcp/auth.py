"""Optional static bearer-token authentication for the HTTP transport.

A single pre-shared token (read from the ``MCP_AUTH_TOKEN`` environment
variable by the CLI) is compared against the incoming ``Authorization: Bearer``
token. This is transport-level access control, not per-user identity — every
caller that presents the token gets full access.
"""

from __future__ import annotations

import hmac

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

TOKEN_ENV = "MCP_AUTH_TOKEN"


class StaticTokenVerifier(TokenVerifier):
    """Verify bearer tokens against one pre-shared secret (constant-time)."""

    def __init__(self, token: str) -> None:
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token, self._token):
            return AccessToken(token=token, client_id="static", scopes=[])
        return None


def build_auth_settings(base_url: str) -> AuthSettings:
    """Minimal resource-server settings required to enable token verification.

    A static token has no real OAuth issuer, so both URLs point at the server's
    own base URL (``http://host:port``).
    """
    url = AnyHttpUrl(base_url)
    return AuthSettings(issuer_url=url, resource_server_url=url)
