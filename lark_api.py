#!/usr/bin/env python3
"""
Lark API Client for downloading meeting recordings
Uses session-based authentication (browser cookies) for Minutes API
"""

import os
import sys
import requests
import re
from typing import Optional, Dict, Any

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Import session module
try:
    from lark_session import (
        load_session,
        get_meeting_status,
        get_meeting_info as session_get_meeting_info,
        get_session_headers,
        LARK_DOMAIN
    )
    HAS_SESSION = True
except ImportError:
    HAS_SESSION = False
    print("⚠️ lark_session module not found")
    LARK_DOMAIN = os.getenv('LARK_DOMAIN', 'gearvn-com.sg.larksuite.com')


def extract_minute_token(meeting_url: str) -> Optional[str]:
    """
    Extract minute_token from Lark meeting URL

    Args:
        meeting_url: URL like https://gearvn-com.sg.larksuite.com/minutes/obsgji9p2ik7j516z48l1ln2

    Returns:
        str: minute_token if found, None otherwise
    """
    # Pattern: /minutes/{minute_token}
    match = re.search(r'/minutes/([a-zA-Z0-9]+)', meeting_url)

    if match:
        token = match.group(1)
        print(f"✓ Extracted minute_token: {token}")
        return token
    else:
        print(f"✗ Could not extract minute_token from URL: {meeting_url}")
        return None


def get_meeting_info(minute_token: str, session_data: Dict = None) -> Optional[Dict[str, Any]]:
    """
    Get meeting metadata from Lark API using session cookies

    Args:
        minute_token: The minute token
        session_data: Session cookies (optional, loads from file)

    Returns:
        dict: Meeting metadata if successful, None otherwise
    """
    if not HAS_SESSION:
        print("✗ Session module not available")
        return None

    if not session_data:
        session_data = load_session()

    if not session_data:
        print("✗ No session data. Please configure session cookies.")
        return None

    return session_get_meeting_info(minute_token, session_data)


def get_download_url(minute_token: str, session_data: Dict = None) -> Optional[str]:
    """
    Get download URL for meeting video using session cookies

    Args:
        minute_token: The minute token
        session_data: Session cookies (optional)

    Returns:
        str: Download URL if successful, None otherwise
    """
    if not HAS_SESSION:
        print("✗ Session module not available")
        return None

    if not session_data:
        session_data = load_session()

    if not session_data:
        print("✗ No session data. Please configure session cookies.")
        return None

    print(f"🔗 Getting download URL for token: {minute_token}...")

    status = get_meeting_status(minute_token, session_data)

    if not status:
        return None

    video_info = status.get('video_info', {})
    download_url = video_info.get('video_download_url')

    if download_url:
        print(f"✓ Download URL retrieved")
        return download_url
    else:
        print("✗ No download URL in response")
        return None


def download_video(download_url: str, output_path: str, session_data: Dict = None, chunk_size: int = 8192) -> Optional[str]:
    """
    Download video from Lark download URL

    Args:
        download_url: The download URL
        output_path: Where to save the video file
        session_data: Session cookies for authentication
        chunk_size: Download chunk size in bytes

    Returns:
        str: Path to downloaded file if successful, None otherwise
    """
    print(f"⬇️ Downloading video to: {output_path}")

    if not session_data:
        session_data = load_session()

    # Create output directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Build headers with session cookies
    headers = get_session_headers(session_data) if session_data else {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # Stream download to handle large files
        with requests.get(download_url, headers=headers, stream=True, timeout=300) as response:
            response.raise_for_status()

            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Print progress for large files
                        if total_size > 0 and downloaded % (chunk_size * 100) == 0:
                            progress = (downloaded / total_size) * 100
                            print(f"  Progress: {progress:.1f}% ({downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB)")

        file_size = os.path.getsize(output_path)
        print(f"✓ Download complete: {file_size / 1024 / 1024:.2f}MB")
        return output_path

    except requests.exceptions.RequestException as e:
        print(f"✗ Download failed: {str(e)}")

        # Clean up partial file
        if os.path.exists(output_path):
            os.remove(output_path)

        return None


def download_meeting_video(meeting_url: str, output_folder: str = "downloads") -> Optional[Dict[str, Any]]:
    """
    Complete workflow: Extract token, get info, download video using session cookies

    Args:
        meeting_url: Lark meeting URL
        output_folder: Where to save downloaded video

    Returns:
        dict: {
            'minute_token': str,
            'meeting_info': dict,
            'video_path': str,
            'video_size': int
        } if successful, None otherwise
    """
    print("=" * 70)
    print("LARK MEETING VIDEO DOWNLOAD (Session-based)")
    print("=" * 70)

    # Load session
    session_data = load_session() if HAS_SESSION else None
    if not session_data:
        print("✗ No session data. Please configure session cookies first.")
        print("  Run: python lark_session.py set-session")
        return None

    # Step 1: Extract minute token
    minute_token = extract_minute_token(meeting_url)
    if not minute_token:
        return None

    # Step 2: Get meeting info (optional, for metadata)
    meeting_info = get_meeting_info(minute_token, session_data)

    # Step 3: Get download URL
    download_url = get_download_url(minute_token, session_data)
    if not download_url:
        return None

    # Step 4: Download video
    os.makedirs(output_folder, exist_ok=True)
    video_filename = f"{minute_token}.mp4"
    video_path = os.path.join(output_folder, video_filename)

    downloaded_path = download_video(download_url, video_path, session_data)
    if not downloaded_path:
        return None

    print("\n" + "=" * 70)
    print("✓ DOWNLOAD COMPLETED SUCCESSFULLY")
    print("=" * 70)

    return {
        'minute_token': minute_token,
        'meeting_info': meeting_info,
        'video_path': downloaded_path,
        'video_size': os.path.getsize(downloaded_path)
    }


# Test function
def main():
    """Test the Lark API client"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lark_api.py <meeting_url>")
        print("Example: python lark_api.py https://gearvn-com.sg.larksuite.com/minutes/obsgji9p2ik7j516z48l1ln2")
        print()
        print("Note: Make sure to configure session cookies first:")
        print("  python lark_session.py set-session")
        return

    meeting_url = sys.argv[1]
    result = download_meeting_video(meeting_url)

    if result:
        print(f"\n📄 Result:")
        print(f"  Minute Token: {result['minute_token']}")
        print(f"  Video Path: {result['video_path']}")
        print(f"  Video Size: {result['video_size'] / 1024 / 1024:.2f}MB")


if __name__ == "__main__":
    main()
