#!/usr/bin/env python3
"""
Lark OAuth - User Access Token Management
Handles OAuth flow, token storage, and auto-refresh
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')

# Lark OAuth Configuration
LARK_APP_ID = os.getenv('LARK_APP_ID', 'cli_a9aab0f22978deed')
LARK_APP_SECRET = os.getenv('LARK_APP_SECRET', 'qGF9xiBcIcZrqzpTS8wV3fB7ouywulDV')

# OAuth URLs
AUTHORIZE_URL = "https://accounts.larksuite.com/open-apis/authen/v1/authorize"
TOKEN_URL = "https://open.larksuite.com/open-apis/authen/v2/oauth/token"

# Token storage file
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '.lark_token.json')

# Redirect URI for OAuth callback
REDIRECT_URI = os.getenv('LARK_REDIRECT_URI', 'https://lark-meeting-webhook.onrender.com/oauth/callback')


def save_token(token_data: Dict):
    """Save token data to file"""
    token_data['saved_at'] = time.time()
    with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
        json.dump(token_data, f, indent=2)
    print(f"✓ Token saved to {TOKEN_FILE}")


def load_token() -> Optional[Dict]:
    """Load token data from file"""
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load token: {e}")
        return None


def is_token_valid(token_data: Dict) -> bool:
    """Check if access token is still valid"""
    if not token_data:
        return False

    saved_at = token_data.get('saved_at', 0)
    expires_in = token_data.get('expires_in', 0)

    # Token is valid if current time < saved_at + expires_in - 5 minutes buffer
    expiry_time = saved_at + expires_in - 300
    is_valid = time.time() < expiry_time

    if is_valid:
        remaining = int(expiry_time - time.time())
        print(f"✓ Access token valid for {remaining}s ({remaining // 60} minutes)")
    else:
        print("✗ Access token expired")

    return is_valid


def is_refresh_token_valid(token_data: Dict) -> bool:
    """Check if refresh token is still valid"""
    if not token_data:
        return False

    saved_at = token_data.get('saved_at', 0)
    refresh_expires_in = token_data.get('refresh_token_expires_in', 0)

    if refresh_expires_in == 0:
        return False

    # Refresh token is valid if current time < saved_at + refresh_expires_in - 1 hour buffer
    expiry_time = saved_at + refresh_expires_in - 3600
    is_valid = time.time() < expiry_time

    if is_valid:
        remaining = int(expiry_time - time.time())
        print(f"✓ Refresh token valid for {remaining}s ({remaining // 3600} hours)")
    else:
        print("✗ Refresh token expired")

    return is_valid


def refresh_access_token(refresh_token: str) -> Optional[Dict]:
    """
    Refresh the access token using refresh_token

    Args:
        refresh_token: The refresh token

    Returns:
        dict: New token data if successful, None otherwise
    """
    print("🔄 Refreshing access token...")

    url = "https://open.larksuite.com/open-apis/authen/v2/oauth/token"

    payload = {
        "grant_type": "refresh_token",
        "client_id": LARK_APP_ID,
        "client_secret": LARK_APP_SECRET,
        "refresh_token": refresh_token
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()

        if data.get('code') == '0' or data.get('code') == 0:
            token_data = {
                'access_token': data.get('access_token'),
                'expires_in': data.get('expires_in', 7200),
                'refresh_token': data.get('refresh_token'),
                'refresh_token_expires_in': data.get('refresh_token_expires_in', 0),
                'token_type': data.get('token_type', 'Bearer'),
                'scope': data.get('scope', '')
            }

            save_token(token_data)
            print(f"✓ Token refreshed successfully!")
            print(f"  - Access token expires in: {token_data['expires_in']}s")
            if token_data['refresh_token_expires_in']:
                print(f"  - Refresh token expires in: {token_data['refresh_token_expires_in']}s")

            return token_data
        else:
            print(f"✗ Failed to refresh token: {data.get('error_description', data)}")
            return None

    except Exception as e:
        print(f"✗ Error refreshing token: {e}")
        return None


def exchange_code_for_token(code: str, redirect_uri: str = None) -> Optional[Dict]:
    """
    Exchange authorization code for access token

    Args:
        code: Authorization code from OAuth callback
        redirect_uri: Redirect URI used in authorization

    Returns:
        dict: Token data if successful, None otherwise
    """
    print(f"🔑 Exchanging authorization code for token...")

    payload = {
        "grant_type": "authorization_code",
        "client_id": LARK_APP_ID,
        "client_secret": LARK_APP_SECRET,
        "code": code
    }

    if redirect_uri:
        payload["redirect_uri"] = redirect_uri

    try:
        response = requests.post(TOKEN_URL, json=payload, timeout=30)
        data = response.json()

        if data.get('code') == '0' or data.get('code') == 0:
            token_data = {
                'access_token': data.get('access_token'),
                'expires_in': data.get('expires_in', 7200),
                'refresh_token': data.get('refresh_token'),
                'refresh_token_expires_in': data.get('refresh_token_expires_in', 0),
                'token_type': data.get('token_type', 'Bearer'),
                'scope': data.get('scope', '')
            }

            save_token(token_data)
            print(f"✓ Token obtained successfully!")
            print(f"  - Access token expires in: {token_data['expires_in']}s ({token_data['expires_in'] // 60} minutes)")
            if token_data['refresh_token_expires_in']:
                print(f"  - Refresh token expires in: {token_data['refresh_token_expires_in']}s ({token_data['refresh_token_expires_in'] // 3600} hours)")

            return token_data
        else:
            print(f"✗ Failed to exchange code: {data.get('error_description', data)}")
            return None

    except Exception as e:
        print(f"✗ Error exchanging code: {e}")
        return None


def get_authorization_url(state: str = "random_state") -> str:
    """
    Generate OAuth authorization URL

    Args:
        state: Random state for CSRF protection

    Returns:
        str: Authorization URL
    """
    # Scopes needed for Minutes API
    scopes = "offline_access minutes:minutes:read minutes:minutes:media"

    url = (
        f"{AUTHORIZE_URL}"
        f"?client_id={LARK_APP_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&state={state}"
        f"&scope={scopes}"
    )

    return url


def get_valid_access_token() -> Optional[str]:
    """
    Get a valid access token, refreshing if necessary

    This is the main function to call when you need an access token.
    It will:
    1. Load saved token
    2. Check if access token is valid
    3. If not, try to refresh using refresh_token
    4. If refresh_token is also expired, return None (need new authorization)

    Returns:
        str: Valid access token, or None if authorization is needed
    """
    print("=" * 70)
    print("LARK USER ACCESS TOKEN CHECK")
    print("=" * 70)

    # Load saved token
    token_data = load_token()

    if not token_data:
        print("✗ No saved token found. Authorization required.")
        print(f"\n📋 Please authorize the app:")
        print(f"1. Open this URL in browser:")
        print(f"   {get_authorization_url()}")
        print(f"2. Authorize the app")
        print(f"3. Copy the 'code' parameter from callback URL")
        print(f"4. Run: python lark_oauth.py --code YOUR_CODE")
        return None

    # Check if access token is valid
    if is_token_valid(token_data):
        return token_data['access_token']

    # Access token expired, try to refresh
    refresh_token = token_data.get('refresh_token')

    if not refresh_token:
        print("✗ No refresh token available. Re-authorization required.")
        print(f"\n📋 Please authorize the app:")
        print(f"   {get_authorization_url()}")
        return None

    # Check if refresh token is valid
    if not is_refresh_token_valid(token_data):
        print("✗ Refresh token expired. Re-authorization required.")
        print(f"\n📋 Please authorize the app:")
        print(f"   {get_authorization_url()}")
        return None

    # Refresh the token
    new_token_data = refresh_access_token(refresh_token)

    if new_token_data:
        return new_token_data['access_token']
    else:
        print("✗ Failed to refresh token. Re-authorization required.")
        print(f"\n📋 Please authorize the app:")
        print(f"   {get_authorization_url()}")
        return None


def main():
    """CLI interface for token management"""
    import argparse

    parser = argparse.ArgumentParser(description='Lark OAuth Token Manager')
    parser.add_argument('--code', type=str, help='Authorization code from OAuth callback')
    parser.add_argument('--check', action='store_true', help='Check token status')
    parser.add_argument('--refresh', action='store_true', help='Force refresh token')
    parser.add_argument('--url', action='store_true', help='Generate authorization URL')

    args = parser.parse_args()

    if args.url:
        print("📋 Authorization URL:")
        print(get_authorization_url())
        return

    if args.code:
        # Exchange code for token
        token_data = exchange_code_for_token(args.code, REDIRECT_URI)
        if token_data:
            print("\n✅ Token saved successfully!")
        return

    if args.refresh:
        # Force refresh
        token_data = load_token()
        if token_data and token_data.get('refresh_token'):
            refresh_access_token(token_data['refresh_token'])
        else:
            print("✗ No refresh token available")
        return

    # Default: check and get valid token
    token = get_valid_access_token()

    if token:
        print(f"\n✅ Valid access token available!")
        print(f"Token (first 50 chars): {token[:50]}...")
    else:
        print("\n❌ No valid token. Please authorize the app.")


if __name__ == "__main__":
    main()
