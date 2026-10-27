# Gmail OAuth 2.0 Setup Guide for PRISM Survey Delivery

This document explains how to configure Google OAuth 2.0 with refresh token support for PRISM transactional survey email delivery.

---

## 1. Overview & Architecture

PRISM supports 5 mail delivery providers via `prism_core.mail.send()`:
1. **Gmail OAuth 2.0 REST API** (`MAIL_PROVIDER="gmail"`) — Recommended for Google Workspace and Gmail accounts using app-level OAuth with refresh token.
2. **SMTP Relay / Gmail App Password** (`MAIL_PROVIDER="smtp"`) — Explicitly configured alternative for standard SMTP.
3. **Resend REST API** (`MAIL_PROVIDER="resend"`).
4. **Postmark REST API** (`MAIL_PROVIDER="postmark"`).
5. **Simulated Outbox** (`MAIL_PROVIDER="simulated"`) — **Default in development/testing.** Safely logs rendered HTML to `email_outbox` with status `"simulated"` and provides `/v1/email/outbox/{id}/preview` without sending live emails.

---

## 2. Google Cloud Console Setup

### Step 1: Create or Select a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `prism-quality-intelligence`) or select an existing one.

### Step 2: Enable the Gmail API
1. In the navigation menu, go to **APIs & Services &rarr; Library**.
2. Search for **Gmail API** and click **Enable**.

### Step 3: Configure the OAuth Consent Screen
1. Go to **APIs & Services &rarr; OAuth consent screen**.
2. Select **Internal** (if using Google Workspace organization) or **External** (for personal Gmail test accounts).
3. Fill in App Name (e.g. `PRISM Quality Intelligence`) and Developer Contact Email.
4. Under **Scopes**, click **Add or Remove Scopes** and add:
   - `https://www.googleapis.com/auth/gmail.send` (Send emails on your behalf)
5. Save and continue. If external and in "Testing" status, add your test recipient email under **Test Users**.

### Step 4: Create OAuth 2.0 Credentials
1. Go to **APIs & Services &rarr; Credentials**.
2. Click **Create Credentials &rarr; OAuth client ID**.
3. Application type: Select **Web application** (or **Desktop app** for local CLI generation).
4. Under **Authorized redirect URIs**, add:
   - `https://developers.google.com/oauthplayground` (convenient for generating refresh tokens)
   - `http://localhost:8000/oauth2callback` (if using custom redirect handler)
5. Click **Create**. Note your **Client ID** and **Client Secret**.

---

## 3. Generating the Refresh Token

Using the [Google OAuth 2.0 Playground](https://developers.google.com/oauthplayground):
1. Open OAuth 2.0 Playground.
2. Click the gear icon (**OAuth 2.0 configuration**) in the top right:
   - Check **Use your own OAuth credentials**.
   - Enter your **OAuth Client ID** and **OAuth Client Secret**.
3. In Step 1 (**Select & authorize APIs**), enter the scope:
   `https://www.googleapis.com/auth/gmail.send`
4. Click **Authorize APIs** and log in with the Gmail account from which emails will be sent.
5. In Step 2 (**Exchange authorization code for tokens**), click **Exchange authorization code for tokens**.
6. Copy the **Refresh token** value.

---

## 4. Environment Variables Configuration

In production, Render, or your local `.env`, set the following environment variables:

```bash
# Enable Gmail OAuth 2.0 Provider
MAIL_PROVIDER=gmail

# Google OAuth 2.0 Credentials
GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-your-client-secret
GMAIL_REFRESH_TOKEN=1//04your-long-lived-refresh-token

# Sender Addresses
GMAIL_USER_EMAIL=quality-team@yourdomain.com
MAIL_FROM="PRISM Engineering Diagnostic <quality-team@yourdomain.com>"
```

### Alternative: Gmail SMTP with App Password
If you prefer standard SMTP over Gmail OAuth 2.0:
```bash
MAIL_PROVIDER=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=quality-team@yourdomain.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_USE_TLS=true
MAIL_FROM=quality-team@yourdomain.com
```

### Development Default: Simulated Outbox
When no credentials or `MAIL_PROVIDER=simulated` is set:
- Messages are logged into `email_outbox` with `status: "simulated"`.
- The system never claims simulated messages were `"sent"` or `"delivered"`.
- Full HTML previews can be viewed at `/v1/email/outbox/{id}/preview`.

---

## 5. Security & Isolation Guarantees

1. **Credential Secrecy**: `gmail_client_id`, `gmail_client_secret`, and `gmail_refresh_token` are wrapped in Pydantic's `SecretStr`. They are never logged or exposed in API responses.
2. **Reviewer-Specific Token Scoping**: Each survey invite includes a cryptographically signed HMAC token (`/v1/survey/{token}`) tied strictly to that individual reviewer and tenant, expiring in 7 days.
3. **Consent Enforcement**: Emails are only dispatched if `RawReview.payload.contact.consent_followup == True` and the destination matches the recorded intake email.
4. **Idempotency**: Retries check `EmailOutbox` for matching `(to_hash, survey_id)` to avoid sending duplicate invitations.
5. **Outbox State Integrity**: State is set to `"sent"` only when the Gmail API returns HTTP 200 with an assigned message ID (`id`), never prematurely.
