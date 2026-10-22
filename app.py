"""
Taskflow Organizational Work Management System
Flask Application & API Service
Teams 2 & 4: Backend, Authentication, and Integration
"""

import os
import sqlite3
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from auth import get_db, get_current_user, login_required, role_required

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "taskflow-sage-cream-secure-key-2026")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskflow.db")

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_user():
    return {'current_user': get_current_user()}

# -------------------------------------------------------------
# AUTHENTICATION ROUTES
# -------------------------------------------------------------
@app.route('/')
def index():
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard_router'))
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ? AND is_active = 1;", (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for('dashboard_router'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role_id = int(request.form.get('role_id', 3)) # Default: Employee
        department_id = int(request.form.get('department_id', 1))
        
        if not full_name or not email or not password:
            flash("All fields are required.", "warning")
            return render_template('signup.html')
            
        initials = "".join([part[0].upper() for part in full_name.split()[:2]]) or "U"
        pw_hash = generate_password_hash(password)
        
        db = get_db()
        try:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO users (full_name, email, password_hash, role_id, department_id, avatar_initials, title)
                VALUES (?, ?, ?, ?, ?, ?, 'Team Member');
            """, (full_name, email, pw_hash, role_id, department_id, initials))
            db.commit()
            session['user_id'] = cursor.lastrowid
            flash("Account created successfully! Welcome to Taskflow.", "success")
            return redirect(url_for('dashboard_router'))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "danger")
            
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('login'))

@app.route('/auth/switch-demo-role/<role_name>')
def switch_demo_role(role_name):
    """Convenience endpoint for review and demoing all 3 role perspectives."""
    role_name = role_name.upper()
    db = get_db()
    user = db.execute("""
        SELECT u.id FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE r.name = ? AND u.is_active = 1
        LIMIT 1;
    """, (role_name,)).fetchone()
    
    if user:
        session['user_id'] = user['id']
        flash(f"Switched view to {role_name} persona.", "info")
    return redirect(url_for('dashboard_router'))

# -------------------------------------------------------------
# ROLE DASHBOARD ROUTER & PAGES
# -------------------------------------------------------------
@app.route('/dashboard')
@login_required
def dashboard_router():
    user = get_current_user()
    role = user['role_name']
    if role == 'ADMIN':
        return redirect(url_for('admin_dashboard'))
    elif role == 'TEAM_LEAD':
        return redirect(url_for('lead_dashboard'))
    else:
        return redirect(url_for('employee_dashboard'))

@app.route('/dashboard/admin')
@role_required('ADMIN')
def admin_dashboard():
    db = get_db()
    # Company-wide stats
    total_users = db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1;").fetchone()[0]
    total_projects = db.execute("SELECT COUNT(*) FROM projects;").fetchone()[0]
    total_tasks = db.execute("SELECT COUNT(*) FROM tasks;").fetchone()[0]
    completed_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status = 'DONE';").fetchone()[0]
    completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks else 0
    
    # Department breakdown
    dept_stats = db.execute("""
        SELECT d.id, d.name, d.code,
               COUNT(DISTINCT u.id) as user_count,
               COUNT(DISTINCT p.id) as project_count,
               COUNT(DISTINCT t.id) as task_count
        FROM departments d
        LEFT JOIN users u ON u.department_id = d.id
        LEFT JOIN projects p ON p.department_id = d.id
        LEFT JOIN tasks t ON t.project_id = p.id
        GROUP BY d.id;
    """).fetchall()
    
    # Recent audit events
    audit_logs = db.execute("""
        SELECT l.*, t.task_code, t.title as task_title, u.full_name as user_name
        FROM task_activity_log l
        JOIN tasks t ON l.task_id = t.id
        LEFT JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC LIMIT 10;
    """).fetchall()

    users_list = db.execute("""
        SELECT u.*, r.label as role_label, d.name as department_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN departments d ON u.department_id = d.id
        ORDER BY u.created_at DESC;
    """).fetchall()

    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_projects=total_projects,
                           total_tasks=total_tasks,
                           completion_rate=completion_rate,
                           dept_stats=dept_stats,
                           audit_logs=audit_logs,
                           users_list=users_list)

@app.route('/dashboard/lead')
@role_required('ADMIN', 'TEAM_LEAD')
def lead_dashboard():
    db = get_db()
    user = get_current_user()
    
    # Team members and workload
    team_members = db.execute("""
        SELECT u.id, u.full_name, u.avatar_initials, u.title,
               COUNT(t.id) as assigned_count,
               SUM(CASE WHEN t.status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress_count,
               SUM(CASE WHEN t.status = 'BLOCKED' THEN 1 ELSE 0 END) as blocked_count
        FROM users u
        LEFT JOIN tasks t ON t.assignee_id = u.id AND t.status != 'DONE'
        GROUP BY u.id
        ORDER BY assigned_count DESC;
    """).fetchall()

    # Tasks needing Lead Review
    pending_reviews = db.execute("""
        SELECT t.*, u.full_name as assignee_name, p.title as project_title, c.name as category_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        JOIN projects p ON t.project_id = p.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.status = 'UNDER_REVIEW'
        ORDER BY t.updated_at DESC;
    """).fetchall()

    # Active blockers needing intervention
    blockers = db.execute("""
        SELECT t.*, u.full_name as assignee_name, p.title as project_title
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        JOIN projects p ON t.project_id = p.id
        WHERE t.status = 'BLOCKED'
        ORDER BY t.updated_at DESC;
    """).fetchall()

    # All active team tasks
    tasks = db.execute("""
        SELECT t.*, u.full_name as assignee_name, u.avatar_initials,
               p.title as project_title, c.name as category_name, c.color_hex as category_color
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        JOIN projects p ON t.project_id = p.id
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY 
            CASE t.priority 
                WHEN 'CRITICAL' THEN 1 
                WHEN 'HIGH' THEN 2 
                WHEN 'MEDIUM' THEN 3 
                ELSE 4 
            END;
    """).fetchall()

    projects = db.execute("SELECT id, title, code FROM projects;").fetchall()
    assignees = db.execute("SELECT id, full_name, title FROM users WHERE is_active = 1;").fetchall()
    categories = db.execute("SELECT id, name FROM categories;").fetchall()

    return render_template('lead_dashboard.html',
                           team_members=team_members,
                           pending_reviews=pending_reviews,
                           blockers=blockers,
                           tasks=tasks,
                           projects=projects,
                           assignees=assignees,
                           categories=categories)

@app.route('/dashboard/employee')
@login_required
def employee_dashboard():
    db = get_db()
    user = get_current_user()
    
    # "Assigned to Me" tasks
    my_tasks = db.execute("""
        SELECT t.*, p.title as project_title, c.name as category_name, c.color_hex as category_color,
               lead.full_name as lead_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        LEFT JOIN categories c ON t.category_id = c.id
        LEFT JOIN users lead ON t.reviewer_id = lead.id
        WHERE t.assignee_id = ?
        ORDER BY 
            CASE t.status
                WHEN 'BLOCKED' THEN 1
                WHEN 'IN_PROGRESS' THEN 2
                WHEN 'TODO' THEN 3
                WHEN 'UNDER_REVIEW' THEN 4
                ELSE 5
            END,
            CASE t.priority
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                ELSE 4
            END;
    """, (user['id'],)).fetchall()

    # Summary metrics for employee
    active_count = sum(1 for t in my_tasks if t['status'] in ('TODO', 'IN_PROGRESS'))
    review_count = sum(1 for t in my_tasks if t['status'] == 'UNDER_REVIEW')
    blocked_count = sum(1 for t in my_tasks if t['status'] == 'BLOCKED')
    done_count = sum(1 for t in my_tasks if t['status'] == 'DONE')

    return render_template('employee_dashboard.html',
                           my_tasks=my_tasks,
                           active_count=active_count,
                           review_count=review_count,
                           blocked_count=blocked_count,
                           done_count=done_count)

# -------------------------------------------------------------
# WORKSPACES: PROJECTS, TEAMS, & ACTIVITY LOGS
# -------------------------------------------------------------
@app.route('/projects')
@login_required
def projects_view():
    db = get_db()
    projects = db.execute("""
        SELECT p.*, d.name as department_name, d.code as department_code,
               u.full_name as lead_name, u.avatar_initials as lead_initials,
               COUNT(t.id) as total_tasks,
               SUM(CASE WHEN t.status = 'DONE' THEN 1 ELSE 0 END) as done_tasks,
               SUM(CASE WHEN t.status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as in_progress_tasks,
               SUM(CASE WHEN t.status = 'BLOCKED' THEN 1 ELSE 0 END) as blocked_tasks
        FROM projects p
        JOIN departments d ON p.department_id = d.id
        LEFT JOIN users u ON p.lead_id = u.id
        LEFT JOIN tasks t ON t.project_id = p.id
        GROUP BY p.id
        ORDER BY p.created_at DESC;
    """).fetchall()

    tasks_by_project = {}
    for proj in projects:
        t_list = db.execute("""
            SELECT t.*, u.full_name as assignee_name, c.name as category_name
            FROM tasks t
            LEFT JOIN users u ON t.assignee_id = u.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.project_id = ?
            ORDER BY t.created_at DESC;
        """, (proj['id'],)).fetchall()
        tasks_by_project[proj['id']] = t_list

    return render_template('projects.html', projects=projects, tasks_by_project=tasks_by_project)

@app.route('/teams')
@login_required
def teams_view():
    db = get_db()
    users = db.execute("""
        SELECT u.*, r.label as role_label, d.name as department_name, d.code as department_code,
               COUNT(t.id) as total_tasks,
               SUM(CASE WHEN t.status = 'IN_PROGRESS' THEN 1 ELSE 0 END) as active_tasks,
               SUM(CASE WHEN t.status = 'BLOCKED' THEN 1 ELSE 0 END) as blocked_tasks,
               SUM(CASE WHEN t.status = 'DONE' THEN 1 ELSE 0 END) as done_tasks
        FROM users u
        JOIN roles r ON u.role_id = r.id
        LEFT JOIN departments d ON u.department_id = d.id
        LEFT JOIN tasks t ON t.assignee_id = u.id
        WHERE u.is_active = 1
        GROUP BY u.id
        ORDER BY u.role_id ASC, active_tasks DESC;
    """).fetchall()

    tasks_by_user = {}
    for u in users:
        u_tasks = db.execute("""
            SELECT t.*, p.title as project_title, c.name as category_name
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.assignee_id = ? AND t.status != 'DONE'
            ORDER BY t.priority = 'CRITICAL' DESC, t.priority = 'HIGH' DESC;
        """, (u['id'],)).fetchall()
        tasks_by_user[u['id']] = u_tasks

    return render_template('teams.html', users=users, tasks_by_user=tasks_by_user)

@app.route('/activity')
@login_required
def activity_view():
    db = get_db()
    action_filter = request.args.get('action', 'ALL')
    
    if action_filter != 'ALL':
        logs = db.execute("""
            SELECT l.*, t.task_code, t.title as task_title, u.full_name as user_name, u.avatar_initials
            FROM task_activity_log l
            JOIN tasks t ON l.task_id = t.id
            LEFT JOIN users u ON l.user_id = u.id
            WHERE l.action = ?
            ORDER BY l.created_at DESC;
        """, (action_filter,)).fetchall()
    else:
        logs = db.execute("""
            SELECT l.*, t.task_code, t.title as task_title, u.full_name as user_name, u.avatar_initials
            FROM task_activity_log l
            JOIN tasks t ON l.task_id = t.id
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.created_at DESC;
        """).fetchall()

    return render_template('activity.html', logs=logs, current_filter=action_filter)

# -------------------------------------------------------------
# RESTFUL API ENDPOINTS FOR TASKS & WORKFLOWS
# -------------------------------------------------------------
@app.route('/api/tasks', methods=['GET', 'POST'])
@login_required
def api_tasks():
    db = get_db()
    user = get_current_user()
    
    if request.method == 'POST':
        data = request.get_json() or request.form
        title = data.get('title')
        project_id = data.get('project_id')
        assignee_id = data.get('assignee_id') or None
        priority = data.get('priority', 'MEDIUM')
        category_id = data.get('category_id') or None
        description = data.get('description', '')
        est_hours = float(data.get('estimated_hours', 0.0) or 0.0)
        due_date = data.get('due_date') or None

        if not title or not project_id:
            return jsonify({'error': 'Title and Project are required'}), 400

        # Generate unique task code
        task_count = db.execute("SELECT COUNT(*) FROM tasks;").fetchone()[0] + 101
        task_code = f"TSK-{task_count}"

        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO tasks (
                task_code, title, description, project_id, category_id,
                author_id, assignee_id, reviewer_id, priority, status,
                estimated_hours, due_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'TODO', ?, ?);
        """, (task_code, title, description, project_id, category_id,
              user['id'], assignee_id, user['id'], priority, est_hours, due_date))
        
        task_id = cursor.lastrowid
        # Log action
        cursor.execute("""
            INSERT INTO task_activity_log (task_id, user_id, action, details)
            VALUES (?, ?, 'CREATED', ?);
        """, (task_id, user['id'], f"Created task and assigned to user #{assignee_id}"))
        db.commit()

        return jsonify({'message': 'Task created successfully', 'task_id': task_id, 'task_code': task_code}), 201

    # GET: filtered tasks
    tasks = db.execute("""
        SELECT t.*, u.full_name as assignee_name, p.title as project_title, c.name as category_name
        FROM tasks t
        LEFT JOIN users u ON t.assignee_id = u.id
        JOIN projects p ON t.project_id = p.id
        LEFT JOIN categories c ON t.category_id = c.id
        ORDER BY t.created_at DESC;
    """).fetchall()
    return jsonify([dict(t) for t in tasks])

@app.route('/api/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_task_status(task_id):
    db = get_db()
    user = get_current_user()
    data = request.get_json() or request.form
    new_status = data.get('status')
    
    valid_statuses = ('BACKLOG', 'TODO', 'IN_PROGRESS', 'UNDER_REVIEW', 'DONE', 'BLOCKED')
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status: {new_status}'}), 400

    task = db.execute("SELECT * FROM tasks WHERE id = ?;", (task_id,)).fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    completed_at = datetime.now().isoformat() if new_status == 'DONE' else None

    db.execute("""
        UPDATE tasks 
        SET status = ?, completed_at = COALESCE(?, completed_at)
        WHERE id = ?;
    """, (new_status, completed_at, task_id))

    db.execute("""
        INSERT INTO task_activity_log (task_id, user_id, action, details)
        VALUES (?, ?, 'STATUS_CHANGE', ?);
    """, (task_id, user['id'], f"Status transitioned from {task['status']} to {new_status}"))
    db.commit()

    return jsonify({'success': True, 'new_status': new_status})

@app.route('/api/tasks/<int:task_id>/blocker', methods=['POST'])
@login_required
def report_blocker(task_id):
    db = get_db()
    user = get_current_user()
    data = request.get_json() or request.form
    reason = data.get('blocker_reason', '').strip()
    
    if not reason:
        return jsonify({'error': 'Blocker reason is required'}), 400

    db.execute("""
        UPDATE tasks 
        SET status = 'BLOCKED', blocker_reason = ? 
        WHERE id = ?;
    """, (reason, task_id))

    db.execute("""
        INSERT INTO task_activity_log (task_id, user_id, action, details)
        VALUES (?, ?, 'BLOCKED', ?);
    """, (task_id, user['id'], f"Task flagged as BLOCKED: {reason}"))
    db.commit()

    return jsonify({'success': True, 'message': 'Blocker reported to Lead'})

@app.route('/api/tasks/<int:task_id>/review', methods=['POST'])
@login_required
def submit_or_approve_review(task_id):
    db = get_db()
    user = get_current_user()
    data = request.get_json() or request.form
    action = data.get('action') # 'SUBMIT' or 'APPROVE' or 'REJECT'
    notes = data.get('notes', '')

    if action == 'SUBMIT':
        db.execute("UPDATE tasks SET status = 'UNDER_REVIEW' WHERE id = ?;", (task_id,))
        db.execute("""
            INSERT INTO task_activity_log (task_id, user_id, action, details)
            VALUES (?, ?, 'SUBMIT_REVIEW', ?);
        """, (task_id, user['id'], f"Submitted work for review: {notes}"))
    elif action == 'APPROVE':
        if user['role_name'] not in ('ADMIN', 'TEAM_LEAD'):
            return jsonify({'error': 'Only Team Leads and Admins can approve tasks'}), 403
        db.execute("""
            UPDATE tasks 
            SET status = 'DONE', completed_at = CURRENT_TIMESTAMP 
            WHERE id = ?;
        """, (task_id,))
        db.execute("""
            INSERT INTO task_activity_log (task_id, user_id, action, details)
            VALUES (?, ?, 'APPROVED', ?);
        """, (task_id, user['id'], f"Work approved and marked DONE: {notes}"))
    elif action == 'REJECT':
        if user['role_name'] not in ('ADMIN', 'TEAM_LEAD'):
            return jsonify({'error': 'Only Team Leads and Admins can reject tasks'}), 403
        db.execute("UPDATE tasks SET status = 'IN_PROGRESS' WHERE id = ?;", (task_id,))
        db.execute("""
            INSERT INTO task_activity_log (task_id, user_id, action, details)
            VALUES (?, ?, 'REJECTED', ?);
        """, (task_id, user['id'], f"Changes requested: {notes}"))
    else:
        return jsonify({'error': 'Invalid review action'}), 400

    db.commit()
    return jsonify({'success': True, 'action': action})

@app.route('/api/tasks/<int:task_id>/comments', methods=['GET', 'POST'])
@login_required
def task_comments(task_id):
    db = get_db()
    user = get_current_user()

    if request.method == 'POST':
        data = request.get_json() or request.form
        content = data.get('content', '').strip()
        if not content:
            return jsonify({'error': 'Comment content cannot be empty'}), 400
        
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO comments (task_id, user_id, content)
            VALUES (?, ?, ?);
        """, (task_id, user['id'], content))
        db.commit()
        return jsonify({'success': True, 'comment_id': cursor.lastrowid}), 201

    comments = db.execute("""
        SELECT c.*, u.full_name as author_name, u.avatar_initials
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.task_id = ?
        ORDER BY c.created_at ASC;
    """, (task_id,)).fetchall()
    return jsonify([dict(c) for c in comments])

if __name__ == '__main__':
    # Running locally for verification and demo
    app.run(host='127.0.0.1', port=5000, debug=True)
