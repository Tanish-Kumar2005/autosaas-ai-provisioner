import io
import uuid
import shutil
import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import (
    save_parsed_csv, 
    init_db, 
    update_run_status, 
    log_audit_event
)
from agent import BrowserbaseProvisioningAgent

# Initialize FastAPI application
app = FastAPI(title="AutoSaaS AI - Backend Provisioner")

# Enable CORS so your HTML/JS frontend can communicate with this backend without blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Define path configurations for static frontend serving
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

# Mount frontend static files if directory exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        """Serves the main frontend UI dashboard at the root URL."""
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Frontend index.html not found"}
else:
    @app.get("/")
    def root_fallback():
        return {"message": "AutoSaaS AI Backend is running successfully. Frontend directory not detected."}

# Initialize database tables on startup
init_db()

@app.post("/api/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Handles CSV upload, validates columns, cleans data with case-insensitive TC2 deduplication, and saves to database."""
    try:
        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Read CSV using pandas with io.BytesIO
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {str(e)}")

        # Validate required columns
        required_cols = {"email", "role"}
        if not required_cols.issubset(df.columns):
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns. Expected at least: {list(required_cols)}"
            )

        # Normalize emails and roles to handle case/whitespace variants (TC2 safeguard)
        df['email'] = df['email'].astype(str).str.strip().str.lower()
        df['role'] = df['role'].astype(str).str.strip()

        initial_count = len(df)
        df = df.drop_duplicates(subset=["email"], keep="first")
        filtered_count = initial_count - len(df)

        # Generate a unique Run ID for this batch session
        run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
        records = []

        # Loop through the cleaned rows and format them
        for idx, row in enumerate(df.to_dict(orient="records")):
            records.append({
                "id": f"REC-{idx+1:03d}",
                "email": row.get("email"),
                "role": row.get("role", "Member"),
                "status": "pending",
                "error": ""
            })

        # Save the parsed run and records into SQLite
        save_parsed_csv(run_id, file.filename, records)
        log_audit_event(run_id, "INFO", f"CSV uploaded successfully: {file.filename} ({len(records)} records, {filtered_count} duplicates filtered)")

        return {
            "run_id": run_id,
            "filename": file.filename,
            "total_records": len(records),
            "filtered_duplicates": filtered_count,
            "records": records
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error during upload: {str(e)}")


@app.post("/api/approve-run")
def approve_run(payload: dict):
    """Marks a run session as approved via the HitL review gate."""
    run_id = payload.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required.")
    
    update_run_status(run_id, "approved")
    log_audit_event(run_id, "INFO", "Run session approved by operator via HitL gate.")
    return {"run_id": run_id, "status": "approved"}


@app.post("/api/run-agent")
def run_agent(payload: dict):
    """Triggers the Browserbase agent using the provided run_id and mock console URL after HitL approval check."""
    run_id = payload.get("run_id")
    console_url = payload.get("console_url")

    if not run_id or not console_url:
        raise HTTPException(status_code=400, detail="run_id and console_url are required.")

    # Enforce Server-Side HitL Approval check
    import sqlite3
    conn = sqlite3.connect("provisioner_state.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM runs WHERE run_id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Run ID not found.")
    
    current_status = row[0]
    if current_status not in ["approved", "pending"]:
        raise HTTPException(status_code=400, detail=f"Run cannot be executed because its status is '{current_status}'. Approval required.")

    # Instantiate and run our agent
    agent = BrowserbaseProvisioningAgent(run_id)
    results = agent.run(console_url)

    return {
        "run_id": run_id,
        "status": "completed",
        "results": results
    }