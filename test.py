from __future__ import annotations

import sys
import os
import json
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse

import requests
from decouple import config

# Google OAuth libs
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar'
BACKEND_CALLBACKS = (
    '/api/google/auth/callback/',
    '/api/google-oauth-callback/',
)


def _mask(s: str, show: int = 6) -> str:
    if not s:
        return ''
    return ('*' * max(0, len(s) - show)) + s[-show:]


def validate_env() -> dict:
    # Support both naming styles
    client_id = (config('GOOGLE_OAUTH_CLIENT_ID', default=None) or config('client_id', default='')).strip()
    client_secret = (config('GOOGLE_OAUTH_CLIENT_SECRET', default=None) or config('client_secret', default='')).strip()
    redirect_uri = (config('GOOGLE_OAUTH_REDIRECT_URI', default=None) or config('redirect_uris', default='')).strip()
    # If multiple URIs supplied, take the first
    if ',' in redirect_uri:
        redirect_uri = redirect_uri.split(',')[0].strip()
    elif ' ' in redirect_uri:
        redirect_uri = redirect_uri.split()[0].strip()
    refresh_token = os.getenv('GOOGLE_OAUTH_REFRESH_TOKEN', '').strip()

    errors = []

    if not client_id:
        errors.append('GOOGLE_OAUTH_CLIENT_ID is missing')
    elif not client_id.endswith('.apps.googleusercontent.com'):
        print('WARN: CLIENT_ID does not end with .apps.googleusercontent.com (double-check)')

    if not client_secret:
        errors.append('GOOGLE_OAUTH_CLIENT_SECRET is missing')

    if not redirect_uri:
        errors.append('GOOGLE_OAUTH_REDIRECT_URI is missing')
    else:
        parsed = urlparse(redirect_uri)
        if parsed.scheme not in ('http', 'https'):
            errors.append(f'Invalid scheme for REDIRECT_URI: {parsed.scheme}')
        if not parsed.netloc:
            errors.append('REDIRECT_URI missing host (use localhost:8000 or 127.0.0.1:8000)')
        if parsed.path not in BACKEND_CALLBACKS:
            print(
                f"WARN: Redirect path '{parsed.path}' does not match known callback routes: {BACKEND_CALLBACKS}\n"
                "      Ensure your backend exposes this exact path in backend/urls.py."
            )

    if errors:
        for e in errors:
            print(f'ERROR: {e}')
        sys.exit(1)

    print('Env OK:')
    print(f'  GOOGLE_OAUTH_CLIENT_ID    = {_mask(client_id)}')
    print(f'  GOOGLE_OAUTH_CLIENT_SECRET = {_mask(client_secret)}')
    print(f'  GOOGLE_OAUTH_REDIRECT_URI  = {redirect_uri}')
    if refresh_token:
        print('  GOOGLE_OAUTH_REFRESH_TOKEN = (provided)')

    return {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'refresh_token': refresh_token,
    }


def build_auth_url(cfg: dict) -> str:
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': cfg['client_id'],
                'client_secret': cfg['client_secret'],
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [cfg['redirect_uri']],
            }
        },
        scopes=[CALENDAR_SCOPE],
    )
    flow.redirect_uri = cfg['redirect_uri']
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        # Google requires lowercase string 'true' not boolean True for this param
        include_granted_scopes='true',
        prompt='consent',  # ensure refresh_token on subsequent consents
    )
    print('\nAuthorization URL (open in a browser to test OAuth):')
    print(authorization_url)
    print(f'State: {state}\n')
    return authorization_url


