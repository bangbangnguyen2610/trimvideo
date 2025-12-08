#!/usr/bin/env python3
"""
Webhook Receiver - FastAPI app to receive Lark webhooks and trigger processing
Deploy this to Railway/Render for production use
"""

import os
import sys
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')

# Import processor
from meeting_processor import process_meeting

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
