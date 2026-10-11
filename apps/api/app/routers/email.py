from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from hashlib import sha256
from secrets import token_urlsafe
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import get_settings
from ..dependencies import current_db, require_permissions
from ..models import MailboxConnection, Membership
from ..schemas import (
    MailboxMessageListResponse,
    MailboxMessageSummary,
    MailboxOAuthStartResponse,
    MailboxSendRequest,
    MailboxSendResponse,
    MailboxStatusResponse,
    MailboxThreadMessage,
    MailboxThreadResponse,
)

router = APIRouter(prefix="/email", tags=["email"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GMAIL_SCOPES = (
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
)
OAUTH_STATE_TTL = timedelta(minutes=10)


def _frontend_redirect(*, error: str | None = None, connected: bool = False) -> RedirectResponse:
    settings = get_settings()
    query = urlencode({"email_error": error} if error else {"email_connected": "1" if connected else "0"})
    return RedirectResponse(url=f"{settings.goag_web_url.rstrip('/')}/dashboard?{query}", status_code=303)


def _fernet() -> Fernet:
    key = get_settings().goag_gmail_token_encryption_key
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOAG_GMAIL_TOKEN_ENCRYPTION_KEY is not configured",
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="Mailbox token encryption key is invalid") from exc


def _state_hash(state: str) -> str:
    return sha256(state.encode()).hexdigest()


@router.get("/status", response_model=MailboxStatusResponse)
def mailbox_status(
    membership: Membership = Depends(require_permissions("mailbox.read")),
    db: Session = Depends(current_db),
) -> MailboxStatusResponse:
    settings = get_settings()
    connection = db.scalar(select(MailboxConnection).where(MailboxConnection.company_id == membership.company_id))
    configured = settings.gmail_oauth_configured and bool(settings.goag_gmail_token_encryption_key)
    if not connection:
        return MailboxStatusResponse(
            configured=configured,
            connected=False,
            provider="google_gmail",
            mailbox_email=settings.goag_gmail_mailbox_address or None,
            message=(
                "Google Gmail OAuth is ready for configuration."
                if configured
                else "Google Gmail OAuth credentials and token encryption key are not configured yet."
            ),
        )

    return MailboxStatusResponse(
        configured=configured,
        connected=connection.status == "connected",
        provider=connection.provider,
        mailbox_email=connection.mailbox_email,
        message=(
            "Shared GOAG mailbox connected."
            if connection.status == "connected"
            else connection.last_error or "Shared GOAG mailbox is not connected."
        ),
    )


@router.get("/oauth/start", response_model=MailboxOAuthStartResponse)
def start_mailbox_oauth(
    membership: Membership = Depends(require_permissions("mailbox.manage")),
    db: Session = Depends(current_db),
) -> MailboxOAuthStartResponse:
    settings = get_settings()
    if not settings.gmail_oauth_configured:
        raise HTTPException(status_code=503, detail="Google Gmail OAuth credentials are not configured")
    _fernet()

    connection = db.scalar(select(MailboxConnection).where(MailboxConnection.company_id == membership.company_id))
    if not connection:
        connection = MailboxConnection(company_id=membership.company_id)
        db.add(connection)
        db.flush()

    state = token_urlsafe(32)
    connection.status = "oauth_pending"
    connection.oauth_state_hash = _state_hash(state)
    connection.oauth_state_expires_at = datetime.now(UTC) + OAUTH_STATE_TTL
    connection.connected_by_membership_id = membership.id
    connection.last_error = None
    record_audit(
        db,
        membership=membership,
        action="email.mailbox_oauth_started",
        entity_type="mailbox_connection",
        entity_id=connection.id,
        after={"provider": "google_gmail", "status": "oauth_pending"},
    )
    db.commit()

    params = {
        "client_id": settings.goag_gmail_client_id,
        "redirect_uri": settings.goag_gmail_redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return MailboxOAuthStartResponse(authorization_url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/oauth/callback", include_in_schema=False)
def mailbox_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(current_db),
) -> RedirectResponse:
    if error:
        return _frontend_redirect(error="google_oauth_denied")
    if not code or not state:
        return _frontend_redirect(error="google_oauth_missing_parameters")

    connection = db.scalar(
        select(MailboxConnection).where(
            MailboxConnection.oauth_state_hash == _state_hash(state),
            MailboxConnection.oauth_state_expires_at > datetime.now(UTC),
        )
    )
    if not connection or not connection.connected_by_membership_id:
        return _frontend_redirect(error="google_oauth_invalid_state")

    membership = db.get(Membership, connection.connected_by_membership_id)
    if not membership:
        return _frontend_redirect(error="google_oauth_invalid_state")

    settings = get_settings()
    try:
        with httpx.Client(timeout=15) as client:
            token_response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.goag_gmail_client_id,
                    "client_secret": settings.goag_gmail_client_secret,
                    "redirect_uri": settings.goag_gmail_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            if not access_token or not refresh_token:
                raise ValueError("Google did not return the required access and refresh tokens")

            userinfo_response = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_response.raise_for_status()
            mailbox_email = userinfo_response.json().get("email")
            if not mailbox_email:
                raise ValueError("Google did not return the mailbox email address")
    except (httpx.HTTPError, ValueError) as exc:
        connection.status = "error"
        connection.last_error = "Google mailbox connection failed. Check the OAuth configuration and consent."
        connection.oauth_state_hash = None
        connection.oauth_state_expires_at = None
        record_audit(
            db,
            membership=membership,
            action="email.mailbox_connection_failed",
            entity_type="mailbox_connection",
            entity_id=connection.id,
            reason=str(exc)[:500],
        )
        db.commit()
        return _frontend_redirect(error="google_oauth_failed")

    configured_mailbox = settings.goag_gmail_mailbox_address.strip().lower()
    if configured_mailbox and mailbox_email.lower() != configured_mailbox:
        connection.status = "error"
        connection.last_error = "The connected Google account does not match the configured GOAG mailbox."
        connection.oauth_state_hash = None
        connection.oauth_state_expires_at = None
        record_audit(
            db,
            membership=membership,
            action="email.mailbox_connection_rejected",
            entity_type="mailbox_connection",
            entity_id=connection.id,
            reason="Google account did not match the configured GOAG mailbox",
            after={"google_email": mailbox_email},
        )
        db.commit()
        return _frontend_redirect(error="google_mailbox_mismatch")

    connection.status = "connected"
    connection.mailbox_email = mailbox_email
    connection.refresh_token_ciphertext = _fernet().encrypt(refresh_token.encode()).decode()
    connection.scopes = token_data.get("scope", "").split() or list(GMAIL_SCOPES)
    connection.oauth_state_hash = None
    connection.oauth_state_expires_at = None
    connection.last_error = None
    record_audit(
        db,
        membership=membership,
        action="email.mailbox_connected",
        entity_type="mailbox_connection",
        entity_id=connection.id,
        after={"provider": "google_gmail", "mailbox_email": mailbox_email, "scopes": connection.scopes},
    )
    db.commit()
    return _frontend_redirect(connected=True)


def decrypt_refresh_token(connection: MailboxConnection) -> str:
    if not connection.refresh_token_ciphertext:
        raise HTTPException(status_code=503, detail="Shared GOAG mailbox is not connected")
    try:
        return _fernet().decrypt(connection.refresh_token_ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(status_code=500, detail="Stored mailbox token could not be decrypted") from exc


def _connected_mailbox(membership: Membership, db: Session) -> MailboxConnection:
    connection = db.scalar(
        select(MailboxConnection).where(
            MailboxConnection.company_id == membership.company_id,
            MailboxConnection.status == "connected",
        )
    )
    if not connection:
        raise HTTPException(status_code=503, detail="Shared GOAG mailbox is not connected")
    return connection


def _access_token(connection: MailboxConnection) -> str:
    settings = get_settings()
    try:
        with httpx.Client(timeout=20) as client:
            token_response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.goag_gmail_client_id,
                    "client_secret": settings.goag_gmail_client_secret,
                    "refresh_token": decrypt_refresh_token(connection),
                    "grant_type": "refresh_token",
                },
            )
            token_response.raise_for_status()
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise ValueError("Google did not return an access token")
            return access_token
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Unable to authenticate with the Gmail mailbox") from exc


def _gmail_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _header_values(payload: dict) -> dict[str, str]:
    return {
        header.get("name", "").lower(): header.get("value", "")
        for header in payload.get("headers", [])
        if header.get("name")
    }


def _gmail_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def _decode_gmail_body(data: str | None) -> str:
    if not data:
        return ""
    try:
        padded = data + "=" * (-len(data) % 4)
        return urlsafe_b64decode(padded.encode()).decode("utf-8", errors="replace")
    except (ValueError, UnicodeError):
        return ""


def _plain_text_body(payload: dict) -> str:
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        body = _decode_gmail_body(payload.get("body", {}).get("data"))
        if body:
            return body
    for part in payload.get("parts", []):
        body = _plain_text_body(part)
        if body:
            return body
    return _decode_gmail_body(payload.get("body", {}).get("data"))


def _message_summary(message: dict) -> MailboxMessageSummary:
    headers = _header_values(message.get("payload", {}))
    label_ids = message.get("labelIds", [])
    return MailboxMessageSummary(
        id=message["id"],
        thread_id=message.get("threadId"),
        sender=headers.get("from", "Unknown sender"),
        recipients=headers.get("to", ""),
        subject=headers.get("subject", "(no subject)"),
        snippet=message.get("snippet", ""),
        received_at=_gmail_timestamp(message.get("internalDate")),
        label_ids=label_ids,
        unread="UNREAD" in label_ids,
    )


def _thread_message(message: dict) -> MailboxThreadMessage:
    headers = _header_values(message.get("payload", {}))
    return MailboxThreadMessage(
        id=message["id"],
        thread_id=message.get("threadId"),
        sender=headers.get("from", "Unknown sender"),
        recipients=headers.get("to", ""),
        subject=headers.get("subject", "(no subject)"),
        body=_plain_text_body(message.get("payload", {})) or message.get("snippet", ""),
        sent_at=_gmail_timestamp(message.get("internalDate")),
        label_ids=message.get("labelIds", []),
    )


@router.get("/messages", response_model=MailboxMessageListResponse)
def list_mailbox_messages(
    q: str = "",
    page_token: str | None = None,
    max_results: int = 25,
    membership: Membership = Depends(require_permissions("mailbox.read")),
    db: Session = Depends(current_db),
) -> MailboxMessageListResponse:
    connection = _connected_mailbox(membership, db)
    access_token = _access_token(connection)
    params: dict[str, str | int] = {"userId": "me", "maxResults": min(max(max_results, 1), 50)}
    if q.strip():
        params["q"] = q.strip()
    if page_token:
        params["pageToken"] = page_token

    try:
        with httpx.Client(timeout=20) as client:
            list_response = client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers=_gmail_headers(access_token),
                params=params,
            )
            list_response.raise_for_status()
            listed = list_response.json()
            messages: list[MailboxMessageSummary] = []
            for message_ref in listed.get("messages", []):
                message_response = client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_ref['id']}",
                    headers=_gmail_headers(access_token),
                    params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject"]},
                )
                message_response.raise_for_status()
                messages.append(_message_summary(message_response.json()))
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Unable to load Gmail messages") from exc

    record_audit(
        db,
        membership=membership,
        action="email.inbox_listed",
        entity_type="gmail_mailbox",
        entity_id=str(connection.id),
        after={"query": q.strip(), "message_count": len(messages)},
    )
    db.commit()
    return MailboxMessageListResponse(messages=messages, next_page_token=listed.get("nextPageToken"))


