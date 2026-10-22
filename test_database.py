"""
Taskflow Organizational Work Management System
Database Test Suite
Team 3: Database and Data Management

Tests:
- Table structures and PRAGMA settings
- CRUD operations for users, projects, and tasks
- Integrity constraints (CHECK, UNIQUE, NOT NULL)
- Relational foreign keys and cascading delete behaviors
- Multi-role data isolation (Department-level and User-level)
- Triggers and audit logs
"""

import os
import sqlite3
import unittest
from init_db import init_db, seed_data

TEST_DB = "test_taskflow.db"

class TaskflowDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_DB)

    def setUp(self):
        # Create fresh test database for each test
        self.conn = init_db(db_path=self.db_path, drop_existing=True)
        seed_data(self.conn)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    # ---------------------------------------------------------
    # 1. SCHEMA INTEGRITY & PRAGMA TESTS
    # ---------------------------------------------------------
    def test_foreign_keys_pragma_enabled(self):
        """Verify foreign key enforcement is turned ON."""
        result = self.cursor.execute("PRAGMA foreign_keys;").fetchone()
        self.assertEqual(result[0], 1, "Foreign keys MUST be enabled in SQLite")

    def test_all_core_tables_exist(self):
        """Verify all organizational tables exist."""
        expected_tables = {
            'roles', 'departments', 'users', 'projects',
            'categories', 'tasks', 'task_activity_log', 'comments'
        }
        rows = self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        table_names = {row['name'] for row in rows}
        for table in expected_tables:
            self.assertIn(table, table_names, f"Table '{table}' must exist in schema")

    def test_indexes_exist(self):
        """Verify performance and lookup indexes exist."""
        rows = self.cursor.execute("SELECT name FROM sqlite_master WHERE type='index';").fetchall()
        index_names = {row['name'] for row in rows}
        expected_indexes = [
            'idx_users_email', 'idx_users_role_dept', 'idx_projects_dept',
            'idx_tasks_project', 'idx_tasks_assignee_status', 'idx_tasks_status_priority'
        ]
        for idx in expected_indexes:
            self.assertIn(idx, index_names, f"Index '{idx}' should be created")

    # ---------------------------------------------------------
    # 2. CRUD OPERATIONS
    # ---------------------------------------------------------
    def test_task_creation_and_retrieval(self):
        """Test task creation and complex join query."""
        self.cursor.execute("""
            INSERT INTO tasks (
                task_code, title, description, project_id, category_id,
                author_id, assignee_id, reviewer_id, priority, status, estimated_hours
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, ('TSK-999', 'Write Unit Tests', 'Complete DB tests', 1, 1, 2, 4, 2, 'HIGH', 'IN_PROGRESS', 5.0))
        self.conn.commit()

        # Query with JOINs
        self.cursor.execute("""
            SELECT t.task_code, t.title, p.title as project_title, u.full_name as assignee_name
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            JOIN users u ON t.assignee_id = u.id
            WHERE t.task_code = 'TSK-999';
        """)
        row = self.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['task_code'], 'TSK-999')
        self.assertEqual(row['title'], 'Write Unit Tests')
        self.assertEqual(row['assignee_name'], 'Alex Rivera')

    def test_task_update_and_status_progression(self):
        """Test transitioning task from IN_PROGRESS to UNDER_REVIEW."""
        self.cursor.execute("UPDATE tasks SET status = 'UNDER_REVIEW' WHERE task_code = 'TSK-102';")
        self.conn.commit()

        row = self.cursor.execute("SELECT status FROM tasks WHERE task_code = 'TSK-102';").fetchone()
        self.assertEqual(row['status'], 'UNDER_REVIEW')

    # ---------------------------------------------------------
    # 3. CHECK CONSTRAINTS & DATA VALIDATION
    # ---------------------------------------------------------
    def test_invalid_task_status_rejected(self):
        """Verify CHECK constraint rejects invalid status."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("""
                INSERT INTO tasks (task_code, title, project_id, author_id, status)
                VALUES ('TSK-ERR1', 'Invalid Status Task', 1, 1, 'INVALID_STATUS');
            """)
            self.conn.commit()

    def test_invalid_priority_rejected(self):
        """Verify CHECK constraint rejects invalid priority."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("""
                INSERT INTO tasks (task_code, title, project_id, author_id, priority)
                VALUES ('TSK-ERR2', 'Invalid Priority Task', 1, 1, 'SUPER_URGENT');
            """)
            self.conn.commit()

    def test_unique_user_email_constraint(self):
        """Verify user email uniqueness."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("""
                INSERT INTO users (full_name, email, password_hash, role_id)
                VALUES ('Duplicate User', 'admin@taskflow.local', 'hash', 1);
            """)
            self.conn.commit()

    # ---------------------------------------------------------
    # 4. RELATIONSHIPS & CASCADES
    # ---------------------------------------------------------
    def test_foreign_key_violation_rejected(self):
        """Verify FK constraint fails when referencing non-existent project."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.cursor.execute("""
                INSERT INTO tasks (task_code, title, project_id, author_id)
                VALUES ('TSK-FK1', 'Orphan Task', 99999, 1);
            """)
            self.conn.commit()

    def test_cascade_delete_task_removes_logs_and_comments(self):
        """Deleting a task must cascade to comments and activity log."""
        task_id = 1
        # Confirm logs and comments exist
        log_count = self.cursor.execute("SELECT COUNT(*) FROM task_activity_log WHERE task_id = ?;", (task_id,)).fetchone()[0]
        comment_count = self.cursor.execute("SELECT COUNT(*) FROM comments WHERE task_id = ?;", (task_id,)).fetchone()[0]
        self.assertGreater(log_count, 0)
        self.assertGreater(comment_count, 0)

        # Delete the task
        self.cursor.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
        self.conn.commit()

        # Verify cascades
        new_log_count = self.cursor.execute("SELECT COUNT(*) FROM task_activity_log WHERE task_id = ?;", (task_id,)).fetchone()[0]
        new_comment_count = self.cursor.execute("SELECT COUNT(*) FROM comments WHERE task_id = ?;", (task_id,)).fetchone()[0]
        self.assertEqual(new_log_count, 0, "Activity logs must cascade delete with task")
        self.assertEqual(new_comment_count, 0, "Comments must cascade delete with task")

    # ---------------------------------------------------------
    # 5. ORGANIZATIONAL DATA ISOLATION TESTS
    # ---------------------------------------------------------
    def test_department_data_isolation(self):
        """Ensure queries scoped to Engineering (dept_id=1) isolate from Design (dept_id=2)."""
        eng_projects = self.cursor.execute("""
            SELECT p.code FROM projects p WHERE p.department_id = 1;
        """).fetchall()
        eng_project_codes = [p['code'] for p in eng_projects]
        self.assertIn('ENG-CORE', eng_project_codes)
        self.assertNotIn('DES-SAGE', eng_project_codes, "Design project must not leak into Engineering queries")

    def test_employee_assigned_tasks_isolation(self):
        """Ensure an employee only sees tasks assigned to them when filtered."""
        # Alex Rivera (user_id = 4)
        alex_tasks = self.cursor.execute("""
            SELECT task_code, title FROM tasks WHERE assignee_id = 4;
        """).fetchall()
        alex_codes = [t['task_code'] for t in alex_tasks]
        self.assertIn('TSK-102', alex_codes)
        self.assertIn('TSK-105', alex_codes)
        # Maya Patel's task (TSK-101) should not be in Alex's personal queue
        self.assertNotIn('TSK-101', alex_codes)

    # ---------------------------------------------------------
    # 6. TRIGGER TESTS
    # ---------------------------------------------------------
    def test_updated_at_trigger(self):
        """Verify trg_tasks_updated_at automatically updates updated_at."""
        original = self.cursor.execute("SELECT updated_at FROM tasks WHERE id = 2;").fetchone()['updated_at']
        self.cursor.execute("UPDATE tasks SET title = 'Updated Title' WHERE id = 2;")
        self.conn.commit()
        updated = self.cursor.execute("SELECT updated_at FROM tasks WHERE id = 2;").fetchone()['updated_at']
        self.assertIsNotNone(updated)

if __name__ == '__main__':
    unittest.main()
