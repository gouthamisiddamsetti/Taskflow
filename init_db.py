"""
Taskflow Organizational Work Management System
Database Initialization & Seeding Script
Team 3: Database and Data Management
"""

import os
import sqlite3
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "taskflow.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def get_db_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db(db_path=DB_PATH, schema_path=SCHEMA_PATH, drop_existing=True, verbose=True):
    """Initializes the SQLite database using the schema file."""
    if drop_existing and os.path.exists(db_path):
        os.remove(db_path)
        if verbose:
            print(f"[*] Removed existing database at: {db_path}")

    conn = get_db_connection(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    if verbose:
        print("[*] Database schema initialized with constraints, foreign keys, and indexes.")
    return conn

def seed_data(conn, verbose=True):
    """Populates the database with realistic organizational company data."""
    cursor = conn.cursor()

    # 1. Seed Roles
    roles = [
        ('ADMIN', 'Administrator', 'Full system configuration, organization oversight, and user management.'),
        ('TEAM_LEAD', 'Team Lead / Manager', 'Project sprint leadership, task assignment, workload balancing, and review sign-off.'),
        ('EMPLOYEE', 'Employee / Individual Contributor', 'Task execution, progress tracking, blocker escalation, and review submission.')
    ]
    cursor.executemany("INSERT INTO roles (name, label, description) VALUES (?, ?, ?);", roles)

    # 2. Seed Departments
    departments = [
        ('ENG', 'Engineering & Infrastructure', 'Core software development, cloud infrastructure, and database engineering.'),
        ('DES', 'Product Design & UX', 'Design systems, user research, wireframes, and design polish.'),
        ('MKT', 'Growth & Marketing', 'Product launches, customer acquisition, and marketing automation.')
    ]
    cursor.executemany("INSERT INTO departments (code, name, description) VALUES (?, ?, ?);", departments)

    # 3. Seed Users
    # Default password for all seed accounts: "password123"
    default_pw = generate_password_hash("password123")
    
    users = [
        # Admin
        ('Sarah Jenkins', 'admin@taskflow.local', default_pw, 1, 1, 'VP of Technology & Operations', 'SJ'),
        # Team Leads
        ('David Chen', 'lead.eng@taskflow.local', default_pw, 2, 1, 'Staff Software Engineer & Team Lead', 'DC'),
        ('Elena Rostova', 'lead.des@taskflow.local', default_pw, 2, 2, 'Principal UX Lead', 'ER'),
        # Employees (ICs)
        ('Alex Rivera', 'alex.dev@taskflow.local', default_pw, 3, 1, 'Full Stack Engineer', 'AR'),
        ('Maya Patel', 'maya.dev@taskflow.local', default_pw, 3, 1, 'Database & Backend Specialist', 'MP'),
        ('Liam Vance', 'liam.des@taskflow.local', default_pw, 3, 2, 'Senior Product Designer', 'LV'),
        ('Zoe Martinez', 'zoe.mkt@taskflow.local', default_pw, 3, 3, 'Growth Marketing Lead', 'ZM')
    ]
    cursor.executemany("""
        INSERT INTO users (full_name, email, password_hash, role_id, department_id, title, avatar_initials)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, users)

    # 4. Seed Categories
    categories = [
        ('Architecture', '#4E6B56'),
        ('Backend API', '#2F4336'),
        ('Frontend UI', '#84A98C'),
        ('Database', '#52796F'),
        ('DevOps', '#354F52'),
        ('Design System', '#CAD2C5')
    ]
    cursor.executemany("INSERT INTO categories (name, color_hex) VALUES (?, ?);", categories)

    # 5. Seed Projects
    target_q4 = (date.today() + timedelta(days=45)).isoformat()
    target_q1 = (date.today() + timedelta(days=90)).isoformat()
    projects = [
        ('ENG-CORE', 'Enterprise Platform v2.0', 'Re-architecting organizational workflows, real-time collaboration, and audit logs.', 1, 2, 'ACTIVE', target_q4),
        ('ENG-DATA', 'High Performance DB & Cache Layer', 'Database migration to SQLite WAL mode with indexed query optimization.', 1, 2, 'ACTIVE', target_q4),
        ('DES-SAGE', 'Cream & Sage Design System', 'Comprehensive component library and visual tokens for ergonomic enterprise workflows.', 2, 3, 'ACTIVE', target_q1)
    ]
    cursor.executemany("""
        INSERT INTO projects (code, title, description, department_id, lead_id, status, target_date)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, projects)

    # 6. Seed Tasks
    # Statuses: 'BACKLOG', 'TODO', 'IN_PROGRESS', 'UNDER_REVIEW', 'DONE', 'BLOCKED'
    # Priorities: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    today = date.today()
    tasks = [
        (
            'TSK-101', 'Design Relational Schema & Constraints',
            'Define tables, foreign keys with ON DELETE rules, check constraints, and performance indexes.',
            1, 4, 2, 5, 2, 'CRITICAL', 'DONE', 16, 16, None,
            (today - timedelta(days=2)).isoformat(), (datetime.now() - timedelta(days=2)).isoformat()
        ),
        (
            'TSK-102', 'Implement Role-Based Access Control Middleware',
            'Develop Flask decorators to enforce Admin, Team Lead, and Employee authorization boundaries.',
            1, 2, 2, 4, 2, 'HIGH', 'IN_PROGRESS', 20, 12, None,
            (today + timedelta(days=3)).isoformat(), None
        ),
        (
            'TSK-103', 'Cream & Sage Green Design Tokens',
            'Establish CSS custom properties for warm cream background, sage green accents, and typography hierarchy.',
            3, 6, 3, 6, 3, 'HIGH', 'UNDER_REVIEW', 12, 11, None,
            (today + timedelta(days=1)).isoformat(), None
        ),
        (
            'TSK-104', 'Multi-tenant Data Isolation Unit Tests',
            'Verify SQLite foreign key enforcement, cross-department data isolation, and unauthorized mutation defense.',
            2, 4, 2, 5, 2, 'CRITICAL', 'IN_PROGRESS', 14, 8, None,
            (today + timedelta(days=4)).isoformat(), None
        ),
        (
            'TSK-105', 'Third-party OAuth & SSO Provider Integration',
            'Implement Google Workspace Single Sign-On and enterprise SAML gateway.',
            1, 2, 2, 4, 2, 'MEDIUM', 'BLOCKED', 24, 6, 'Awaiting Google Cloud enterprise client ID credentials from IT security.',
            (today + timedelta(days=7)).isoformat(), None
        ),
        (
            'TSK-106', 'Executive Analytics Dashboard Aggregation',
            'Build aggregation endpoints for department velocity, task throughput, and workload heatmaps.',
            1, 2, 1, 4, 1, 'HIGH', 'TODO', 18, 0, None,
            (today + timedelta(days=6)).isoformat(), None
        ),
        (
            'TSK-107', 'Mobile Responsive Layout & Sidebar Collapse',
            'Ensure navigation drawer and task kanban board gracefully adapt to tablet and mobile screens.',
            3, 3, 3, 6, 3, 'MEDIUM', 'TODO', 10, 0, None,
            (today + timedelta(days=5)).isoformat(), None
        ),
        (
            'TSK-108', 'Audit Trail Activity Logging Hook',
            'Automatically log state transitions, assignment changes, and review approvals into task_activity_log.',
            2, 4, 2, 5, 2, 'HIGH', 'UNDER_REVIEW', 8, 8, None,
            (today + timedelta(days=1)).isoformat(), None
        )
    ]

    cursor.executemany("""
        INSERT INTO tasks (
            task_code, title, description, project_id, category_id, author_id,
            assignee_id, reviewer_id, priority, status, estimated_hours, logged_hours,
            blocker_reason, due_date, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, tasks)

    # 7. Seed Task Activity Logs
    activity_logs = [
        (1, 2, 'CREATED', 'Task created and assigned to Maya Patel'),
        (1, 5, 'STATUS_CHANGE', 'Status changed from TODO to IN_PROGRESS'),
        (1, 5, 'STATUS_CHANGE', 'Status changed from IN_PROGRESS to UNDER_REVIEW'),
        (1, 2, 'APPROVED', 'David Chen approved deliverables and marked task DONE'),
        (2, 2, 'CREATED', 'Task created and assigned to Alex Rivera'),
        (2, 4, 'STATUS_CHANGE', 'Status changed from TODO to IN_PROGRESS (12h logged)'),
        (5, 4, 'BLOCKED', 'Alex Rivera flagged task as BLOCKED: Awaiting Google Cloud client credentials'),
        (3, 3, 'SUBMIT_REVIEW', 'Liam Vance submitted design tokens for review with Figma specs')
    ]
    cursor.executemany("""
        INSERT INTO task_activity_log (task_id, user_id, action, details)
        VALUES (?, ?, ?, ?);
    """, activity_logs)

    # 8. Seed Comments
    comments = [
        (1, 5, 'Initial schema definition passed all SQLite foreign key stress tests with flying colors.'),
        (1, 2, 'Excellent work on the triggers and indexing strategy. Merged to develop.'),
        (5, 4, 'Submitted an internal IT ticket #4092 to obtain the OAuth client secret.'),
        (5, 2, 'Thanks Alex, escalating to Sarah Jenkins for prioritized IT review.'),
        (3, 6, 'Cream palette (#FBF9F5) and Sage Green (#4E6B56) provide 7:1 contrast ratio compliance.')
    ]
    cursor.executemany("""
        INSERT INTO comments (task_id, user_id, content)
        VALUES (?, ?, ?);
    """, comments)

    conn.commit()
    if verbose:
        print("[*] Seed data populated successfully with real company hierarchy, projects, and tasks.")

if __name__ == "__main__":
    conn = init_db()
    seed_data(conn)
    conn.close()
    print("[OK] Taskflow database initialization complete!")
