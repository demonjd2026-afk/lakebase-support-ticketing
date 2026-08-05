# =============================================================
# db.py — Lakebase connection + all query helpers
# All SQL lives here. app.py never writes raw SQL.
#
# Connection string format (OAuth / PAT):
#   postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres
#
# Set this as env var LAKEBASE_CONN before running:
#   export LAKEBASE_CONN="postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres"
# =============================================================

import os
import psycopg2
import psycopg2.extras  # returns rows as dicts


# ─────────────────────────────────────────
# CONNECTION
# ─────────────────────────────────────────

def get_conn():
    """
    Returns a new psycopg2 connection using the LAKEBASE_CONN env var.
    cursor_factory=RealDictCursor means every row comes back as a dict.
    """
    conn_str = os.environ.get("LAKEBASE_CONN")
    if not conn_str:
        raise EnvironmentError(
            "LAKEBASE_CONN environment variable is not set. "
            "Set it to: postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres"
        )
    return psycopg2.connect(conn_str, cursor_factory=psycopg2.extras.RealDictCursor)


# ─────────────────────────────────────────
# READ HELPERS
# ─────────────────────────────────────────

def get_all_tickets(status_filter=None):
    """
    Returns all tickets, optionally filtered by status.
    status_filter: None | 'open' | 'in_progress' | 'resolved'
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        if status_filter and status_filter != "All":
            cur.execute("""
                SELECT ticket_id, title, status, priority, category, created_by,
                       created_at,
                       (SELECT COUNT(*) FROM ticket_messages m
                        WHERE m.ticket_id = t.ticket_id) AS message_count
                FROM tickets t
                WHERE status = %s
                ORDER BY created_at DESC
            """, (status_filter,))
        else:
            cur.execute("""
                SELECT ticket_id, title, status, priority, category, created_by,
                       created_at,
                       (SELECT COUNT(*) FROM ticket_messages m
                        WHERE m.ticket_id = t.ticket_id) AS message_count
                FROM tickets t
                ORDER BY created_at DESC
            """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_ticket_by_id(ticket_id):
    """Returns a single ticket dict, or None if not found."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT ticket_id, title, status, priority, category, created_by, created_at
            FROM tickets
            WHERE ticket_id = %s
        """, (ticket_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_messages(ticket_id):
    """Returns all messages for a ticket, oldest first."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT message_id, ticket_id, message_text, author, created_at
            FROM ticket_messages
            WHERE ticket_id = %s
            ORDER BY created_at ASC
        """, (ticket_id,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_stats():
    """
    Returns ticket counts by status for the stats panel.
    Example: {'open': 2, 'in_progress': 1, 'resolved': 1, 'total': 4}
    """
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) AS cnt
            FROM tickets
            GROUP BY status
        """)
        rows = cur.fetchall()
        stats = {'open': 0, 'in_progress': 0, 'resolved': 0}
        for row in rows:
            stats[row['status']] = row['cnt']
        stats['total'] = sum(stats.values())
        return stats
    finally:
        conn.close()


# ─────────────────────────────────────────
# WRITE HELPERS
# ─────────────────────────────────────────

def create_ticket(title, created_by, priority='medium', category=None):
    """
    Inserts a new ticket. Returns the new ticket_id.
    """
    if not title or not title.strip():
        raise ValueError("Ticket title cannot be empty.")
    if not created_by or not created_by.strip():
        raise ValueError("Created by cannot be empty.")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tickets (title, status, priority, category, created_by)
            VALUES (%s, 'open', %s, %s, %s)
            RETURNING ticket_id
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
    """
    Inserts a new message on an existing ticket.
    """
    if not message_text or not message_text.strip():
        raise ValueError("Message text cannot be empty.")
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
    """
    Updates the status of a ticket.
    new_status must be one of: open, in_progress, resolved
    """
    valid = {'open', 'in_progress', 'resolved'}
    if new_status not in valid:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of: {valid}")

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE tickets SET status = %s WHERE ticket_id = %s
        """, (new_status, ticket_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_ticket(ticket_id):
    """
    Deletes a ticket and all its messages (ON DELETE CASCADE handles messages).
    """
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


# ─────────────────────────────────────────
# QUICK TEST  (run: python db.py)
# ─────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Lakebase connection...")
    try:
        tickets = get_all_tickets()
        print(f"✅ Connected. Tickets found: {len(tickets)}")
        for t in tickets:
            print(f"   [{t['ticket_id']}] {t['title']} — {t['status']} ({t['priority']})")
        stats = get_stats()
        print(f"\n📊 Stats: {stats}")
    except Exception as e:
        print(f"❌ Error: {e}")
