# Lakebase Support Ticketing System

> **Databricks Bootcamp — Day 1 Homework**
> An internal support ticketing app powered by **Databricks Lakebase** (managed Postgres OLTP) and deployed via **Databricks Apps**.

**🔗 Live App:** https://support-ticketing-7474654640109575.aws.databricksapps.com
**📄 Full project write-up (PDF):** `Lakebase_Support_Ticketing_System.pdf` (in repo root)

---

## Overview

This project builds a full-stack internal support system where users can:

- View all support tickets
- Select a ticket and read its message thread
- Create a new ticket
- Add messages to an existing ticket
- Update a ticket's status
- Filter tickets by status *(bonus)*
- View live ticket statistics *(bonus)*
- Delete a ticket with a confirmation step *(bonus)*

All operational data is stored in and served from **Lakebase** — Databricks' managed PostgreSQL OLTP engine — not Delta Lake analytics tables.

---

## Architecture

```
+---------------------------------------------------------------+
|                     Databricks Platform                        |
|                                                                  |
|   +------------------+        +---------------------------+   |
|   |  Databricks App   |        |         Lakebase            |   |
|   |  (Gradio, Python) |<------>|   (Managed PostgreSQL)       |   |
|   |                    |        |                              |   |
|   |  - All Tickets     |        |   tickets                    |   |
|   |  - View & Update   |        |   ticket_messages             |   |
|   |  - New Ticket       |        +---------------------------+   |
|   +------------------+                                         |
|            |                                                    |
|            |  Auth: Service-principal OAuth (client_credentials)|
|            |  Secret: Databricks secret scope -> app.yml -> env |
+---------------------------------------------------------------+
                        |
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

## Database Schema

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

## Repository Structure

```
lakebase-support-ticketing/
│
├── README.md
├── Lakebase_Support_Ticketing_System.pdf   <- full write-up with screenshots
├── .gitignore
│
├── sql/
│   ├── 01_create_schema.sql
│   └── 02_seed_data.sql
│
├── notebooks/
│   └── setup_lakebase.ipynb
│
└── app/
    ├── app.py            <- Gradio UI
    ├── app.yml           <- Databricks Apps entrypoint + secret wiring
    ├── db.py             <- Lakebase connection + query helpers
    └── requirements.txt
```

---

## ✅ Status — Complete

| Phase | Description | Status |
|---|---|---|
| Phase 1 | Lakebase schema + seed data | ✅ Complete |
| Phase 2 | `db.py` — connection + query layer | ✅ Complete |
| Phase 3 | `app.py` — Gradio UI | ✅ Complete |
| Phase 4 | Databricks App deployment | ✅ Complete — **live** |
| Phase 5 | Bonus features | ✅ Complete |

---

## Phase 1 — Lakebase Setup

- Lakebase project `support-ticketing`, branch `production`, database `databricks_postgres`
- Schema created directly in the Lakebase SQL Editor
- Seeded 4 tickets across 3 statuses (`open`, `in_progress`, `resolved`) with 11 threaded messages

**Verification query:**
```sql
SELECT t.ticket_id, t.title, t.status, t.priority,
       COUNT(m.message_id) AS message_count
FROM tickets t
LEFT JOIN ticket_messages m ON t.ticket_id = m.ticket_id
GROUP BY t.ticket_id, t.title, t.status, t.priority
ORDER BY t.ticket_id;
```

---

## Phase 2 — Database Helper Layer (`app/db.py`)

All SQL is isolated in `db.py`. Inside Databricks Apps, the platform injects a service-principal
`DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET`, which `db.py` exchanges for a short-lived
OAuth JWT (`client_credentials` grant) and uses as the Lakebase connection password —
no personal access token is ever stored.

| Function | Purpose |
|---|---|
| `get_all_tickets(status_filter)` | All tickets, optional status filter |
| `get_ticket_by_id(id)` | Single ticket dict |
| `get_messages(ticket_id)` | All messages for a ticket, oldest first |
| `get_stats()` | Count by status + total |
| `create_ticket(title, created_by, priority, category)` | Insert + return new `ticket_id` |
| `add_message(ticket_id, text, author)` | Insert message |
| `update_status(ticket_id, new_status)` | Update ticket status |
| `delete_ticket(ticket_id)` | Delete with cascade |

---

## Phase 3 — Application UI (`app/app.py`)

Three-tab **Gradio** interface styled as a corporate helpdesk portal (light slate/indigo palette,
Inter typeface, sticky sidebar dashboard):

- **All Tickets** — filterable table, live message counts
- **View & Update** — formatted ticket detail card, message thread, status update, guarded delete
- **New Ticket** — validated creation form

---

## Phase 4 — Databricks App Deployment

- App: `support-ticketing`, source: this GitHub repo, path `app/`
- Entrypoint set via `app.yml`: `python app.py`
- `LAKEBASE_CONN` wired as a secret resource
- App's auto-generated service principal granted a Lakebase role on the `production` branch
- **Live URL:** https://support-ticketing-7474654640109575.aws.databricksapps.com

### Smoke test — all passing
- [x] Existing tickets load from Lakebase
- [x] New ticket can be created
- [x] Message can be added
- [x] Status can be updated (persists after refresh)
- [x] Filter by status works
- [x] Delete requires confirmation checkbox

---

## Bonus Features

| Feature | Status |
|---|---|
| Priority + category | ✅ In schema, forms, and table |
| Filter by status | ✅ Dropdown on All Tickets tab |
| Input validation + error messages | ✅ On create/update/message actions |
| Ticket statistics | ✅ Live sidebar dashboard |
| Delete with confirmation | ✅ Explicit checkbox required |
| Improved visual design | ✅ Corporate helpdesk-style UI |

---

## Security Notes

- `LAKEBASE_CONN` / Lakebase credentials never committed to this repo
- Auth uses the Databricks App's own service-principal OAuth identity, not a static PAT
- `.gitignore` excludes `.env`, `*.pem`, `__pycache__/`, `.DS_Store`

---

## Local Development

```bash
git clone https://github.com/demonjd2026-afk/lakebase-support-ticketing.git
cd lakebase-support-ticketing

pip install -r app/requirements.txt

export LAKEBASE_CONN="postgresql://token:<PAT>@<lakebase-host>:5432/databricks_postgres?sslmode=require"

python app/db.py     # quick connection test
python app/app.py    # run the app locally
```

---

## Reflection

**What was the most difficult part?**
Getting the Databricks App to authenticate against Lakebase. Lakebase requires a JWT OAuth token,
not a PAT — the working path was to have the app's own service principal exchange its injected
`DATABRICKS_CLIENT_ID`/`DATABRICKS_CLIENT_SECRET` for a JWT via the OIDC `client_credentials`
grant, and to grant that principal a Lakebase role on the branch.

**How is Lakebase different from a traditional analytics table?**
Lakebase gives row-level ACID transactions and millisecond read/write latency over the standard
Postgres protocol — built for an app's live create/update/delete operations. A Delta table is
built for large, append-oriented batch writes and file-level commits, not single-row OLTP traffic.

**What feature would you add next?**
An AI agent layer using Databricks Model Serving to auto-triage new tickets, draft reply
messages, and summarize long threads on load.

---

*Built by Jay (Jayanth Dolai) · Databricks Bootcamp Day 1 · August 2026*
