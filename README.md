# AutoSaaS AI Provisioner 🚀
*Ziro Digital Agentic AI Hackathon 2026*

AutoSaaS AI Provisioner is a production-grade agentic automation system built with FastAPI, Playwright, SQLite, and Tailwind CSS. It ingests user CSVs, performs case-insensitive deduplication, enforces a Server-Side Human-in-the-Loop (HitL) approval gate, and delegates browser actions to an intelligent agent with robust per-record failure isolation and TC4 retry capabilities.

---

## 🛠️ Architecture & Tech Stack
* **Backend:** FastAPI, Python 3.10, Pandas, SQLite, Uvicorn
* **Automation:** Playwright (Chromium), Browserbase Cloud Integration
* **Frontend:** Tailwind CSS (Responsive Single-Page Application)
* **Deployment:** Containerized via Docker, deployed live on Render Cloud

---

## 📋 Core Compliance Features
* **TC2 (Deduplication):** Case-insensitive and whitespace-trimmed email duplicate filtering prior to database persistence, tracking filtered metrics.
* **TC3 (Role Normalization):** Intelligent agent mapping of input variants to strict role schemas, successfully overriding UI defaults.
* **TC4 (Retry Semantics):** Resilient execution logic allowing re-running batch runs to fetch and process only pending/failed records without duplicating successful creations.
* **Human-in-the-Loop (HitL) Gate:** Server-enforced approval flow requiring explicit operator authorization before agent execution.
* **Auditability:** Complete SQLite run states, per-record tracking, and structured audit logs.