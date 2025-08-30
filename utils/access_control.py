"""
Access Control Utilities for HailyDB
Handles admin authentication and authorization with session-based login
"""

import os
import hashlib
from flask import request, redirect, url_for, session

# Admin credentials (in production, these should be environment variables)
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@hailyai.com')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', hashlib.sha256('admin123'.encode()).hexdigest())

def verify_admin_credentials(email, password):
    """Verify admin email and password"""
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return email == ADMIN_EMAIL and password_hash == ADMIN_PASSWORD_HASH

def is_admin_access():
    """Check if the current request is from authenticated admin"""
    return session.get('admin_authenticated', False)

def require_admin_or_redirect():
    """Check admin access or redirect to documentation"""
    if not is_admin_access():
        return redirect(url_for('documentation'))
    return None

def login_admin():
    """Mark admin as logged in"""
    session['admin_authenticated'] = True
    session.permanent = True

def logout_admin():
    """Log out admin"""
    session.pop('admin_authenticated', None)