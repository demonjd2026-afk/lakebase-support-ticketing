# 🎫 Lakebase Support Ticketing System

> **Databricks Bootcamp — Day 1 Homework**  
> An internal support ticketing app powered by **Databricks Lakebase** (managed Postgres OLTP) and deployed via **Databricks Apps**.

---

## 📌 Overview

This project builds a full-stack internal support system where users can:

- 📋 View all support tickets
- 🔍 Select a ticket and read its message thread
- ✏️ Create a new ticket
- 💬 Add messages to an existing ticket
- 🔄 Update a ticket's status
- 🎯 Filter tickets by status *(bonus)*
- 📊 View ticket statistics *(bonus)*

All operational data is stored in and served from **Lakebase** — Databricks' managed PostgreSQL OLTP engine — not Delta Lake analytics tables.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Databricks Platform                      │
│                                                             │
│  ┌──────────────────┐        ┌──────────────────────────┐  │
│  │  Databricks App  │        │        Lakebase          │  │
│  │  (Streamlit /    │◄──────►│  (Managed PostgreSQL)    │  │
│  │   Gradio / Flask)│        │                          │  │
│  │                  │        │  ┌────────────────────┐  │  │
│  │  • Ticket List   │        │  │  tickets           │  │  │
│  │  • Message View  │        │  │  ticket_messages   │  │  │
│  │  • Create Form   │        │  │  (+ audit logs)    │  │  │
│  │  • Status Update │        │  └────────────────────┘  │  │
│  └──────────────────┘        └──────────────────────────┘  │
│           │                                                  │
│           │  Auth: Databricks PAT / Service Principal        │
│           │  Connection: psycopg2 / SQLAlchemy               │
└─────────────────────────────────────────────────────────────┘
                         │
                    (browser)
                    End User
