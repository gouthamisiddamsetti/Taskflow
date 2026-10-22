-- Taskflow Organizational Work Management System
-- Database Schema (SQLite)
-- Team 3: Database and Data Management

PRAGMA foreign_keys = ON;

-- 1. ROLES TABLE
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE CHECK(name IN ('ADMIN', 'TEAM_LEAD', 'EMPLOYEE')),
    label TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. DEPARTMENTS TABLE
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    department_id INTEGER,
    title TEXT,
    avatar_initials TEXT,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT,
    FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE SET NULL
);

-- 4. PROJECTS TABLE
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    department_id INTEGER NOT NULL,
    lead_id INTEGER,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('PLANNING', 'ACTIVE', 'PAUSED', 'COMPLETED')),
    target_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments (id) ON DELETE CASCADE,
    FOREIGN KEY (lead_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 5. CATEGORIES / TAGS TABLE
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color_hex TEXT NOT NULL DEFAULT '#608066'
);

-- 6. TASKS TABLE
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    git_url TEXT,
    project_id INTEGER NOT NULL,
    category_id INTEGER,
    author_id INTEGER NOT NULL,
    assignee_id INTEGER,
    reviewer_id INTEGER,
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status TEXT NOT NULL DEFAULT 'TODO' CHECK(status IN ('BACKLOG', 'TODO', 'IN_PROGRESS', 'UNDER_REVIEW', 'DONE', 'BLOCKED')),
    estimated_hours REAL DEFAULT 0,
    logged_hours REAL DEFAULT 0,
    blocker_reason TEXT,
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL,
    FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (assignee_id) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 7. TASK ACTIVITY AUDIT LOG TABLE
CREATE TABLE IF NOT EXISTS task_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER,
    action TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- 8. TASK COMMENTS TABLE
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- 9. EMPLOYEE WORK SUBMISSIONS
CREATE TABLE IF NOT EXISTS task_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL UNIQUE,
    submitted_by INTEGER NOT NULL,
    git_url TEXT NOT NULL,
    description TEXT NOT NULL,
    attachments_json TEXT NOT NULL DEFAULT '[]',
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE CASCADE
);

-- INDEXES FOR PERFORMANCE AND ROLE-BASED QUERY ACCELERATION
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role_dept ON users(role_id, department_id);
CREATE INDEX IF NOT EXISTS idx_projects_dept ON projects(department_id);
CREATE INDEX IF NOT EXISTS idx_projects_lead ON projects(lead_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assignee_status ON tasks(assignee_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_activity_task ON task_activity_log(task_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_task ON comments(task_id, created_at ASC);

-- TRIGGER: Auto-update updated_at timestamp on task modification
CREATE TRIGGER IF NOT EXISTS trg_tasks_updated_at
AFTER UPDATE ON tasks
FOR EACH ROW
BEGIN
    UPDATE tasks 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = OLD.id;
END;
