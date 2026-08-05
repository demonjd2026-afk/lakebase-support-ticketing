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
│  │  (Streamlit)     │◄──────►│  (Managed PostgreSQL)    │  │
│  │                  │        │                          │  │
│  │  • Ticket List   │        │  ┌────────────────────┐  │  │
│  │  • Message View  │        │  │  tickets           │  │  │
│  │  • Create Form   │        │  │  ticket_messages   │  │  │
│  │  • Status Update │        │  └────────────────────┘  │  │
│  └──────────────────┘        └──────────────────────────┘  │
│           │                                                  │
│           │  Auth: Databricks PAT (OAuth token)             │
│           │  Connection: psycopg2 via LAKEBASE_CONN env var │
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
CREATE TABLE tickets (
    ticket_id   SERIAL       PRIMARY KEY,
    title       TEXT         NOT NULL,
    status      TEXT         NOT NULL DEFAULT 'open',    -- open | in_progress | resolved
    priority    TEXT         NOT NULL DEFAULT 'medium',  -- low | medium | high
    category    TEXT,
    created_by  TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE ticket_messages (
    message_id   SERIAL       PRIMARY KEY,
    ticket_id    INT          NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    message_text TEXT         NOT NULL,
    author       TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_ticket_id ON ticket_messages(ticket_id);
CREATE INDEX idx_tickets_status     ON tickets(status);
CREATE INDEX idx_tickets_priority   ON tickets(priority);
```

---

## 📁 Repository Structure

```
lakebase-support-ticketing/
│
├── README.md                   ← you are here
├── .gitignore                  ← excludes secrets, __pycache__, .env
│
├── sql/
│   ├── 01_create_schema.sql    ← DDL: create tables + indexes (reference)
│   └── 02_seed_data.sql        ← DML: sample tickets + messages (reference)
│
└── app/
    ├── app.py                  ← main Streamlit application  [Phase 3]
    ├── db.py                   ← Lakebase connection + query helpers  ✅ done
    └── requirements.txt        ← psycopg2-binary, streamlit, pandas  ✅ done
```

---

## ✅ Progress Tracker

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Lakebase project + schema + seed data | ✅ Complete |
| **Phase 2** | `db.py` — connection layer + all query helpers | ✅ Complete |
| **Phase 3** | `app.py` — Streamlit UI | 🔄 In progress |
| **Phase 4** | Databricks App deployment + smoke test | ⏳ Pending |
| **Phase 5** | Bonus features | ⏳ Pending |

---

## 🚀 Phase 1 — Lakebase Setup ✅

**What was done:**

1. Created Lakebase project `support-ticketing` in Databricks workspace
   - URL: `dbc-291b687e-da89.cloud.databricks.com/lakebase/projects`
   - Branch: `production`
   - Database: `databricks_postgres`
   - Auth: OAuth (Databricks identity)

2. Ran `sql/01_create_schema.sql` directly in Lakebase SQL Editor
   - Created `tickets` table (7 columns including `priority` and `category`)
   - Created `ticket_messages` table with FK → `tickets(ticket_id) ON DELETE CASCADE`
   - Created 3 indexes: `idx_messages_ticket_id`, `idx_tickets_status`, `idx_tickets_priority`
   - Result: **7 queries executed — Statement executed successfully (297ms)**

3. Ran `sql/02_seed_data.sql` directly in Lakebase SQL Editor
   - Inserted 4 tickets across 3 statuses: `open`, `in_progress`, `resolved`
   - Inserted 11 messages (3 per ticket for tickets 1–3, 2 for ticket 4)
   - Result: **4 rows verified (316ms)**

**Verified data:**

| ticket_id | title | status | priority | messages |
|---|---|---|---|---|
| 1 | Databricks cluster auto-terminates during pipeline run | open | high | 3 |
| 2 | Unable to access Unity Catalog schema after permission update | in_progress | high | 3 |
| 3 | Delta table OPTIMIZE job taking longer than expected | resolved | medium | 3 |
| 4 | Lakebase connection string not recognized in Databricks App | open | medium | 2 |

---

## 🚀 Phase 2 — Database Helper Layer ✅

**What was done:**

Built `app/db.py` — all SQL isolated here, `app.py` never writes raw SQL.

**Connection:** reads `LAKEBASE_CONN` env var at runtime:
```
postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres
```

**Functions implemented:**

| Function | Purpose |
|---|---|
| `get_conn()` | Returns psycopg2 connection with `RealDictCursor` |
| `get_all_tickets(status_filter)` | All tickets, optional status filter |
| `get_ticket_by_id(ticket_id)` | Single ticket dict |
| `get_messages(ticket_id)` | All messages for a ticket (oldest first) |
| `get_stats()` | Count by status + total |
| `create_ticket(title, created_by, priority, category)` | Insert + return new `ticket_id` |
| `add_message(ticket_id, message_text, author)` | Insert message |
| `update_status(ticket_id, new_status)` | Update ticket status |
| `delete_ticket(ticket_id)` | Delete with cascade |

Built `app/requirements.txt`:
```
streamlit>=1.35.0
psycopg2-binary>=2.9.9
pandas>=2.0.0
```

---

## 🚀 Phase 3 — Streamlit Application *(in progress)*

**Planned UI:**

**Sidebar:**
- Status filter: `All / open / in_progress / resolved`
- Stats panel: metric cards (open, in progress, resolved, total)
- New Ticket button

**Main panel — Ticket List:**
- Filterable table of all tickets
- Click any ticket → Ticket Detail view

**Main panel — Ticket Detail:**
- Title, status badge, priority, category, created by / at
- Status update dropdown + Update button
- Delete ticket with confirmation
- Full message thread (chronological)
- Add message text area + Send button

**Main panel — Create Ticket form:**
- Title (required), Priority (dropdown), Category (text), Created By (required)
- Validates inputs before writing to Lakebase

---

## 🚀 Phase 4 — Databricks App Deployment *(pending)*

1. Databricks workspace → **Apps** → **Create App** → **Custom App**
2. Connect to GitHub repo or upload `app/` folder
3. Set env var `LAKEBASE_CONN` in App config (never hardcoded)
4. Entrypoint: `streamlit run app.py --server.port $PORT`
5. Smoke test all operations

---

## 🚀 Phase 5 — Bonus Features *(pending)*

| Feature | Status |
|---|---|
| Priority + category columns | ✅ Already in schema and `db.py` |
| Filter by status | ⏳ Phase 3 |
| Input validation + error messages | ⏳ Phase 3 |
| Ticket statistics panel | ⏳ Phase 3 |
| Delete with confirmation | ⏳ Phase 3 |
| Improved visual design | ⏳ Phase 3 |

---

## 🔐 Security Notes

- `LAKEBASE_CONN` is **never** committed to this repo
- PAT is injected only via Databricks App environment variable config
- `.gitignore` excludes `.env`, `*.pem`, `__pycache__/`, `secrets.toml`
- Auth method: OAuth (Databricks identity token)

---

## 🛠️ Local Development

```bash
# Clone the repo
git clone https://github.com/<your-username>/lakebase-support-ticketing.git
cd lakebase-support-ticketing

# Install dependencies
pip install -r app/requirements.txt

# Set connection string (local only — never commit this)
export LAKEBASE_CONN="postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres"

# Test the DB layer
python app/db.py

# Run the app
streamlit run app/app.py
```

---

## 📋 Submission Checklist

- [ ] Databricks App URL
- [ ] Source code zipped
- [ ] Screenshot: deployed application
- [ ] Screenshot: Lakebase tables with sample records ✅ captured
- [ ] Reflection (3–5 sentences)

---

## 🙋 Reflection *(fill in after Phase 4)*

**What was the most difficult part?**
_(e.g., finding the Lakebase connection string — it is exposed via OAuth token not a traditional password, requiring a Databricks PAT as the password in the psycopg2 connection string)_

**How is Lakebase different from a traditional analytics table?**
_(Lakebase gives you row-level ACID transactions and millisecond read/write latency via standard Postgres protocol. A Delta table requires file-level commits and is built for bulk analytical workloads — not suitable for per-row operational writes from a live app.)_

**What feature would you add next?**
_(AI-powered ticket summarization and auto-routing using Databricks Model Serving + DBRX or Claude)_

---

*Built by Jay (Jayanth Dolai) · Databricks Bootcamp Day 1 · August 2026*
