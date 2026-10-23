import os 
import time
from dotenv import load_dotenv
from browserbase import Browserbase
from playwright.sync_api import sync_playwright
from database import (
    update_record_status, 
    get_pending_records, 
    update_run_status, 
    log_audit_event
)

load_dotenv()

class BrowserbaseProvisioningAgent:

    def __init__(self, run_id: str):
        self.run_id = run_id

    def run(self, console_url: str):
        print(f"Starting agent execution for run_id: {self.run_id}")
        log_audit_event(self.run_id, "INFO", f"Agent execution started for URL: {console_url}")
        update_run_status(self.run_id, "running")

        records = get_pending_records(self.run_id)
        
        if not records:
            print("No pending records found to process.")
            log_audit_event(self.run_id, "WARNING", "No pending records found.")
            update_run_status(self.run_id, "completed")
            return []

        # Check if we are testing locally vs cloud Browserbase
        is_local = "localhost" in console_url or "127.0.0.1" in console_url or "file://" in console_url

        results = []
        with sync_playwright() as p:
            if is_local:
                print("Launching local Chromium browser for local testing...")
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
            else:
                print("Connecting to Browserbase cloud browser...")
                bb = Browserbase(api_key=os.environ.get("BROWSERBASE_API_KEY"))
                session = bb.sessions.create()
                print(f"Browserbase Session Live: {session.connect_url}")
                browser = p.chromium.connect_over_cdp(session.connect_url)
                context = browser.contexts[0]
                page = context.pages[0]

            try:
                print(f"Navigating to: {console_url}")
                page.goto(console_url)
                
                for record in records:
                    email = record["email"]
                    raw_role = record["role"]
                    record_id = record["id"]

                    # Normalize role to match dropdown options (Admin, Manager, Member) to satisfy TC3
                    role_map = {
                        "admin": "Admin",
                        "manager": "Manager",
                        "member": "Member"
                    }
                    role = role_map.get(str(raw_role).strip().lower(), "Member")

                    print(f"Provisioning user: {email} with role: {role}")

                    try:
                        # 1. Open the modal
                        page.click("#open-modal-btn")
                        page.wait_for_selector("#userModal:not(.hidden)", timeout=5000)

                        # 2. Fill out email and normalized role inside the modal
                        page.fill("#email-input", email)
                        page.select_option("#role-dropdown", role)
                        
                        # 3. Submit the user
                        page.click("#submit-user-btn")
                        
                        time.sleep(0.5) # Brief pause for UI state update
                        
                        # 4. Read-back verification (TC requirement: re-read console state)
                        table_content = page.locator("#userTableBody").inner_text()
                        if email in table_content:
                            update_record_status(self.run_id, record_id, "success", "Successfully provisioned and verified in console")
                            log_audit_event(self.run_id, "SUCCESS", f"Provisioned and verified user: {email}")
                            results.append({"email": email, "status": "success"})
                        else:
                            raise Exception("User submitted but not found in console table read-back verification.")

                    except Exception as record_err:
                        err_msg = str(record_err)
                        print(f"Failed to provision {email}: {err_msg}")
                        update_record_status(self.run_id, record_id, "failed", err_msg)
                        log_audit_event(self.run_id, "ERROR", f"Failed to provision {email}: {err_msg}")
                        results.append({"email": email, "status": "failed", "error": err_msg})

                print("All pending records processed!")
                update_run_status(self.run_id, "completed")
                log_audit_event(self.run_id, "INFO", "Run session completed successfully.")

            except Exception as e:
                err_msg = str(e)
                print(f"Automation execution error: {err_msg}")
                update_run_status(self.run_id, "failed")
                log_audit_event(self.run_id, "CRITICAL", f"Run failed with exception: {err_msg}")
                raise e

            finally:
                browser.close()

        return results