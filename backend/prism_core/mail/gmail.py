"""
prism_core/mail/gmail.py

Gmail OAuth 2.0 API Delivery Provider for PRISM:
- Obtains short-lived access tokens via OAuth 2.0 refresh token grant.
- Caches access tokens in-memory until expiration.
- Composes RFC 2822 MIME multipart messages and base64url-encodes them.
- Submits messages via Gmail REST API (users/me/messages/send).
- Implements robust error handling (invalid_grant, 429 rate limits, timeouts).
- Strictly prevents credential/token leakage in error messages and logs.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/send"

# In-memory access token cache: {cache_key: {"access_token": str, "expires_at": float}}
_token_cache: dict[str, dict[str, Any]] = {}


class GmailAuthError(Exception):
    """Raised when OAuth 2.0 token acquisition or refresh fails."""


class GmailDeliveryError(Exception):
    """Raised when Gmail REST API rejects or fails to send an email."""


def clear_gmail_token_cache() -> None:
    """Clear cached OAuth tokens (useful for testing and handling token invalidation)."""
    _token_cache.clear()


async def refresh_gmail_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    Exchanges a Gmail OAuth 2.0 refresh token for a short-lived access token.
    Caches valid tokens in memory until 60 seconds before expiration.
    Sanitizes errors to avoid exposing credentials or tokens.
    """
    if not (client_id and client_secret and refresh_token):
        raise GmailAuthError("Incomplete Gmail OAuth credentials: client_id, client_secret, or refresh_token is missing.")

    cache_key = hashlib.sha256(f"{client_id}:{refresh_token}".encode("utf-8")).hexdigest()
    now = time.time()
    cached = _token_cache.get(cache_key)
    if cached and cached.get("expires_at", 0) > now + 60:
        return cached["access_token"]

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }

    try:
        if client is not None:
            resp = await client.post(GOOGLE_TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        else:
            async with httpx.AsyncClient(timeout=10.0) as local_client:
                resp = await local_client.post(GOOGLE_TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    except httpx.TimeoutException:
        raise GmailAuthError("Gmail OAuth token refresh network timeout.")
    except Exception as e:
        raise GmailAuthError(f"Gmail OAuth token refresh network error: {e.__class__.__name__}")

    if resp.status_code != 200:
        try:
            err_data = resp.json()
            err_type = err_data.get("error", "token_refresh_failed")
            err_desc = err_data.get("error_description", f"HTTP {resp.status_code}")
        except Exception:
            err_type = f"http_{resp.status_code}"
            err_desc = "Non-JSON response from Google OAuth endpoint"
        raise GmailAuthError(f"Gmail OAuth token refresh failed: {err_type} ({err_desc})")

    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise GmailAuthError("Gmail OAuth token response did not contain an access_token.")

    expires_in = int(token_data.get("expires_in", 3600))
    _token_cache[cache_key] = {
        "access_token": access_token,
        "expires_at": now + expires_in,
    }
    return access_token


def build_raw_email(from_addr: str, to_addr: str, subject: str, html_body: str) -> str:
    """
    Constructs an RFC 2822 MIME multipart message and returns its urlsafe base64 string
    without padding, as expected by the Gmail API.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    plain_text = f"{subject}\n\nPlease view this email in an HTML-compatible client."
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw_bytes = msg.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode("utf-8").rstrip("=")


async def send_via_gmail_api(
    to_addr: str,
    from_addr: str,
    subject: str,
    html_body: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    user_id: str = "me",
    client: httpx.AsyncClient | None = None,
) -> str:
    """
    Sends an already-rendered email using the Google Gmail REST API.
    - Uses OAuth 2.0 with refresh token to acquire valid access token.
    - Posts base64url-encoded raw message to /gmail/v1/users/{userId}/messages/send.
    - Returns the Gmail provider message ID.
    - Raises GmailAuthError or GmailDeliveryError on failure.
    """
    access_token = await refresh_gmail_access_token(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        client=client,
    )

    raw_b64 = build_raw_email(from_addr=from_addr, to_addr=to_addr, subject=subject, html_body=html_body)
    url = GMAIL_SEND_URL.format(userId=user_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"raw": raw_b64}

    try:
        if client is not None:
            resp = await client.post(url, headers=headers, json=payload)
        else:
            async with httpx.AsyncClient(timeout=10.0) as local_client:
                resp = await local_client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException:
        raise GmailDeliveryError("Gmail API request timed out.")
    except Exception as e:
        raise GmailDeliveryError(f"Gmail API network error: {e.__class__.__name__}")

    if resp.status_code == 200:
        data = resp.json()
        msg_id = data.get("id")
        if not msg_id:
            raise GmailDeliveryError("Gmail API response missing message ID.")
        return str(msg_id)

    elif resp.status_code == 401:
        # Access token might have been invalidated; clear cache
        clear_gmail_token_cache()
        raise GmailAuthError("Gmail API unauthorized (HTTP 401): access token rejected or revoked.")

    elif resp.status_code == 429:
        raise GmailDeliveryError("Gmail API rate limit exceeded (HTTP 429).")

    else:
        try:
            err_json = resp.json()
            err_msg = err_json.get("error", {}).get("message", f"HTTP {resp.status_code}")
        except Exception:
            err_msg = f"HTTP {resp.status_code}"
        raise GmailDeliveryError(f"Gmail API delivery rejected ({resp.status_code}): {err_msg}")
