#!/usr/bin/env python3
"""
Credential sanity checker for Google OAuth settings in .env

What this script does:
- Loads GOOGLE_OAUTH_CLIENT_ID/SECRET/REDIRECT_URI from .env (via python-decouple)
- Validates basic format and that redirect path matches backend routes
- Builds a Google OAuth Flow and prints a working authorization URL
- Optionally: if GOOGLE_OAUTH_REFRESH_TOKEN is set, tries a token refresh

Usage:
  python test.py

Optional env (for advanced check):
  GOOGLE_OAUTH_REFRESH_TOKEN=<refresh_token>

Note: This script doesn't complete the OAuth code exchange automatically.
      It just validates configuration and produces the consent URL.
"""
from __future__ import annotations

import sys
import os
from urllib.parse import urlparse

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
    client_id = config('GOOGLE_OAUTH_CLIENT_ID', default='').strip()
    client_secret = config('GOOGLE_OAUTH_CLIENT_SECRET', default='').strip()
    redirect_uri = config('GOOGLE_OAUTH_REDIRECT_URI', default='').strip()
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
