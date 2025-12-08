#!/usr/bin/env python3
"""
Webhook Receiver - FastAPI app to receive Lark webhooks and trigger processing
Deploy this to Railway/Render for production use
Supports OAuth for user_access_token (required for Minutes API)
"""

import os
import sys
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')

# Import processor and OAuth
from meeting_processor import process_meeting
from lark_oauth import (
    exchange_code_for_token,
    get_authorization_url,
    get_valid_access_token,
    REDIRECT_URI
)

# Create FastAPI app
app = FastAPI(
    title="Lark Meeting Webhook Receiver",
    description="Receives webhooks from Lark and processes meetings automatically",
    version="1.0.0"
)


class WebhookPayload(BaseModel):
    """Expected webhook payload structure"""
    meeting_url: str
    event_type: Optional[str] = "meeting_completed"
    timestamp: Optional[str] = None
    meeting_id: Optional[str] = None


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Lark Meeting Webhook Receiver",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check for Railway/Render"""
    return {"status": "healthy"}


# ==================== OAuth Endpoints ====================

@app.get("/oauth/authorize")
async def oauth_authorize():
    """
    Redirect to Lark OAuth authorization page

    Open this URL to start OAuth flow:
    https://your-app.onrender.com/oauth/authorize
    """
    auth_url = get_authorization_url()
    print(f"🔐 Redirecting to Lark OAuth: {auth_url}")
    return RedirectResponse(url=auth_url)


