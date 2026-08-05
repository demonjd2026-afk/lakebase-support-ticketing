# =============================================================
# db.py — Lakebase connection
# Uses DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET
# injected automatically by Databricks Apps runtime
# =============================================================

import os
import psycopg2
import psycopg2.extras
import urllib.parse
import requests as http_requests

LAKEBASE_HOST = "ep-damp-rain-d8xddh4u.database.us-east-2.cloud.databricks.com"
LAKEBASE_DB   = "databricks_postgres"


def get_oauth_token():
    """
    Exchange DATABRICKS_CLIENT_ID + DATABRICKS_CLIENT_SECRET
    for a short-lived OAuth JWT token accepted by Lakebase.
    """
    client_id     = os.environ["DATABRICKS_CLIENT_ID"]
    client_secret = os.environ["DATABRICKS_CLIENT_SECRET"]
    host          = os.environ.get("DATABRICKS_HOST",
                    "dbc-291b687e-da89.cloud.databricks.com")

    # Ensure host has no trailing slash and has https://
    if not host.startswith("https://"):
        host = f"https://{host}"

    r = http_requests.post(
        f"{host}/oidc/v1/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
            "scope":         "all-apis",
        },
        timeout=30,
    )

    if r.status_code != 200:
        raise RuntimeError(f"Token fetch failed: {r.status_code} {r.text}")

    return r.json()["access_token"]


def get_conn():
    token = get_oauth_token()
    user  = urllib.parse.quote("jayanthdolai07@gmail.com", safe="")
    pw    = urllib.parse.quote(token, safe="")
    conn_str = (
        f"postgresql://{user}:{pw}"
        f"@{LAKEBASE_HOST}/{LAKEBASE_DB}?sslmode=require"
    )
    return psycopg2.connect(conn_str, cursor_factory=psycopg2.extras.RealDictCursor)


def get_all_tickets(status_filter=None):
    conn = get_conn()
    try:
        cur = conn.cursor()
        if status_filter and status_filter != "All":
            cur.execute("""
                SELECT t.ticket_id, t.title, t.status, t.priority, t.category,
                       t.created_by, t.created_at,
                       (SELECT COUNT(*) FROM ticket_messages m
                        WHERE m.ticket_id = t.ticket_id) AS message_count
                FROM tickets t WHERE t.status = %s ORDER BY t.created_at DESC
            """, (status_filter,))
        else:
            cur.execute("""
                SELECT t.ticket_id, t.title, t.status, t.priority, t.category,
                       t.created_by, t.created_at,
                       (SELECT COUNT(*) FROM ticket_messages m
                        WHERE m.ticket_id = t.ticket_id) AS message_count
                FROM tickets t ORDER BY t.created_at DESC
            """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_ticket_by_id(ticket_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ticket_id, title, status, priority, category, created_by, created_at
            FROM tickets WHERE ticket_id = %s
        """, (ticket_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_messages(ticket_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT message_id, ticket_id, message_text, author, created_at
            FROM ticket_messages WHERE ticket_id = %s ORDER BY created_at ASC
        """, (ticket_id,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_stats():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status, COUNT(*) AS cnt FROM tickets GROUP BY status")
        rows = cur.fetchall()
        stats = {'open': 0, 'in_progress': 0, 'resolved': 0}
        for row in rows:
            stats[row['status']] = row['cnt']
        stats['total'] = sum(stats.values())
        return stats
    finally:
        conn.close()


def create_ticket(title, created_by, priority='medium', category=None):
    if not title or not title.strip():
        raise ValueError("Title cannot be empty.")
    if not created_by or not created_by.strip():
        raise ValueError("Created by cannot be empty.")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tickets (title, status, priority, category, created_by)
            VALUES (%s, 'open', %s, %s, %s) RETURNING ticket_id
        """, (title.strip(), priority, category, created_by.strip()))
        ticket_id = cur.fetchone()['ticket_id']
        conn.commit()
        return ticket_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def add_message(ticket_id, message_text, author):
    if not message_text or not message_text.strip():
        raise ValueError("Message cannot be empty.")
    if not author or not author.strip():
        raise ValueError("Author cannot be empty.")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ticket_messages (ticket_id, message_text, author)
            VALUES (%s, %s, %s)
        """, (ticket_id, message_text.strip(), author.strip()))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_status(ticket_id, new_status):
    valid = {'open', 'in_progress', 'resolved'}
    if new_status not in valid:
        raise ValueError(f"Invalid status '{new_status}'.")
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE tickets SET status = %s WHERE ticket_id = %s",
                    (new_status, ticket_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_ticket(ticket_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