@router.get("/threads/{thread_id}", response_model=MailboxThreadResponse)
def read_mailbox_thread(
    thread_id: str,
    membership: Membership = Depends(require_permissions("mailbox.read")),
    db: Session = Depends(current_db),
) -> MailboxThreadResponse:
    connection = _connected_mailbox(membership, db)
    access_token = _access_token(connection)
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
                headers=_gmail_headers(access_token),
                params={"format": "full"},
            )
            response.raise_for_status()
            thread = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Unable to load the Gmail thread") from exc

    thread_messages = [_thread_message(message) for message in thread.get("messages", [])]
    record_audit(
        db,
        membership=membership,
        action="email.thread_read",
        entity_type="gmail_thread",
        entity_id=thread_id,
        after={"message_count": len(thread_messages)},
    )
    db.commit()
    return MailboxThreadResponse(thread_id=thread_id, messages=thread_messages)


@router.post("/messages/send", response_model=MailboxSendResponse)
def send_mailbox_message(
    payload: MailboxSendRequest,
    membership: Membership = Depends(require_permissions("mailbox.send")),
    db: Session = Depends(current_db),
) -> MailboxSendResponse:
    connection = _connected_mailbox(membership, db)

    try:
        with httpx.Client(timeout=20) as client:
            access_token = _access_token(connection)

            message = EmailMessage()
            message["To"] = str(payload.to)
            message["Subject"] = payload.subject
            message.set_content(payload.body)
            raw_message = urlsafe_b64encode(message.as_bytes()).decode()
            send_response = client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"raw": raw_message},
            )
            send_response.raise_for_status()
            sent_data = send_response.json()
            message_id = sent_data.get("id")
            if not message_id:
                raise ValueError("Gmail did not return a message ID")
    except (httpx.HTTPError, ValueError) as exc:
        connection.last_error = "Gmail message send failed. The mailbox may need to be reconnected."
        reason = exc.response.text[:500] if isinstance(exc, httpx.HTTPStatusError) else str(exc)[:500]
        record_audit(
            db,
            membership=membership,
            action="email.message_send_failed",
            entity_type="gmail_message",
            entity_id="unknown",
            reason=reason,
            after={"to": str(payload.to), "subject": payload.subject},
        )
        db.commit()
        raise HTTPException(status_code=502, detail="Unable to send the Gmail message") from exc

    record_audit(
        db,
        membership=membership,
        action="email.message_sent",
        entity_type="gmail_message",
        entity_id=message_id,
        after={"to": str(payload.to), "subject": payload.subject, "mailbox_email": connection.mailbox_email},
    )
    db.commit()
    return MailboxSendResponse(message_id=message_id, thread_id=sent_data.get("threadId"))
