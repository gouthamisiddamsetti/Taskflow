"""
Taskflow Integration & End-to-End Test Suite
Team 4: Integration, Testing and DevOps

Tests:
- HTTP endpoints and template rendering
- Authentication and session handling
- Role-Based Access Control (RBAC) boundaries
- Full Task Lifecycle (Create -> Start -> Block -> Unblock -> Review -> Approve)
- Activity logging verification
"""

import os
import unittest
import sqlite3
from app import app
from init_db import init_db, seed_data

TEST_DB = "test_integration.db"

class TaskflowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_DB)
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False

    def setUp(self):
        # Override DB_PATH for testing
        import app as app_module
        import auth as auth_module
        app_module.DB_PATH = self.db_path
        auth_module.DB_PATH = self.db_path

        conn = init_db(db_path=self.db_path, drop_existing=True, verbose=False)
        seed_data(conn, verbose=False)
        conn.close()

        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def login_as(self, email, password="password123"):
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # 1. PUBLIC ROUTES
    def test_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Engineered for Organizations", response.data)
        self.assertIn(b"Taskflow", response.data)

    def test_login_page_renders_google_sso(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Continue with Google Workspace", response.data)

    # 2. AUTHENTICATION & SESSION
    def test_successful_login_and_redirect(self):
        # Log in as Team Lead David Chen
        response = self.login_as('lead.eng@taskflow.local')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Team Lead & Sprint Management", response.data)

    def test_failed_login(self):
        response = self.login_as('lead.eng@taskflow.local', password="wrongpassword")
        self.assertIn(b"Invalid email or password", response.data)

    # 3. RBAC ROLE PERMISSIONS
    def test_employee_cannot_access_admin_dashboard(self):
        # Log in as Employee Alex Rivera
        self.login_as('alex.dev@taskflow.local')
        response = self.client.get('/dashboard/admin', follow_redirects=True)
        # Should be redirected away or forbidden
        self.assertIn(b"Access denied", response.data)

    def test_admin_can_access_admin_dashboard(self):
        # Log in as Admin Sarah Jenkins
        self.login_as('admin@taskflow.local')
        response = self.client.get('/dashboard/admin')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Administrator Overview", response.data)
        self.assertIn(b"Department Resource Allocation", response.data)

    # 4. TASK LIFECYCLE API & AUDIT TRAIL
    def test_full_task_lifecycle_workflow(self):
        """Simulate end-to-end organizational workflow:
           1. Lead delegates new task
           2. Employee starts work (IN_PROGRESS)
           3. Employee reports blocker (BLOCKED)
           4. Lead unblocks (IN_PROGRESS)
           5. Employee submits for review (UNDER_REVIEW)
           6. Lead approves and finalizes (DONE)
        """
        # Step 1: Lead creates task
        self.login_as('lead.eng@taskflow.local')
        create_res = self.client.post('/api/tasks', json={
            'title': 'Build Redis Cache Layer',
            'project_id': 2,
            'assignee_id': 4, # Alex Rivera
            'priority': 'HIGH',
            'description': 'Cache session tokens and user permissions',
            'estimated_hours': 10
        })
        self.assertEqual(create_res.status_code, 201)
        task_id = create_res.get_json()['task_id']

        # Step 2: Employee logs in & starts work
        self.login_as('alex.dev@taskflow.local')
        status_res = self.client.post(f'/api/tasks/{task_id}/status', json={'status': 'IN_PROGRESS'})
        self.assertEqual(status_res.status_code, 200)

        # Step 3: Employee flags blocker
        blocker_res = self.client.post(f'/api/tasks/{task_id}/blocker', json={
            'blocker_reason': 'Redis cluster firewall port 6379 closed'
        })
        self.assertEqual(blocker_res.status_code, 200)

        # Step 4: Lead unblocks
        self.login_as('lead.eng@taskflow.local')
        unblock_res = self.client.post(f'/api/tasks/{task_id}/status', json={'status': 'IN_PROGRESS'})
        self.assertEqual(unblock_res.status_code, 200)

        # Step 5: Employee submits for review
        self.login_as('alex.dev@taskflow.local')
        review_sub = self.client.post(f'/api/tasks/{task_id}/review', json={
            'action': 'SUBMIT',
            'notes': 'PR #108 opened with redis cluster tests'
        })
        self.assertEqual(review_sub.status_code, 200)

        # Step 6: Lead approves work
        self.login_as('lead.eng@taskflow.local')
        review_app = self.client.post(f'/api/tasks/{task_id}/review', json={
            'action': 'APPROVE',
            'notes': 'Performance tests verified 10x throughput'
        })
        self.assertEqual(review_app.status_code, 200)

        # Step 7: Verify final state in database
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        task = conn.execute("SELECT status, completed_at FROM tasks WHERE id = ?;", (task_id,)).fetchone()
        self.assertEqual(task['status'], 'DONE')
        self.assertIsNotNone(task['completed_at'])

        # Verify audit activity log entries were recorded
        logs = conn.execute("SELECT action FROM task_activity_log WHERE task_id = ? ORDER BY id ASC;", (task_id,)).fetchall()
        actions = [log['action'] for log in logs]
        self.assertIn('CREATED', actions)
        self.assertIn('STATUS_CHANGE', actions)
        self.assertIn('BLOCKED', actions)
        self.assertIn('SUBMIT_REVIEW', actions)
        self.assertIn('APPROVED', actions)
        conn.close()

if __name__ == '__main__':
    unittest.main()