@app.get("/oauth/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    OAuth callback endpoint - Lark redirects here after user authorization

    Args:
        code: Authorization code from Lark
        state: State parameter for CSRF protection
        error: Error if authorization failed
    """
    print("=" * 70)
    print("📨 OAuth Callback Received")
    print("=" * 70)
    print(f"Code: {code[:20]}..." if code else "No code")
    print(f"State: {state}")
    print(f"Error: {error}")
    print("=" * 70)

    if error:
        return HTMLResponse(content=f"""
        <html>
        <head><title>OAuth Error</title></head>
        <body>
            <h1>❌ Authorization Failed</h1>
            <p>Error: {error}</p>
            <p><a href="/oauth/authorize">Try again</a></p>
        </body>
        </html>
        """, status_code=400)

    if not code:
        return HTMLResponse(content=f"""
        <html>
        <head><title>OAuth Error</title></head>
        <body>
            <h1>❌ No Authorization Code</h1>
            <p>No code parameter received from Lark.</p>
            <p><a href="/oauth/authorize">Try again</a></p>
        </body>
        </html>
        """, status_code=400)

    # Exchange code for token
    token_data = exchange_code_for_token(code, REDIRECT_URI)

    if token_data:
        access_token = token_data.get('access_token', '')
        expires_in = token_data.get('expires_in', 0)
        refresh_expires = token_data.get('refresh_token_expires_in', 0)

        return HTMLResponse(content=f"""
        <html>
        <head><title>OAuth Success</title></head>
        <body>
            <h1>✅ Authorization Successful!</h1>
            <p>Token has been saved. The system will auto-refresh when needed.</p>
            <hr>
            <h3>Token Details:</h3>
            <ul>
                <li><strong>Access Token:</strong> {access_token[:30]}...</li>
                <li><strong>Expires In:</strong> {expires_in} seconds ({expires_in // 60} minutes)</li>
                <li><strong>Refresh Token Expires In:</strong> {refresh_expires} seconds ({refresh_expires // 3600} hours)</li>
            </ul>
            <hr>
            <p>You can now close this page. Webhooks will use this token automatically.</p>
            <p><a href="/oauth/status">Check Token Status</a></p>
        </body>
        </html>
        """)
    else:
        return HTMLResponse(content=f"""
        <html>
        <head><title>OAuth Error</title></head>
        <body>
            <h1>❌ Token Exchange Failed</h1>
            <p>Could not exchange authorization code for token.</p>
            <p>Please check the server logs for details.</p>
            <p><a href="/oauth/authorize">Try again</a></p>
        </body>
        </html>
        """, status_code=500)


@app.get("/oauth/status")
async def oauth_status():
    """
    Check current OAuth token status
    """
    token = get_valid_access_token()

    if token:
        return {
            "status": "valid",
            "message": "Access token is valid and ready to use",
            "token_preview": f"{token[:30]}..."
        }
    else:
        auth_url = get_authorization_url()
        return {
            "status": "invalid",
            "message": "No valid token. Authorization required.",
            "authorize_url": auth_url
        }


@app.post("/webhook/lark-meeting")
async def lark_meeting_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Main webhook endpoint to receive Lark webhooks

    Handles:
    1. URL Verification Challenge from Lark
    2. Event notifications (meeting completed, etc.)
    """
    body = await request.json()

    print("=" * 70)
    print("📨 WEBHOOK RECEIVED")
    print("=" * 70)
    print(f"Body: {body}")
    print("=" * 70)

    # Handle Lark URL Verification Challenge
    # Lark sends: {"challenge": "xxx", "token": "xxx", "type": "url_verification"}
    if body.get("type") == "url_verification" or "challenge" in body:
        challenge = body.get("challenge", "")
        print(f"✅ URL Verification - Returning challenge: {challenge}")
        return {"challenge": challenge}

    # Handle event callback
    # Extract meeting URL from various possible payload formats
    meeting_url = None

    # Format 1: Direct meeting_url field
    if "meeting_url" in body:
        meeting_url = body["meeting_url"]

    # Format 2: Nested in event
    elif "event" in body:
        event = body["event"]
        meeting_url = event.get("meeting_url") or event.get("url")

    # Format 3: Custom payload with url
    elif "url" in body:
        meeting_url = body["url"]

    if not meeting_url:
        print("⚠️ No meeting URL found in payload, acknowledging receipt")
        return {"status": "received", "message": "No meeting URL to process"}

    # Validate meeting URL
    if "larksuite.com/minutes/" not in meeting_url and "feishu.cn/minutes/" not in meeting_url:
        print(f"⚠️ Invalid meeting URL format: {meeting_url}")
        return {"status": "received", "message": "Invalid meeting URL format"}

    print(f"🚀 Processing meeting: {meeting_url}")

    # Trigger processing in background (non-blocking)
    background_tasks.add_task(process_meeting, meeting_url)

    # Return immediate response to Lark
    return {
        "status": "accepted",
        "message": "Meeting processing started in background",
        "meeting_url": meeting_url
    }


@app.post("/webhook/test")
async def test_webhook(request: Request):
    """
    Test endpoint to see raw webhook payload from Lark

    Useful for debugging what Lark actually sends
    """
    body = await request.json()
    print("🔍 Test webhook received:")
    print(body)

    return {
        "status": "received",
        "payload": body
    }


@app.post("/process")
async def manual_process(
    meeting_url: str,
    background_tasks: BackgroundTasks
):
    """
    Manual processing endpoint (for testing without webhook)

    Usage: POST /process?meeting_url=https://...
    """
    print(f"🚀 Manual processing triggered for: {meeting_url}")

    # Trigger processing in background
    background_tasks.add_task(process_meeting, meeting_url)

    return {
        "status": "processing_started",
        "meeting_url": meeting_url
    }


# For local development
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))

    print("=" * 70)
    print("🚀 Starting Lark Meeting Webhook Receiver")
    print("=" * 70)
    print(f"Port: {port}")
    print(f"Webhook URL: http://localhost:{port}/webhook/lark-meeting")
    print(f"Test URL: http://localhost:{port}/webhook/test")
    print(f"Manual process URL: http://localhost:{port}/process")
    print("=" * 70)

    uvicorn.run(
        "webhook_receiver:app",
        host="0.0.0.0",
        port=port,
        reload=True  # Auto-reload on code changes (dev only)
    )
