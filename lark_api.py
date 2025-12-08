#!/usr/bin/env python3
"""
Lark API Client for downloading meeting recordings
Uses user_access_token for Minutes API (requires OAuth authorization)
"""

import os
import sys
import requests
import time
import re
from pathlib import Path
from typing import Optional, Dict, Any

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Lark API Configuration
LARK_APP_ID = os.getenv('LARK_APP_ID', 'cli_a9aab0f22978deed')
LARK_APP_SECRET = os.getenv('LARK_APP_SECRET', 'qGF9xiBcIcZrqzpTS8wV3fB7ouywulDV')
LARK_API_BASE = "https://open.larksuite.com/open-apis"

# Import OAuth module for user_access_token
try:
    from lark_oauth import get_valid_access_token as get_user_access_token
    HAS_OAUTH = True
except ImportError:
    HAS_OAUTH = False
    print("⚠️ lark_oauth module not found, falling back to tenant_access_token")

# Cache for tenant access token (fallback)
_tenant_token_cache = {
    'token': None,
    'expires_at': 0
}


def get_tenant_access_token() -> Optional[str]:
    """
    Get tenant_access_token (fallback, does NOT work for Minutes API)

    Returns:
        str: Access token if successful, None otherwise
    """
    # Check cache first
    current_time = time.time()
    if _tenant_token_cache['token'] and current_time < _tenant_token_cache['expires_at']:
        return _tenant_token_cache['token']

    print("🔐 Getting tenant_access_token (fallback)...")

    url = f"{LARK_API_BASE}/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": LARK_APP_ID,
        "app_secret": LARK_APP_SECRET
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get('code') == 0:
            token = data['tenant_access_token']
            expires_in = data.get('expire', 7200)  # Default 2 hours

            # Cache token (subtract 5 minutes for safety)
            _tenant_token_cache['token'] = token
            _tenant_token_cache['expires_at'] = current_time + expires_in - 300

            print(f"✓ Tenant token obtained (expires in {expires_in}s)")
            return token
        else:
            print(f"✗ Failed to get tenant token: {data.get('msg', 'Unknown error')}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
        return None


def authenticate() -> Optional[str]:
    """
    Get access token for Lark API

    For Minutes API, uses user_access_token (requires OAuth)
    Falls back to tenant_access_token if OAuth not available

    Returns:
        str: Access token if successful, None otherwise
    """
    # Try user_access_token first (required for Minutes API)
    if HAS_OAUTH:
        print("🔐 Getting user_access_token (required for Minutes API)...")
        token = get_user_access_token()
        if token:
            return token
        else:
            print("⚠️ No valid user_access_token. OAuth authorization required.")
            print("   Please visit: https://lark-meeting-webhook.onrender.com/oauth/authorize")
            return None

    # Fallback to tenant_access_token (won't work for Minutes API)
    print("⚠️ Using tenant_access_token (may not work for Minutes API)")
    return get_tenant_access_token()


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


def get_meeting_info(minute_token: str, access_token: str) -> Optional[Dict[str, Any]]:
    """
    Get meeting metadata from Lark API

    Args:
        minute_token: The minute token
        access_token: Lark access token

    Returns:
        dict: Meeting metadata if successful, None otherwise
    """
    print(f"📋 Fetching meeting info for token: {minute_token}...")

    url = f"{LARK_API_BASE}/minutes/v1/minutes/{minute_token}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get('code') == 0:
            meeting_data = data.get('data', {})
            print(f"✓ Meeting info retrieved successfully")
            return meeting_data
        else:
            error_msg = data.get('msg', 'Unknown error')
            print(f"✗ Failed to get meeting info: {error_msg}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
        return None


def get_download_url(minute_token: str, access_token: str) -> Optional[str]:
    """
    Get download URL for meeting video/audio

    Args:
        minute_token: The minute token
        access_token: Lark access token

    Returns:
        str: Download URL (valid for 1 day) if successful, None otherwise
    """
    print(f"🔗 Getting download URL for token: {minute_token}...")

    url = f"{LARK_API_BASE}/minutes/v1/minutes/{minute_token}/media"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()

        if data.get('code') == 0:
            download_url = data.get('data', {}).get('download_url')

            if download_url:
                print(f"✓ Download URL retrieved (valid for 1 day)")
                return download_url
            else:
                print(f"✗ No download URL in response")
                return None
        else:
            error_code = data.get('code')
            error_msg = data.get('msg', 'Unknown error')

            # Handle specific error codes
            if error_code == 2091003:
                print(f"⚠️ Meeting transcription not ready yet, try later")
            elif error_code == 2091004:
                print(f"✗ Meeting has been deleted")
            elif error_code == 2091005:
                print(f"✗ Permission denied - check app scopes")
            else:
                print(f"✗ Failed to get download URL: {error_msg} (code: {error_code})")

            return None

    except requests.exceptions.RequestException as e:
        print(f"✗ Request failed: {str(e)}")
        return None


def download_video(download_url: str, output_path: str, chunk_size: int = 8192) -> Optional[str]:
    """
    Download video from Lark download URL

    Args:
        download_url: The download URL from get_download_url()
        output_path: Where to save the video file
        chunk_size: Download chunk size in bytes

    Returns:
        str: Path to downloaded file if successful, None otherwise
    """
    print(f"⬇️ Downloading video to: {output_path}")

    # Create output directory if needed
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    try:
        # Stream download to handle large files
        with requests.get(download_url, stream=True, timeout=60) as response:
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
    Complete workflow: Extract token, authenticate, get info, download video

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
    print("LARK MEETING VIDEO DOWNLOAD")
    print("=" * 70)

    # Step 1: Extract minute token
    minute_token = extract_minute_token(meeting_url)
    if not minute_token:
        return None

    # Step 2: Authenticate
    access_token = authenticate()
    if not access_token:
        return None

    # Step 3: Get meeting info (optional, for metadata)
    meeting_info = get_meeting_info(minute_token, access_token)

    # Step 4: Get download URL
    download_url = get_download_url(minute_token, access_token)
    if not download_url:
        return None

    # Step 5: Download video
    os.makedirs(output_folder, exist_ok=True)
    video_filename = f"{minute_token}.mp4"
    video_path = os.path.join(output_folder, video_filename)

    downloaded_path = download_video(download_url, video_path)
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
