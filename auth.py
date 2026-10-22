"""
Taskflow Authentication & Role-Based Access Control (RBAC)
Team 2: Backend and Authentication
"""

from functools import wraps
from flask import session, redirect, url_for, flash, g, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskflow.db")

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def get_current_user():
    """Retrieves current user dict from session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    db = get_db()
    user = db.execute("""
        SELECT u.id, u.full_name, u.email, u.title, u.avatar_initials,
               r.name as role_name, r.label as role_label,
               d.name as department_name, d.code as department_code
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN departments d ON u.department_id = d.id
        WHERE u.id = ? AND u.is_active = 1;
    """, (user_id,)).fetchone()
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            flash('Please log in to access this area.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('login'))
            user = get_current_user()
            if not user or user['role_name'] not in allowed_roles:
                if request.is_json or request.path.startswith('/api/'):
                    return jsonify({'error': 'Forbidden: Insufficient privileges'}), 403
                flash('Access denied: Your role does not permit this action.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
