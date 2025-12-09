#!/usr/bin/env python3
"""
Webhook Receiver - FastAPI app to receive Lark webhooks and trigger processing
Deploy this to Railway/Render for production use
Uses session-based authentication for Minutes API
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

# Import processor and session module
from meeting_processor import process_meeting as _process_meeting
from lark_session import save_session, load_session
import traceback


def process_meeting_safe(meeting_url: str):
    """Wrapper to catch and log all errors from background task"""
    try:
        print(f"[BG Task] Starting processing for: {meeting_url}")
        result = _process_meeting(meeting_url)
        print(f"[BG Task] Completed with result: {result}")
        return result
    except Exception as e:
        print(f"[BG Task] ERROR: {str(e)}")
        print(f"[BG Task] Traceback:")
        traceback.print_exc()
        return False

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


# ==================== Session Management Endpoints ====================

@app.get("/session/status")
async def session_status():
    """
    Check current session status
    """
    session_data = load_session()

    if session_data:
        return {
            "status": "configured",
            "message": "Session cookies are configured",
            "has_sl_session": "sl_session" in session_data,
            "has_session": "session" in session_data
        }
    else:
        return {
            "status": "not_configured",
            "message": "Session cookies not configured. Please use /session/set to configure.",
            "setup_url": "/session/set"
        }


@app.get("/session/set")
async def session_set_form():
    """
    Show form to set session cookies
    """
    return HTMLResponse(content="""
    <html>
    <head>
        <title>Set Lark Session</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            h1 { color: #333; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            textarea { height: 100px; font-family: monospace; }
            button { background: #4CAF50; color: white; padding: 15px 30px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background: #45a049; }
            .instructions { background: #f5f5f5; padding: 15px; border-radius: 4px; margin-bottom: 20px; }
            code { background: #e0e0e0; padding: 2px 6px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <h1>🔐 Set Lark Session Cookies</h1>

        <div class="instructions">
            <h3>How to get session cookies:</h3>
            <ol>
                <li>Open a Lark Minutes page in your browser (logged in)</li>
                <li>Press F12 to open Developer Tools</li>
                <li>Go to Application tab → Cookies</li>
                <li>Find and copy these values:
                    <ul>
                        <li><code>sl_session</code> - Main session token (required)</li>
                        <li><code>session</code> - Session ID (required)</li>
                    </ul>
                </li>
            </ol>
        </div>

        <form action="/session/save" method="POST">
            <div class="form-group">
                <label for="sl_session">sl_session (required):</label>
                <textarea name="sl_session" id="sl_session" required placeholder="eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9..."></textarea>
            </div>

            <div class="form-group">
                <label for="session">session (required):</label>
                <input type="text" name="session" id="session" required placeholder="XN0YXJ0-xxxxx-WVuZA">
            </div>

            <div class="form-group">
                <label for="csrf_token">csrf_token (optional):</label>
                <input type="text" name="csrf_token" id="csrf_token" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx">
            </div>

            <button type="submit">💾 Save Session</button>
        </form>

        <p style="margin-top: 20px;">
            <a href="/session/status">Check current status</a>
        </p>
    </body>
    </html>
    """)


@app.post("/session/save")
async def session_save(request: Request):
    """
    Save session cookies
    """
    form = await request.form()

    sl_session = form.get("sl_session", "").strip()
    session = form.get("session", "").strip()
    csrf_token = form.get("csrf_token", "").strip()

    if not sl_session or not session:
        return HTMLResponse(content="""
        <html>
        <body>
            <h1>❌ Error</h1>
            <p>sl_session and session are required.</p>
            <p><a href="/session/set">Go back</a></p>
        </body>
        </html>
        """, status_code=400)

    session_data = {
        "sl_session": sl_session,
        "session": session
    }

    if csrf_token:
        session_data["csrf_token"] = csrf_token

    if save_session(session_data):
        return HTMLResponse(content="""
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center; }
                .success { color: #4CAF50; font-size: 48px; }
            </style>
        </head>
        <body>
            <div class="success">✅</div>
            <h1>Session Saved Successfully!</h1>
            <p>The system is now ready to download Lark meetings.</p>
            <p>
                <a href="/session/status">Check Status</a> |
                <a href="/">Home</a>
            </p>
        </body>
        </html>
        """)
    else:
        return HTMLResponse(content="""
        <html>
        <body>
            <h1>❌ Failed to Save Session</h1>
            <p>Please check server logs for details.</p>
            <p><a href="/session/set">Try again</a></p>
        </body>
        </html>
        """, status_code=500)


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
    background_tasks.add_task(process_meeting_safe, meeting_url)

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
    background_tasks.add_task(process_meeting_safe, meeting_url)

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