```

### Why Lakebase instead of Delta Lake?

| Dimension | Delta Lake (Analytics) | Lakebase (OLTP) |
|---|---|---|
| Designed for | Batch reads, BI, ML | Transactional reads/writes |
| Latency | Seconds to minutes | Milliseconds |
| Consistency | Eventually consistent | ACID (row-level) |
| Write pattern | Append / bulk | Insert / Update / Delete |
| Use case | Dashboards, pipelines | Apps, APIs, operational data |

---

## 🗄️ Database Schema

```sql
-- Core ticket record
CREATE TABLE tickets (
    ticket_id    SERIAL PRIMARY KEY,
    title        TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'open',   -- open | in_progress | resolved
    priority     TEXT        NOT NULL DEFAULT 'medium', -- low | medium | high  (bonus)
    category     TEXT,                                  -- bonus
    created_by   TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Messages belonging to a ticket
CREATE TABLE ticket_messages (
    message_id   SERIAL PRIMARY KEY,
    ticket_id    INT         NOT NULL REFERENCES tickets(ticket_id),
    message_text TEXT        NOT NULL,
    author       TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX idx_messages_ticket ON ticket_messages(ticket_id);
CREATE INDEX idx_tickets_status  ON tickets(status);
```

---

## 📁 Repository Structure

```
lakebase-support-ticketing/
│
├── README.md                   ← you are here
│
├── sql/
│   ├── 01_create_schema.sql    ← DDL: create tables + indexes
│   └── 02_seed_data.sql        ← DML: 3+ tickets, 2+ messages each
│
├── app/
│   ├── app.py                  ← main Streamlit application
│   ├── db.py                   ← Lakebase connection + query helpers
│   └── requirements.txt        ← psycopg2-binary, streamlit, pandas
│
├── notebooks/
│   └── setup_lakebase.ipynb    ← Databricks notebook: provision DB,
│                                  run SQL scripts, verify data
│
└── .gitignore                  ← exclude secrets, __pycache__, .env
```

---

## 🚀 Implementation Phases

### Phase 1 — Lakebase Setup (Notebook)
**Goal:** Provision the database and seed it with sample data.

1. Open Databricks workspace (Free Edition)
2. Create a Lakebase instance from the **Data** sidebar → **+ Create** → **Lakebase**
3. Create a new notebook `notebooks/setup_lakebase.ipynb`
4. Connect to Lakebase using `psycopg2` with the connection string from the Lakebase UI
5. Run `sql/01_create_schema.sql` — creates `tickets` and `ticket_messages`
6. Run `sql/02_seed_data.sql` — inserts 3 tickets (mix of `open`, `in_progress`, `resolved`) with 2+ messages each
7. Verify: `SELECT count(*) FROM tickets;` returns ≥ 3

**Deliverable:** Lakebase tables visible in the Databricks UI with sample records.

---

### Phase 2 — Database Helper Layer (`app/db.py`)
**Goal:** Isolate all SQL behind clean Python functions.

Functions to implement:

```python
get_all_tickets()          → list[dict]
get_ticket_by_id(id)       → dict
get_messages(ticket_id)    → list[dict]
create_ticket(title, created_by, priority, category)  → int  (new ticket_id)
add_message(ticket_id, text, author)  → None
update_status(ticket_id, new_status)  → None
get_stats()                → dict  (counts by status)
```

Connection string is loaded from **Databricks secrets** (never hardcoded):

```python
import os
conn_str = os.environ["LAKEBASE_CONN"]   # set in Databricks App env config
```

**Deliverable:** `db.py` importable with all functions tested in the notebook.

---

### Phase 3 — Streamlit Application (`app/app.py`)
**Goal:** Build the UI with all required features.

**Sidebar:**
- Status filter dropdown (`All / Open / In Progress / Resolved`)
- Stats panel (ticket counts by status)
- "New Ticket" button → opens create form

**Main Panel — Ticket List view:**
- Table of tickets filtered by status selection
- Each row clickable → loads Ticket Detail view

**Main Panel — Ticket Detail view:**
- Ticket title, status badge, priority, created by / at
- Status update dropdown + "Update" button
- Full message thread (chronological)
- "Add Message" text area + "Send" button

**Main Panel — Create Ticket form:**
- Title (required), Priority (dropdown), Category (text), Created By (text)
- Submit → writes to Lakebase → refreshes ticket list

**Deliverable:** `app.py` runnable locally with `streamlit run app/app.py`.

---

### Phase 4 — Databricks App Deployment
**Goal:** Deploy to Databricks Apps and confirm live persistence.

1. In Databricks workspace: **Apps** → **Create App** → **Custom App**
2. Upload `app/` folder (or connect to GitHub repo)
3. Set environment variable `LAKEBASE_CONN` in App config (never in code)
4. Set entrypoint: `streamlit run app.py --server.port $PORT`
5. Deploy and open the App URL
6. Smoke test:
   - ✅ Existing tickets load
   - ✅ Create a new ticket → appears in list
   - ✅ Add a message → appears in thread
   - ✅ Change status → persists after browser refresh
   - ✅ Filter by status works

**Deliverable:** Live Databricks App URL with all operations verified.

---

### Phase 5 — Bonus Features *(optional)*
| Feature | Complexity |
|---|---|
| Priority / category columns | Already in schema — just surface in UI |
| Filter by status | Sidebar dropdown (Phase 3 includes this) |
| Input validation + error messages | `st.error()` guards on empty fields |
| Ticket statistics panel | `get_stats()` → `st.metric()` cards |
| Delete with confirmation | `st.button` → `st.warning` confirm step |
| Improved visual design | Custom CSS via `st.markdown` |

---

## 🔐 Security Notes

- **Never** commit `LAKEBASE_CONN` or any password to this repo
- Connection string is always injected via Databricks App environment variables
- `.gitignore` excludes `.env`, `*.pem`, and any secrets file
- Use Databricks **Secrets API** or App env config for credentials

---

## 🛠️ Local Development

```bash
# Clone the repo
git clone https://github.com/<your-username>/lakebase-support-ticketing.git
cd lakebase-support-ticketing

# Install dependencies
pip install -r app/requirements.txt

# Set connection string (local only — never commit this)
export LAKEBASE_CONN="postgresql://user:pass@host:5432/dbname"

# Run locally
streamlit run app/app.py
```

---

## 📋 Submission Checklist

- [ ] Databricks App URL
- [ ] Source code zipped
- [ ] Screenshot: deployed application
- [ ] Screenshot: Lakebase tables with sample records
- [ ] Reflection (3–5 sentences)

---

## 🙋 Reflection Prompts *(fill in after completing)*

**What was the most difficult part?**  
_(e.g., configuring the Lakebase connection string securely inside Databricks Apps)_

**How is Lakebase different from a traditional analytics table?**  
_(e.g., Lakebase gives you row-level ACID transactions and millisecond read/write latency — a Delta table would require file-level commits and isn't suited for per-row operational writes from a live app)_

**What feature would you add next?**  
_(e.g., AI-powered ticket summarization using Databricks Model Serving + DBRX)_

---

*Built by Jay (Jayanth Dolai) · Databricks Bootcamp Day 1 · 2026*
