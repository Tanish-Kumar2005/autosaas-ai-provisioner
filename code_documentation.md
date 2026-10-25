# AutoSaaS AI - Complete Code Documentation

## Project Overview

AutoSaaS AI is an autonomous user provisioning tool. It takes a CSV file of users (email + role), validates and deduplicates them, then uses a browser automation agent (Playwright + Browserbase) to create each user in a SaaS admin console. It tracks progress in SQLite and shows a live dashboard.

---

## 1. backend/database.py - SQLite State Management

### What the file does
Manages all database operations using SQLite. Stores runs, individual records, and audit logs.

### Functions

#### init_db()
- Creates 3 tables if they don't exist: runs, records, audit_logs
- runs: tracks each CSV upload (run_id, filename, total_records, status)
- records: tracks each user (id, run_id, email, role, status, error)
- audit_logs: tracks every event (log_id, run_id, timestamp, event_type, details)
- Uses CREATE TABLE IF NOT EXISTS so it's safe to call repeatedly

#### save_parsed_csv(run_id, filename, records)
- Inserts a new run row and all record rows
- Uses INSERT OR REPLACE to handle re-runs
- Status starts as 'pending'

#### get_pending_records(run_id)
- Returns records where status != 'success' (for retry support)
- Uses pandas read_sql_query
- Enables idempotent retries - already-successful records are skipped

#### update_record_status(run_id, record_id, status, error)
- Updates individual record status to 'success' or 'failed'
- Used by agent during processing and by progress polling

#### update_run_status(run_id, status)
- Updates overall run status: pending -> approved -> running -> completed/failed

#### log_audit_event(run_id, event_type, details)
- Inserts audit log entry with auto-incrementing log_id and current timestamp

---

## 2. backend/main.py - FastAPI Backend Server

### What the file does
Exposes REST API endpoints. Serves the frontend. Handles CSV upload, validation, approval, agent execution, and progress polling.

### Key Components

#### FastAPI app + CORS
- app = FastAPI() creates the web server
- CORSMiddleware allows frontend (different port) to call backend

#### /api/upload-csv (POST)
- Reads uploaded file with pandas
- Validates required columns: email, role
- TC1: Validates email format with regex
- Normalizes emails (strip + lowercase) and roles (strip)
- Deduplicates by email (keep first) - TC2
- Assigns record IDs (REC-001, REC-002, ...)
- Saves to database, returns run_id and records

#### /api/approve-run (POST)
- Human-in-the-Loop gate: marks run as 'approved'
- Agent won't run until approved

#### /api/run-progress (GET)
- Returns {completed, total} for live progress bar
- Counts records with status='success'

#### /api/run-agent (POST)
- Triggers BrowserbaseProvisioningAgent
- Checks if run exists, if records need processing
- Enforces approval gate

---

## 3. backend/agent.py - Browser Automation Agent

### What the file does
Uses Playwright to automate the SaaS admin console. Opens modal, fills form, submits, verifies. Updates database after each record.

### Class: BrowserbaseProvisioningAgent

#### __init__(run_id)
- Stores run_id for database operations

#### run(console_url)
- Main execution method
- Logs start, sets run status to 'running'
- Gets pending records from DB
- Launches browser (local Chromium or Browserbase cloud)
- Navigates to console_url
- For each record:
  - Normalizes role (admin->Admin, manager->Manager, member->Member)
  - Single JS round-trip: opens modal, fills email, sets role, clicks submit
  - Reads back last table row to verify
  - Updates DB status (success/failed)
  - Logs audit event
- Sets run status to 'completed'
- Closes browser

### Speed Optimizations
- Combined 4 Playwright calls into 1 page.evaluate() JS call
- Removed 0.5s sleep and wait_for_selector
- Targeted verification: only reads last row

---

## 4. frontend/index.html - Dashboard UI

### What the file does
Single-page web dashboard. Upload CSV, review records, approve, run agent, view results with live progress.

### Key JavaScript Functions

#### handleFileUpload()
- Reads CSV file, sends to /api/upload-csv
- Shows validation loading panel
- Displays parsed records in review table

#### approveAndRun()
- Calls /api/approve-run
- Calls /api/run-agent
- Polls /api/run-progress every 500ms for live progress
- Shows results table on completion

#### renderResultsTable(results, elapsed)
- Builds HTML table with status badges
- Shows CSV role vs applied role comparison
- Highlights role normalization (TC3)

---

## 5. frontend/mock_console.html - Mock SaaS Console

### What the file does
Simulates a SaaS admin console with Add User modal and user table. Used as automation target.

### Key Elements
- #open-modal-btn: opens modal
- #email-input: email field
- #role-dropdown: role selector (defaults to Admin - tests TC3)
- #submit-user-btn: submits form
- #userTableBody: table where users appear

### JavaScript
- toggleModal(show): shows/hides modal
- submitUser(): reads form, appends row to table

---

## 6. requirements.txt - Dependencies

fastapi: Web framework
uvicorn: ASGI server
playwright: Browser automation
browserbase: Cloud browser service
pandas: CSV processing
pydantic: Data validation
python-multipart: File upload support
httpx: HTTP client
numpy: Numerical (pandas dependency)
python-dotenv: Environment variables