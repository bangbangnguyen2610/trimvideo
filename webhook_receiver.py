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
    payload: WebhookPayload,
    background_tasks: BackgroundTasks
):
    """
    Main webhook endpoint to receive Lark meeting notifications

    Expected payload:
    {
        "meeting_url": "https://gearvn-com.sg.larksuite.com/minutes/obsgji9p2ik7j516z48l1ln2",
        "event_type": "meeting_completed",
        "timestamp": "2025-12-09T10:00:00Z"
    }
    """
    print("=" * 70)
    print("📨 WEBHOOK RECEIVED")
    print("=" * 70)
    print(f"Meeting URL: {payload.meeting_url}")
    print(f"Event Type: {payload.event_type}")
    print(f"Timestamp: {payload.timestamp}")
    print("=" * 70)

    # Validate meeting URL
    if not payload.meeting_url or "larksuite.com/minutes/" not in payload.meeting_url:
        raise HTTPException(
            status_code=400,
            detail="Invalid meeting URL format"
        )

    # Trigger processing in background (non-blocking)
    background_tasks.add_task(process_meeting, payload.meeting_url)

    # Return immediate response to Lark
    return JSONResponse(
        status_code=202,
        content={
            "status": "accepted",
            "message": "Meeting processing started in background",
            "meeting_url": payload.meeting_url
        }
    )


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
