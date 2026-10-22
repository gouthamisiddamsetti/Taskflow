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
import io
import json
import tempfile
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
        self.original_upload_folder = app.config['UPLOAD_FOLDER']
        self.upload_directory = tempfile.TemporaryDirectory()
        app.config['UPLOAD_FOLDER'] = self.upload_directory.name

        conn = init_db(db_path=self.db_path, drop_existing=True, verbose=False)
        seed_data(conn, verbose=False)
        conn.close()

        self.client = app.test_client()

    def tearDown(self):
        app.config['UPLOAD_FOLDER'] = self.original_upload_folder
        self.upload_directory.cleanup()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except PermissionError:
                pass

    def login_as(self, email, password="password123"):
        self.client.get('/logout')
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)

    # 1. PUBLIC ROUTES
    def test_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Engineered for Organizations", response.data)
        self.assertIn(b"Taskflow", response.data)

    def test_login_page_shows_individual_role_accounts(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Demo accounts", response.data)
        self.assertNotIn(b"Switch Role", response.data)

    def test_authenticated_user_must_sign_out_before_another_login(self):
        self.login_as('alex.dev@taskflow.local')
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/dashboard', response.headers['Location'])

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

    def test_role_dashboards_require_matching_individual_account(self):
        self.login_as('lead.eng@taskflow.local')
        employee_dashboard = self.client.get('/dashboard/employee', follow_redirects=True)
        self.assertIn(b"Access denied", employee_dashboard.data)
        self.assertEqual(
            self.client.get('/auth/switch-demo-role/EMPLOYEE').status_code,
            404
        )

    def test_signup_cannot_self_assign_privileged_role(self):
        response = self.client.post('/signup', data={
            'full_name': 'New Account',
            'email': 'new.account@taskflow.local',
            'password': 'test-password',
            'role_id': '1',
            'department_id': '1'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        conn = sqlite3.connect(self.db_path)
        role_name = conn.execute("""
            SELECT r.name
            FROM users u JOIN roles r ON u.role_id = r.id
            WHERE u.email = ?;
        """, ('new.account@taskflow.local',)).fetchone()[0]
        conn.close()
        self.assertEqual(role_name, 'EMPLOYEE')

    def test_workspace_routes_render_for_logged_in_user(self):
        self.login_as('lead.eng@taskflow.local')
        
        # Test /projects
        res_proj = self.client.get('/projects')
        self.assertEqual(res_proj.status_code, 200)
        self.assertIn(b"Active Projects Workspace", res_proj.data)
        self.assertIn(b"ENG-CORE", res_proj.data)
        self.assertIn(b'id="createTaskModal"', res_proj.data)
        self.assertIn(b'name="git_url"', res_proj.data)

        # Test /teams
        res_teams = self.client.get('/teams')
        self.assertEqual(res_teams.status_code, 200)
        self.assertIn(b"Team Workload & Personnel", res_teams.data)
        self.assertIn(b"David Chen", res_teams.data)
        self.assertIn(b'id="createTaskModal"', res_teams.data)
        self.assertIn(b'name="git_url"', res_teams.data)

        # Test /activity
        res_act = self.client.get('/activity')
        self.assertEqual(res_act.status_code, 200)
        self.assertIn(b"Activity Logs & Audit Trail", res_act.data)
        self.assertIn(b'id="createTaskModal"', res_act.data)

    def test_admin_and_lead_can_assign_tasks_from_workspace_pages(self):
        employee_id = 4
        for email in ('lead.eng@taskflow.local', 'admin@taskflow.local'):
            self.login_as(email)
            for path in ('/projects', '/teams', '/activity'):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data.count(b'id="createTaskModal"'), 1)
                self.assertIn(b'id="createTaskForm"', response.data)

            created = self.client.post('/api/tasks', json={
                'title': f'Workspace assignment by {email}',
                'project_id': 1,
                'assignee_id': employee_id,
                'git_url': 'https://github.com/example/workspace-task'
            })
            self.assertEqual(created.status_code, 201)
            task_id = created.get_json()['task_id']
            conn = sqlite3.connect(self.db_path)
            task = conn.execute(
                "SELECT author_id, assignee_id, git_url FROM tasks WHERE id = ?;",
                (task_id,)
            ).fetchone()
            expected_author = conn.execute(
                "SELECT id FROM users WHERE email = ?;", (email,)
            ).fetchone()[0]
            conn.close()
            self.assertEqual(task[0], expected_author)
            self.assertEqual(task[1], employee_id)
            self.assertEqual(task[2], 'https://github.com/example/workspace-task')

    # 4. TASK LIFECYCLE API & AUDIT TRAIL
    def test_employee_submission_is_available_to_team_lead(self):
        self.login_as('lead.eng@taskflow.local')
        task_response = self.client.post('/api/tasks', json={
            'title': 'Submit work evidence',
            'project_id': 1,
            'assignee_id': 4,
            'git_url': 'https://github.com/example/taskflow',
            'description': 'Prepare implementation and test notes'
        })
        self.assertEqual(task_response.status_code, 201)
        task_id = task_response.get_json()['task_id']

        self.login_as('alex.dev@taskflow.local')
        employee_dashboard = self.client.get('/dashboard/employee')
        self.assertIn(b'https://github.com/example/taskflow', employee_dashboard.data)
        self.client.post(
            f'/api/tasks/{task_id}/status',
            json={'status': 'IN_PROGRESS'}
        )
        invalid_submission = self.client.post(
            f'/api/tasks/{task_id}/submission',
            data={'git_url': 'http://[invalid', 'description': 'Invalid link'}
        )
        self.assertEqual(invalid_submission.status_code, 400)

        submission_response = self.client.post(
            f'/api/tasks/{task_id}/submission',
            data={
                'git_url': 'https://github.com/example/taskflow/pull/42',
                'description': 'Implemented the feature and verified the upload flow.',
                'attachments': (io.BytesIO(b'test evidence'), 'evidence.txt')
            },
            content_type='multipart/form-data'
        )
        self.assertEqual(submission_response.status_code, 201)
        conn = sqlite3.connect(self.db_path)
        submitted_status = conn.execute(
            "SELECT status FROM tasks WHERE id = ?;", (task_id,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(submitted_status, 'UNDER_REVIEW')

        self.login_as('lead.eng@taskflow.local')
        lead_dashboard = self.client.get('/dashboard/lead')
        self.assertEqual(lead_dashboard.status_code, 200)
        self.assertIn(b'https://github.com/example/taskflow/pull/42', lead_dashboard.data)
        self.assertIn(b'Implemented the feature and verified the upload flow.', lead_dashboard.data)
        self.assertIn(b'evidence.txt', lead_dashboard.data)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        attachment = conn.execute(
            "SELECT attachments_json FROM task_submissions WHERE task_id = ?;",
            (task_id,)
        ).fetchone()
        stored_name = json.loads(attachment['attachments_json'])[0]['stored_name']
        conn.close()
        download_response = self.client.get(
            f'/api/tasks/{task_id}/submission/files/{stored_name}'
        )
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.data, b'test evidence')
        download_response.close()

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
