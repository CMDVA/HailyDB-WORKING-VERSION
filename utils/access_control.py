"""
Access Control Utilities for HailyDB
Handles admin authentication and authorization
"""

import os
from flask import request, redirect, url_for

def is_admin_access():
    """Check if the current request is from admin (localhost or specific patterns)"""
    # Check if request is from localhost/development
    if request.remote_addr in ['127.0.0.1', '::1'] or request.host.startswith('localhost'):
        return True
    
    # Check for Replit internal URLs (admin access)
    if '.replit.dev' in request.host or '.replit.app' in request.host:
        return True
    
    # Add other admin identification logic here (e.g., API keys, session tokens)
    # For now, we'll use a simple header-based check
    admin_key = request.headers.get('X-Admin-Key')
    if admin_key == os.environ.get('ADMIN_ACCESS_KEY', 'dev-admin-key'):
        return True
    
    return False

def require_admin_or_redirect():
    """Decorator/function to check admin access or redirect to documentation"""
    if not is_admin_access():
        # External users get redirected to the documentation page
        # Use the current domain with /documentation route for external access
        return redirect(url_for('documentation'))
    return None