from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from .config import get_settings


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str | None = None
    session_id: str | None = None


def _token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return request.cookies.get("goag_session")


def decode_supabase_token(token: str) -> Identity:
    settings = get_settings()

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc

    algorithm = header.get("alg")
    claims: dict[str, Any] | None = None

    if algorithm == "HS256" and settings.supabase_jwt_secret:
        try:
            claims = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=settings.supabase_jwt_audience,
            )
        except jwt.PyJWTError:
            # Some projects have migrated from the legacy JWT secret to signing keys.
            # The Auth-server fallback below verifies the token without trusting its claims.
            claims = None
    elif algorithm in {"ES256", "RS256", "EdDSA"}:
        try:
            signing_key = PyJWKClient(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[algorithm],
                audience=settings.supabase_jwt_audience,
            )
        except (jwt.PyJWTError, OSError, ValueError):
            claims = None

    if claims is None:
        claims = _verify_with_auth_server(token, settings)

    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    subject = claims.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token has no subject")
    return Identity(subject=subject, email=claims.get("email"), session_id=claims.get("session_id"))


def _verify_with_auth_server(token: str, settings: Any) -> dict[str, Any] | None:
    """Verify a token through Supabase when local key verification is unavailable."""
    if not settings.supabase_url or not settings.supabase_anon_key:
        return None

    try:
        response = httpx.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
    except httpx.HTTPError:
        return None

    if response.status_code != 200:
        return None

    try:
        user = response.json()
        unverified_claims = jwt.decode(token, options={"verify_signature": False})
    except (ValueError, TypeError, jwt.PyJWTError):
        return None

    return {
        **unverified_claims,
        "sub": user.get("id") or unverified_claims.get("sub"),
        "email": user.get("email") or unverified_claims.get("email"),
    }


def get_identity(request: Request) -> Identity:
    token = _token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return decode_supabase_token(token)
