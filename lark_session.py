#!/usr/bin/env python3
"""
Lark Session-based API Client
Uses browser session cookies to access Minutes API (bypasses OAuth scope issues)
"""

import os
import sys
import requests
import json
import re
from typing import Optional, Dict, Any
from pathlib import Path

# Fix encoding for Vietnamese
sys.stdout.reconfigure(encoding='utf-8')

# Session token file
SESSION_FILE = Path(__file__).parent / ".lark_session.json"

# Lark domains
LARK_DOMAIN = os.getenv('LARK_DOMAIN', 'gearvn-com.sg.larksuite.com')


def save_session(session_data: Dict[str, str]) -> bool:
    """
    Save session cookies to file

    Args:
        session_data: Dict containing session cookies
            Required: sl_session, session
            Optional: csrf_token, minutes_csrf_token

    Returns:
        bool: True if saved successfully
    """
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"✓ Session saved to {SESSION_FILE}")
        return True
    except Exception as e:
        print(f"✗ Failed to save session: {e}")
        return False


def load_session() -> Optional[Dict[str, str]]:
    """Load session cookies from file"""
    if not SESSION_FILE.exists():
        return None

    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"✗ Failed to load session: {e}")
        return None


def get_session_headers(session_data: Dict[str, str], referer_token: str = None) -> Dict[str, str]:
    """Build headers for session-based requests"""
    cookie_parts = []
    for key, value in session_data.items():
        cookie_parts.append(f"{key}={value}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Cookie': '; '.join(cookie_parts),
        'x-lsc-terminal': 'web',
        'x-lsc-bizid': '16',
    }

    if referer_token:
        headers['Referer'] = f'https://{LARK_DOMAIN}/minutes/{referer_token}'

    return headers


def get_meeting_status(minute_token: str, session_data: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
    """
    Get meeting status and video info using session cookies

    Args:
        minute_token: The minute token from URL
        session_data: Session cookies (loads from file if not provided)

    Returns:
        dict: Meeting status data including video_download_url
    """
    if not session_data:
        session_data = load_session()

    if not session_data:
        print("✗ No session data. Please set session cookies first.")
        return None

    print(f"📋 Getting meeting status for: {minute_token}")

    url = f"https://{LARK_DOMAIN}/minutes/api/status"
    params = {
        'object_token': minute_token,
        'with_transcript': 'true',
        'language': 'en_us'
    }

    headers = get_session_headers(session_data, minute_token)

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get('msg') == 'success':
                print("✓ Meeting status retrieved successfully")
                return data.get('data', {})
            else:
                print(f"✗ API error: {data.get('msg')}")
                return None
        else:
            print(f"✗ HTTP {response.status_code}: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"✗ Request failed: {e}")
        return None


def get_meeting_info(minute_token: str, session_data: Dict[str, str] = None) -> Optional[Dict[str, Any]]:
    """
    Get meeting metadata (title, participants, etc.)

    Args:
        minute_token: The minute token from URL
        session_data: Session cookies

    Returns:
        dict: Meeting info
    """
    if not session_data:
        session_data = load_session()

    if not session_data:
        print("✗ No session data")
        return None

    print(f"📋 Getting meeting info for: {minute_token}")

    url = f"https://{LARK_DOMAIN}/minutes/api/info"
    params = {
        'object_token': minute_token,
        'language': 'en_us'
    }

    headers = get_session_headers(session_data, minute_token)

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get('msg') == 'success':
                print("✓ Meeting info retrieved")
                return data.get('data', {})
        return None

    except Exception as e:
        print(f"✗ Request failed: {e}")
        return None


def get_download_url(minute_token: str, session_data: Dict[str, str] = None) -> Optional[str]:
    """
    Get video download URL

    Args:
        minute_token: The minute token from URL
        session_data: Session cookies

    Returns:
        str: Download URL for video
    """
    status = get_meeting_status(minute_token, session_data)

    if not status:
        return None

    video_info = status.get('video_info', {})
    download_url = video_info.get('video_download_url')

    if download_url:
        print(f"✓ Got download URL")
        return download_url
    else:
        print("✗ No download URL in response")
        return None


def download_video(minute_token: str, output_path: str, session_data: Dict[str, str] = None) -> Optional[str]:
    """
    Download meeting video

    Args:
        minute_token: The minute token
        output_path: Where to save the video
        session_data: Session cookies

    Returns:
        str: Path to downloaded file
    """
    if not session_data:
        session_data = load_session()

    download_url = get_download_url(minute_token, session_data)

    if not download_url:
        return None

    print(f"⬇️ Downloading video to: {output_path}")

    headers = get_session_headers(session_data, minute_token)

    try:
        # Create output directory
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        with requests.get(download_url, headers=headers, stream=True, timeout=60) as response:
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        if total_size > 0 and downloaded % (8192 * 100) == 0:
                            progress = (downloaded / total_size) * 100
                            print(f"  Progress: {progress:.1f}%")

        file_size = os.path.getsize(output_path)
        print(f"✓ Download complete: {file_size / 1024 / 1024:.2f}MB")
        return output_path

    except Exception as e:
        print(f"✗ Download failed: {e}")
        if os.path.exists(output_path):
            os.remove(output_path)
        return None


def extract_minute_token(meeting_url: str) -> Optional[str]:
    """Extract minute_token from Lark meeting URL"""
    match = re.search(r'/minutes/([a-zA-Z0-9]+)', meeting_url)
    if match:
        return match.group(1)
    return None


# CLI interface
def main():
    import sys

    if len(sys.argv) < 2:
        print("Lark Session-based Meeting Downloader")
        print("=" * 50)
        print()
        print("Usage:")
        print("  python lark_session.py set-session    # Set session cookies")
        print("  python lark_session.py info <url>     # Get meeting info")
        print("  python lark_session.py download <url> # Download video")
        print()
        print("Example:")
        print("  python lark_session.py download https://gearvn-com.sg.larksuite.com/minutes/obsghl2794n824vor6964r7o")
        return

    command = sys.argv[1]

    if command == 'set-session':
        print("Enter session cookies (from browser DevTools):")
        print()
        sl_session = input("sl_session: ").strip()
        session = input("session: ").strip()
        csrf = input("csrf_token (optional): ").strip()

        session_data = {
            'sl_session': sl_session,
            'session': session,
        }
        if csrf:
            session_data['csrf_token'] = csrf

        save_session(session_data)

    elif command == 'info' and len(sys.argv) >= 3:
        url = sys.argv[2]
        token = extract_minute_token(url)
        if token:
            info = get_meeting_info(token)
            if info:
                print(json.dumps(info, indent=2, ensure_ascii=False)[:2000])
        else:
            print("Invalid URL")

    elif command == 'download' and len(sys.argv) >= 3:
        url = sys.argv[2]
        token = extract_minute_token(url)
        if token:
            output = f"downloads/{token}.mp4"
            result = download_video(token, output)
            if result:
                print(f"\n✓ Video saved to: {result}")
        else:
            print("Invalid URL")

    else:
        print("Invalid command. Run without arguments for help.")


if __name__ == "__main__":
    main()
