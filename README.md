# Taskflow: Organizational Work Management System

> **A Multi-Tiered Work Orchestration Platform Engineered for Enterprise Teams.**

Taskflow bridges the gap between simple personal to-do checklists and enterprise-scale operations. Designed around genuine company hierarchies (Managers, Team Leads, and Individual Contributors), it models work delegation, impediment escalation, quality sign-offs, and department-level data isolation.

---

## 1. Core Workflow & Architectural Blueprint

### 1.1 Organizational Work Model vs Personal To-Do
| Personal Task Checklists | Taskflow Organizational System |
| :--- | :--- |
| Single-user flat checklists | Multi-level hierarchy (Department $\to$ Team $\to$ Project $\to$ Task) |
| Work done only for oneself | Work delegated by Leads, executed by Employees, signed off by Managers |
| Hidden bottlenecks & blockers | Explicit **Blocked State** with mandatory reasoning & real-time Lead alerts |
| No historical accountability | **Immutable Audit Log** recording state transitions, actors, and approvals |
| One generic view | **3 Purpose-Built Dashboards** tailored to Admin, Lead, and Employee needs |

### 1.2 End-to-End Task Lifecycle

```
[1. Backlog / Todo]
        │
        ▼ (Employee starts work)
[2. In Progress] ─────────────► [Blocked State (Impediment Flagged)]
        │                                     │
        │                                     ▼ (Lead intervenes & unblocks)
        ▼ (Employee submits work)       [2. In Progress]
[3. Under Review]
        │
   ┌────┴────────────────────────┐
   ▼ (Lead requests changes)      ▼ (Lead approves deliverable)
[2. In Progress]              [4. Done & Logged]
```

---

## 2. Role-Based Dashboards

### 🏛️ 1. Administrator Dashboard (`/dashboard/admin`)
- **Executive Oversight:** Total headcount, department health, project distribution, and overall completion velocity.
- **Department Breakdown:** Headcount and workload metrics across Engineering, Product Design, and Marketing.
- **System Audit Trail:** Real-time stream of all status changes, assignments, and approvals.
- **Personnel Directory:** Role assignments and active status management.

### 🎯 2. Team Lead / Manager Dashboard (`/dashboard/lead`)
- **Workload Balancing Heatmap:** Live task count per engineer to prevent overloading and burnout.
- **Blocker Resolution Center:** High-priority cards highlighting impediments with one-click resolution.
- **Sign-Off Queue:** Quality review pipeline where leads inspect employee submissions and approve or request revisions.
- **Task Delegation Engine:** Modal to dispatch work with priority, categories, estimates, and due dates.

### ⚡ 3. Employee / Individual Contributor Dashboard (`/dashboard/employee`)
- **Focused "My Work" Board:** Clear view of tasks assigned directly to the user.
- **One-Click Progression:** Transition from `TODO` $\to$ `IN_PROGRESS`.
- **Blocker Escalation:** Submit impediment reason with immediate notification to the lead.
- **Deliverable Submission:** Submit pull request links or notes for review sign-off.

---

## 3. Team Deliverables Matrix

| Team | Branch | Scope & Responsibilities | Deliverables | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Team 3 (Our Team)** | `feature/database` | SQLite relational schema, keys, check constraints, indexes, triggers, seed data, and unit tests | `schema.sql`<br>`init_db.py`<br>`test_database.py` | ✅ **Complete & Verified** |
| **Team 2** | `feature/backend-api` | Flask app setup, session auth, password hashing, task CRUD, role middleware, REST endpoints | `app.py`<br>`auth.py` | ✅ **Complete & Verified** |
| **Team 1** | `feature/frontend-ui` | Cream and Sage Green design system, landing page, responsive role dashboards, modals, forms | `templates/`<br>`static/css/style.css`<br>`static/js/app.js` | ✅ **Complete & Verified** |
| **Team 4** | `feature/integration-testing` | End-to-end integration test suite, documentation, and demo verification | `test_integration.py`<br>`README.md` | ✅ **Complete & Verified** |

---

## 4. Database Architecture (Team 3)

### Relational Schema (`schema.sql`)
- **`roles`**: `ADMIN`, `TEAM_LEAD`, `EMPLOYEE` with check constraints.
- **`departments`**: Code, name, and descriptions.
- **`users`**: Foreign keys to `roles` and `departments`, password hashes, and initials.
- **`projects`**: Department ownership and project lead references.
- **`tasks`**: Foreign keys to project, author, assignee, and reviewer with check constraints on `priority` and `status`.
- **`task_activity_log`**: Automated audit trail linked with foreign keys and cascade rules.
- **`comments`**: Threaded discussion on work units.

### Integrity & Performance Features
- `PRAGMA foreign_keys = ON;` strictly enforced on all connections.
- Six performance indexes (`idx_tasks_assignee_status`, `idx_tasks_status_priority`, etc.).
- SQLite Trigger `trg_tasks_updated_at` automatically maintaining timestamps.

---

## 5. Quick Start & Setup Guide

### Prerequisites
- Python 3.10+
- Flask (`pip install flask`)

### 1. Initialize Database & Seed Organizational Data
```bash
python init_db.py
```

### 2. Run Database Test Suite
```bash
python test_database.py -v
```
*(Runs 13 tests covering foreign keys, check constraints, cascades, indexes, and department/employee data isolation).*

### 3. Run Integration Test Suite
```bash
python test_integration.py -v
```
*(Runs 7 tests covering public views, authentication, RBAC boundaries, and full task lifecycle workflows).*

### 4. Start the Application
```bash
python app.py
```
Open your browser at `http://127.0.0.1:5000`.

---

## 6. Live Demo Walkthrough Guide

### Demo Credentials (Default Password: `password123`)
- **Administrator:** `admin@taskflow.local` (Sarah Jenkins - VP Operations)
- **Team Lead:** `lead.eng@taskflow.local` (David Chen - Staff Lead)
- **Employee (IC):** `alex.dev@taskflow.local` (Alex Rivera - Full Stack Engineer)

### Walkthrough Steps:
1. **Landing Page:** Navigate to `/` to view the organizational workflow showcase.
2. **Login Screen:** Sign in with the email and password for the employee, Team Lead, or Admin account. Each account opens only its assigned role dashboard.
3. **Team Lead View:**
   - Log in as `lead.eng@taskflow.local`.
   - Inspect the **Workload Balancing Heatmap**.
   - Notice the **Blocked Task Alert** (`TSK-105`) and the **Sign-Off Queue**.
   - Click `+ Assign Work` to delegate a new task to Alex Rivera.
4. **Employee View:**
   - Sign out, then sign in with `alex.dev@taskflow.local` and the demo password to use the employee account.
   - See the personal focus queue with active hours and blocker warning.
   - Click `Start Work` on a `TODO` item to advance it to `IN_PROGRESS`.
   - Click `Flag Blocker` to report an impediment, or `Submit for Review`.
5. **Admin View:**
   - Sign out, then sign in with `admin@taskflow.local` and the demo password to use the administrator account.
   - Observe company-wide stats, department health, and the updated **System Audit Log** reflecting the actions just completed!
