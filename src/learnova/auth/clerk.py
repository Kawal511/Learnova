"""
Clerk session verification.

The React app sends Clerk's short-lived session JWT as
``Authorization: Bearer <token>``. We verify its RS256 signature against
Clerk's published JWKS rather than trusting a user id sent from the client —
otherwise anyone could read anyone else's decks by changing a header.

The JWKS is cached in memory; a key rotation is picked up when an unknown
``kid`` forces a refetch.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import jwt
import requests
from jwt.algorithms import RSAAlgorithm

from learnova.config import get_clerk_issuer, get_clerk_publishable_key
from learnova.logging_config import logger

_JWKS_CACHE: Dict[str, Any] = {"keys": {}, "fetched_at": 0.0, "issuer": None}
_JWKS_TTL_SECONDS = 3600


class AuthError(Exception):
    """Raised when a session token is missing, malformed, or fails verification."""


def _issuer() -> Optional[str]:
    """
    Clerk's issuer URL, e.g. https://settling-impala-61.clerk.accounts.dev

    Derivable from the publishable key: everything after ``pk_test_``/``pk_live_``
    is the base64 of "<frontend-api-host>$".
    """
    explicit = get_clerk_issuer()
    if explicit:
        return explicit.rstrip("/")

    key = get_clerk_publishable_key()
    if not key:
        return None

    import base64

    try:
        _, _, encoded = key.partition("_test_") if "_test_" in key else key.partition("_live_")
        if not encoded:
            return None
        padded = encoded + "=" * (-len(encoded) % 4)
        host = base64.b64decode(padded).decode("utf-8").rstrip("$")
        return f"https://{host}" if host else None
    except Exception as exc:
        logger.warning("could not derive Clerk issuer from publishable key: %s", exc)
        return None


def _fetch_jwks(force: bool = False) -> Dict[str, Any]:
    issuer = _issuer()
    if not issuer:
        raise AuthError("Clerk is not configured (no publishable key or issuer).")

    fresh = (time.time() - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL_SECONDS
    if not force and fresh and _JWKS_CACHE["keys"] and _JWKS_CACHE["issuer"] == issuer:
        return _JWKS_CACHE["keys"]

    try:
        response = requests.get(f"{issuer}/.well-known/jwks.json", timeout=10)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise AuthError(f"could not fetch Clerk JWKS: {exc}") from exc

    keys = {
        key["kid"]: RSAAlgorithm.from_jwk(key)
        for key in payload.get("keys", [])
        if key.get("kid")
    }
    _JWKS_CACHE.update(keys=keys, fetched_at=time.time(), issuer=issuer)
    logger.info("loaded %d Clerk signing key(s) from %s", len(keys), issuer)
    return keys


def verify_token(token: str) -> Dict[str, Any]:
    """Verify a Clerk session JWT and return its claims. Raises AuthError."""
    if not token:
        raise AuthError("missing session token")

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthError(f"malformed token: {exc}") from exc

    kid = header.get("kid")
    if not kid:
        raise AuthError("token header has no key id")

    keys = _fetch_jwks()
    key = keys.get(kid)
    if key is None:                       # unknown kid → keys may have rotated
        keys = _fetch_jwks(force=True)
        key = keys.get(kid)
    if key is None:
        raise AuthError("token signed with an unrecognised key")

    try:
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=_issuer(),
            # Clerk session tokens carry no `aud` claim by default.
            options={"verify_aud": False},
            leeway=10,
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("session expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthError(f"token verification failed: {exc}") from exc

    if not claims.get("sub"):
        raise AuthError("token has no subject claim")
    return claims


def user_id_from_header(authorization: Optional[str]) -> str:
    """Extract and verify the Clerk user id from an Authorization header."""
    if not authorization:
        raise AuthError("missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("expected 'Authorization: Bearer <token>'")
    return verify_token(token.strip())["sub"]


__all__ = ["AuthError", "verify_token", "user_id_from_header"]
