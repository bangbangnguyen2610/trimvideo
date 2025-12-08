#!/usr/bin/env python3
"""
Meeting Processor - Main orchestrator for Lark meeting automation
Integrates: Lark API → Convert → Transcript → Summary → Auto-Tag → Supabase
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Import our modules
from lark_api import download_meeting_video, extract_minute_token
from gemini_tagger import analyze_and_tag_with_retry
from convert_with_gemini import (
    check_ffmpeg,
    convert_to_mp3,
    split_audio,
    process_segments_with_gemini,
    save_full_transcript,
    summarize_transcript,
    save_summary
)

# Import Supabase
from supabase import create_client, Client

# Supabase Configuration (NEW - for meetings)
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://iuadezkhfzcvkvgmhupe.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml1YWRlemtoZnpjdmt2Z21odXBlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyMTkyNDQsImV4cCI6MjA4MDc5NTI0NH0.mlDh2GfgnG0Q54CXnTGsZ_3WjhfChPLh9eeK9eZdLYc')

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def log_processing_step(meeting_id: str, step: str, status: str, message: str = None, metadata: Dict = None):
    """
    Log processing step to Supabase

    Args:
        meeting_id: UUID of meeting
        step: Processing step name
        status: started, completed, failed
        message: Optional message
        metadata: Optional metadata dict
    """
    try:
        log_data = {
            "meeting_id": meeting_id,
            "step": step,
            "status": status,
            "message": message,
            "metadata": metadata
        }
        supabase.table("processing_logs").insert(log_data).execute()
    except Exception as e:
        print(f"⚠️ Failed to log to Supabase: {str(e)}")


def create_meeting_record(minute_token: str, meeting_url: str, meeting_info: Dict = None) -> Optional[str]:
    """
    Create initial meeting record in Supabase

    Args:
        minute_token: Lark minute token
        meeting_url: Full meeting URL
        meeting_info: Optional meeting metadata from Lark API

    Returns:
        str: Meeting ID (UUID) if successful, None otherwise
    """
    print("💾 Creating meeting record in Supabase...")

    try:
        # Extract basic info
        meeting_title = meeting_info.get('title', 'Untitled Meeting') if meeting_info else 'Untitled Meeting'

        meeting_data = {
            "lark_meeting_id": minute_token,  # Use minute_token as unique ID
            "lark_meeting_url": meeting_url,
            "minute_token": minute_token,
            "meeting_title": meeting_title,
            "meeting_date": datetime.now().isoformat(),
            "status": "processing"
        }

        # Add optional fields if available
        if meeting_info:
            if 'owner' in meeting_info:
                meeting_data['meeting_owner'] = meeting_info['owner']
            if 'participants' in meeting_info:
                meeting_data['participants'] = json.dumps(meeting_info['participants'])
            if 'duration' in meeting_info:
                meeting_data['meeting_duration'] = meeting_info['duration']

        response = supabase.table("meetings").insert(meeting_data).execute()

        if response.data and len(response.data) > 0:
            meeting_id = response.data[0]['id']
            print(f"✓ Meeting record created: {meeting_id}")
            return meeting_id
        else:
            print("✗ Failed to create meeting record")
            return None

    except Exception as e:
        print(f"✗ Error creating meeting record: {str(e)}")
        return None


def update_meeting_status(meeting_id: str, status: str, error_message: str = None, **kwargs):
    """
    Update meeting status in Supabase

    Args:
        meeting_id: Meeting UUID
        status: New status
        error_message: Optional error message
        **kwargs: Additional fields to update
    """
    try:
        update_data = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }

        if error_message:
            update_data["error_message"] = error_message

        if status == "completed":
            update_data["processed_at"] = datetime.now().isoformat()

        # Add any additional fields
        update_data.update(kwargs)

        supabase.table("meetings").update(update_data).eq("id", meeting_id).execute()
        print(f"✓ Meeting status updated: {status}")

    except Exception as e:
        print(f"⚠️ Failed to update meeting status: {str(e)}")


def upload_transcript_and_summary(meeting_id: str, transcript_path: str, summary_path: str, tags: Dict) -> bool:
    """
    Upload transcript and summary to Supabase

    Args:
        meeting_id: Meeting UUID
        transcript_path: Path to transcript file
        summary_path: Path to summary file
        tags: Auto-generated tags dict

    Returns:
        bool: True if successful
    """
    print("📤 Uploading transcript and summary to Supabase...")

    try:
        # Read files
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_content = f.read()

        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_content = f.read()

        # Calculate word count
        word_count = len(transcript_content.split())

        # Create transcript record
        transcript_data = {
            "meeting_id": meeting_id,
            "transcript_content": transcript_content,
            "transcript_word_count": word_count,
            "summary_content": summary_content
        }

        # TODO: Parse summary to extract components (main_topics, decisions, etc.)
        # For now, we'll leave them as NULL

        supabase.table("meeting_transcripts").insert(transcript_data).execute()

        # Update meeting with tags
        update_meeting_status(
            meeting_id,
            status="completed",
            meeting_type=tags.get('meeting_type'),
            meeting_topic=tags.get('meeting_topic')
        )

        print("✓ Transcript and summary uploaded successfully")
        return True

    except Exception as e:
        print(f"✗ Failed to upload transcript/summary: {str(e)}")
        return False


def process_meeting(meeting_url: str) -> bool:
    """
    Main processing pipeline for Lark meeting

    Args:
        meeting_url: Lark meeting URL

    Returns:
        bool: True if successful, False otherwise
    """
    print("\n" + "=" * 70)
    print("LARK MEETING AUTOMATION - FULL PIPELINE")
    print("=" * 70)
    print(f"Meeting URL: {meeting_url}\n")

    meeting_id = None
    minute_token = None

    try:
        # Step 0: Check ffmpeg
        print("[Step 0/8] Checking ffmpeg...")
        if not check_ffmpeg():
            print("✗ ffmpeg not found! Please install ffmpeg first.")
            return False
        print("✓ ffmpeg ready\n")

        # Step 1: Download video from Lark
        print("[Step 1/8] Downloading video from Lark...")
        download_result = download_meeting_video(meeting_url, output_folder="downloads")

        if not download_result:
            print("✗ Failed to download video")
            return False

        minute_token = download_result['minute_token']
        video_path = download_result['video_path']
        video_size = download_result['video_size']
        meeting_info = download_result.get('meeting_info')

        print(f"✓ Video downloaded: {video_path} ({video_size / 1024 / 1024:.2f}MB)\n")

        # Step 2: Create meeting record in Supabase
        print("[Step 2/8] Creating meeting record...")
        meeting_id = create_meeting_record(minute_token, meeting_url, meeting_info)

        if not meeting_id:
            print("✗ Failed to create meeting record")
            return False

        log_processing_step(meeting_id, "download", "completed", f"Downloaded {video_size / 1024 / 1024:.2f}MB")

        # Step 3: Convert MP4 to MP3
        print("\n[Step 3/8] Converting MP4 to MP3...")
        log_processing_step(meeting_id, "convert", "started")

        output_folder = os.path.join("downloads", f"{minute_token}_output")
        mp3_path = convert_to_mp3(video_path, output_folder)

        if not mp3_path:
            raise Exception("Failed to convert MP4 to MP3")

        log_processing_step(meeting_id, "convert", "completed")
        print(f"✓ Converted to MP3: {mp3_path}\n")

        # Step 4: Split into segments
        print("[Step 4/8] Splitting audio into 25-minute segments...")
        log_processing_step(meeting_id, "segment", "started")

        segments = split_audio(mp3_path, segment_duration=1500, output_folder=output_folder)

        if not segments:
            raise Exception("Failed to split audio")

        log_processing_step(meeting_id, "segment", "completed", metadata={"segment_count": len(segments)})
        print(f"✓ Created {len(segments)} segments\n")

        # Step 5: Transcript with Gemini
        print("[Step 5/8] Transcribing with Gemini AI...")
        log_processing_step(meeting_id, "transcript", "started")

        transcripts = process_segments_with_gemini(segments, output_folder)
        transcript_path = save_full_transcript(transcripts, output_folder, minute_token)

        if not transcript_path:
            raise Exception("Failed to generate transcript")

        log_processing_step(meeting_id, "transcript", "completed")
        print(f"✓ Transcript saved: {transcript_path}\n")

        # Step 6: Generate summary
        print("[Step 6/8] Generating summary with Gemini...")
        log_processing_step(meeting_id, "summary", "started")

        summary_result = summarize_transcript(transcript_path)
        summary_path = save_summary(summary_result, output_folder, minute_token)

        if not summary_path:
            raise Exception("Failed to generate summary")

        log_processing_step(meeting_id, "summary", "completed")
        print(f"✓ Summary saved: {summary_path}\n")

        # Step 7: Auto-tag with Gemini
        print("[Step 7/8] Auto-tagging meeting...")
        log_processing_step(meeting_id, "tag", "started")

        # Read summary content for tagging
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary_content = f.read()

        tags = analyze_and_tag_with_retry(summary_content)

        if not tags:
            print("⚠️ Auto-tagging failed, using defaults")
            tags = {
                'meeting_type': 'Họp định kỳ',
                'meeting_topic': 'Business'
            }

        log_processing_step(meeting_id, "tag", "completed", metadata=tags)
        print(f"✓ Tags: {tags['meeting_type']} | {tags['meeting_topic']}\n")

        # Step 8: Upload to Supabase
        print("[Step 8/8] Uploading to Supabase...")
        log_processing_step(meeting_id, "upload", "started")

        if not upload_transcript_and_summary(meeting_id, transcript_path, summary_path, tags):
            raise Exception("Failed to upload to Supabase")

        log_processing_step(meeting_id, "upload", "completed")

        print("\n" + "=" * 70)
        print("✅ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"Meeting ID: {meeting_id}")
        print(f"Transcript: {transcript_path}")
        print(f"Summary: {summary_path}")
        print(f"Tags: {tags['meeting_type']} | {tags['meeting_topic']}")
        print("=" * 70)

        return True

    except Exception as e:
        error_message = str(e)
        print(f"\n✗ Pipeline failed: {error_message}")

        # Update meeting status to failed
        if meeting_id:
            update_meeting_status(meeting_id, "failed", error_message=error_message)

            # Log failure
            log_processing_step(meeting_id, "pipeline", "failed", message=error_message)

        return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python meeting_processor.py <meeting_url>")
        print("Example: python meeting_processor.py https://gearvn-com.sg.larksuite.com/minutes/obsgji9p2ik7j516z48l1ln2")
        sys.exit(1)

    meeting_url = sys.argv[1]
    success = process_meeting(meeting_url)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
