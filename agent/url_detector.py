"""URL type detection utilities for routing to appropriate analysis agents.

This module provides utilities to detect whether a URL is a Google Play Store app
link or a regular website URL, enabling dynamic routing to the correct agent.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs


def extract_app_id_from_play_store_url(url: str) -> Optional[str]:
   
    if not url:
        return None
    
    try:
        parsed = urlparse(url)
        
        # Check if domain is Google Play Store
        if 'play.google.com' not in parsed.netloc:
            return None
        
        # Check if path is for app details
        if '/store/apps/details' not in parsed.path:
            return None
        
        # Extract ID from query parameters
        params = parse_qs(parsed.query)
        app_ids = params.get('id', [])
        
        if app_ids and app_ids[0]:
            return app_ids[0]
        
        return None
    except Exception:
        return None


def is_play_store_url(url: str) -> bool:
    """Check if URL is a Google Play Store app link.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is a Play Store app link, False otherwise
    """
    return extract_app_id_from_play_store_url(url) is not None


def detect_url_type(url: str) -> Tuple[str, Optional[str]]:
    """Detect URL type and extract relevant identifier.
    
    Args:
        url: URL to analyze
        
    Returns:
        Tuple of (type, identifier) where:
        - type: 'app' for Play Store links, 'website' for regular URLs
        - identifier: app package ID for apps, original URL for websites
        
    Examples:
        >>> detect_url_type('https://play.google.com/store/apps/details?id=com.example.app')
        ('app', 'com.example.app')
        >>> detect_url_type('https://www.example.com')
        ('website', 'https://www.example.com')
    """
    if not url or not isinstance(url, str):
        return ('website', url)
    
    # Check for Play Store URL
    app_id = extract_app_id_from_play_store_url(url)
    if app_id:
        return ('app', app_id)
    
    # Default to website
    return ('website', url)


def normalize_url(url: str) -> str:
    """Normalize URL by ensuring it has a proper scheme.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL with https:// scheme
    """
    if not url:
        return url
    
    url = url.strip()
    
    # Skip normalization for Play Store URLs
    if 'play.google.com' in url:
        if not url.startswith('http://') and not url.startswith('https://'):
            return f'https://{url}'
        return url
    
    # For regular URLs, add https:// if missing
    if not url.startswith('https://') and not url.startswith('http://'):
        url = f'https://{url}'
    
    return url