def try_refresh(cfg: dict) -> None:
    if not cfg.get('refresh_token'):
        print('No GOOGLE_OAUTH_REFRESH_TOKEN provided; skipping refresh test.')
        return
    print('Attempting refresh_token exchange...')
    creds = Credentials(
        token=None,
        refresh_token=cfg['refresh_token'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=cfg['client_id'],
        client_secret=cfg['client_secret'],
        scopes=[CALENDAR_SCOPE],
    )
    try:
        creds.refresh(Request())
        if creds.valid and creds.token:
            print('SUCCESS: Refresh token is valid, access token obtained.')
        else:
            print('WARN: Refresh call completed but credentials are not valid.')
    except Exception as e:
        print(f'ERROR: Refresh token invalid or not permitted: {e}')


if __name__ == '__main__':
    cfg = validate_env()
    build_auth_url(cfg)
    try_refresh(cfg)
    print('\nDone. If you see the Authorization URL, your credentials are structurally valid.')

    # Optional: End-to-end API flow helpers
    # Configure these environment variables to test bookings programmatically:
    # API_BASE_URL: defaults to http://localhost:8000/api
    # JWT_ACCESS: if present, used directly; otherwise TEST_USERNAME and TEST_PASSWORD used to sign in
    api_base = os.getenv('API_BASE_URL', 'http://localhost:8000/api').rstrip('/')
    tests_enabled = os.getenv('RUN_BOOKING_TESTS', '0') == '1'

    if tests_enabled:
        session = requests.Session()

        access_token = os.getenv('JWT_ACCESS', '')
        if not access_token:
            # Sign in to get JWT
            username = os.getenv('TEST_USERNAME', '')
            password = os.getenv('TEST_PASSWORD', '')
            if not username or not password:
                print('Set TEST_USERNAME and TEST_PASSWORD or JWT_ACCESS to run booking tests.')
                sys.exit(0)
            r = session.post(f"{api_base}/signin/", json={
                'username_or_email': username,
                'password': password,
            })
            if r.status_code != 200:
                print(f"Sign-in failed: {r.status_code} {r.text}")
                sys.exit(1)
            data = r.json()
            access_token = data.get('access')
            print('Signed in and obtained JWT access token.')

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

        # Example payloads
        now = datetime.now(dt_timezone.utc)
        cal_payload = {
            "summary": "Team Sync",
            "description": "Weekly sync",
            "start_datetime": (now + timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            "end_datetime": (now + timedelta(hours=2)).isoformat().replace('+00:00', 'Z'),
            "timezone": "UTC",
            "attendees": [],
            "location": "Virtual",
            "reminders": True
        }

        meet_payload = {
            "summary": "Client Call",
            "description": "Discuss requirements",
            "start_datetime": (now + timedelta(hours=3)).isoformat().replace('+00:00', 'Z'),
            "end_datetime": (now + timedelta(hours=4)).isoformat().replace('+00:00', 'Z'),
            "timezone": "UTC",
            "attendees": [],
            "send_notifications": True,
            "reminders": True
        }

        def handle_oauth_if_needed(resp, session_obj: requests.Session):
            if resp.status_code == 401:
                try:
                    j = resp.json()
                except Exception:
                    return False
                auth_url = j.get('auth_url')
                if not auth_url:
                    return False
                print('\nOAuth required. Open this URL in your browser, authorize, then paste the code parameter here:')
                print(auth_url)
                code = os.getenv('GOOGLE_OAUTH_CODE') or input('Enter the "code" from the redirected URL here: ').strip()
                # Call backend callback to store credentials in this session cookie jar
                cb_path = urlparse(cfg['redirect_uri']).path
                cb_url = f"{api_base}{cb_path.replace('/api', '') if cb_path.startswith('/api') else cb_path}"
                # Ensure we hit backend callback at the same host
                if not cb_url.startswith(api_base):
                    # Fallback: construct from api base and callback path
                    cb_url = api_base + cb_path
                rcb = session_obj.get(cb_url, params={'code': code})
                print(f"Callback response: {rcb.status_code} {rcb.text}")
                return True
            return False

        # Test calendar booking
        print('\nTesting calendar booking...')
        r1 = session.post(f"{api_base}/book-calendar/", headers=headers, data=json.dumps(cal_payload))
        if handle_oauth_if_needed(r1, session):
            r1 = session.post(f"{api_base}/book-calendar/", headers=headers, data=json.dumps(cal_payload))
        print(f"Calendar booking response: {r1.status_code} {r1.text}")

        # Test meet booking
        print('\nTesting meet booking...')
        r2 = session.post(f"{api_base}/book-meet/", headers=headers, data=json.dumps(meet_payload))
        if handle_oauth_if_needed(r2, session):
            r2 = session.post(f"{api_base}/book-meet/", headers=headers, data=json.dumps(meet_payload))
        print(f"Meet booking response: {r2.status_code} {r2.text}")

