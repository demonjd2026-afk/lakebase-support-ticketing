# =============================================================
# app.py — Lakebase Support Ticketing System
# Gradio UI — Phase 3 (revised)
#
# Run locally:
#   export LAKEBASE_CONN="postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres"
#   python app.py
# =============================================================

import os
import gradio as gr
from db import (
    get_all_tickets,
    get_ticket_by_id,
    get_messages,
    get_stats,
    create_ticket,
    add_message,
    update_status,
    delete_ticket,
)

PORT = int(os.environ.get("DATABRICKS_APP_PORT", 8000))

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

STATUS_OPTIONS   = ["open", "in_progress", "resolved"]
PRIORITY_OPTIONS = ["low", "medium", "high"]
FILTER_OPTIONS   = ["All", "open", "in_progress", "resolved"]

STATUS_EMOJI = {
    "open":        "🟡 Open",
    "in_progress": "🔵 In Progress",
    "resolved":    "🟢 Resolved",
}

PRIORITY_EMOJI = {
    "high":   "🔴 High",
    "medium": "🟠 Medium",
    "low":    "🟢 Low",
}

def fmt_time(ts):
    if ts is None:
        return ""
    if hasattr(ts, "strftime"):
        return ts.strftime("%d %b %Y, %H:%M")
    return str(ts)


# ─────────────────────────────────────────
# DATA FUNCTIONS
# ─────────────────────────────────────────

def load_ticket_table(status_filter="All"):
    try:
        tickets = get_all_tickets(
            status_filter=status_filter if status_filter != "All" else None
        )
        rows = []
        for t in tickets:
            rows.append([
                t["ticket_id"],
                t["title"],
                STATUS_EMOJI.get(t["status"], t["status"]),
                PRIORITY_EMOJI.get(t["priority"], t["priority"]),
                t.get("category") or "general",
                t["created_by"],
                fmt_time(t["created_at"]),
                t.get("message_count", 0),
            ])
        return rows
    except Exception as e:
        return [[f"Error: {e}", "", "", "", "", "", "", ""]]


def load_stats():
    try:
        s = get_stats()
        return (
            f"📊 **Total:** {s.get('total',0)}  |  "
            f"🟡 **Open:** {s.get('open',0)}  |  "
            f"🔵 **In Progress:** {s.get('in_progress',0)}  |  "
            f"🟢 **Resolved:** {s.get('resolved',0)}"
        )
    except Exception as e:
        return f"Could not load stats: {e}"


def load_ticket_detail(ticket_id):
    try:
        t = get_ticket_by_id(int(ticket_id))
        if not t:
            return "Not found", "unknown", "unknown", "general", "unknown", "unknown"
        return (
            f"#{t['ticket_id']} — {t['title']}",
            t["status"],
            t["priority"],
            t.get("category") or "general",
            t["created_by"],
            fmt_time(t["created_at"]),
        )
    except Exception as e:
        return f"Error: {e}", "", "", "", "", ""


def load_messages(ticket_id):
    try:
        msgs = get_messages(int(ticket_id))
        if not msgs:
            return "_No messages yet. Add the first one below._"
        lines = []
        for m in msgs:
            lines.append(
                f"**👤 {m['author']}** — {fmt_time(m['created_at'])}\n\n"
                f"{m['message_text']}\n\n---"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error loading messages: {e}"


# ─────────────────────────────────────────
# ACTION FUNCTIONS
# ─────────────────────────────────────────

def on_filter_change(status_filter):
    return load_ticket_table(status_filter)


def on_create_ticket(title, priority, category, created_by):
    errors = []
    if not title.strip():
        errors.append("Title is required.")
    if not created_by.strip():
        errors.append("Your name is required.")
    if errors:
        return "❌ " + " | ".join(errors), load_ticket_table(), load_stats()
    try:
        new_id = create_ticket(
            title=title.strip(),
            created_by=created_by.strip(),
            priority=priority,
            category=category.strip() or None,
        )
        return (
            f"✅ Ticket #{new_id} created successfully!",
            load_ticket_table(),
            load_stats(),
        )
    except Exception as e:
        return f"❌ Error: {e}", load_ticket_table(), load_stats()


def on_add_message(ticket_id, author, message_text):
    errors = []
    if not ticket_id:
        errors.append("No ticket selected.")
    if not author.strip():
        errors.append("Your name is required.")
    if not message_text.strip():
        errors.append("Message cannot be empty.")
    if errors:
        return "❌ " + " | ".join(errors), load_messages(ticket_id) if ticket_id else ""
    try:
        add_message(int(ticket_id), message_text.strip(), author.strip())
        return "✅ Message sent!", load_messages(ticket_id)
    except Exception as e:
        return f"❌ Error: {e}", load_messages(ticket_id)


def on_update_status(ticket_id, new_status):
    if not ticket_id:
        return "❌ No ticket selected.", ""
    try:
        update_status(int(ticket_id), new_status)
        return f"✅ Status updated to **{new_status}**!", STATUS_EMOJI.get(new_status, new_status)
    except Exception as e:
        return f"❌ Error: {e}", ""


def on_delete_ticket(ticket_id):
    if not ticket_id:
        return "❌ No ticket selected.", load_ticket_table(), load_stats()
    try:
        delete_ticket(int(ticket_id))
        return (
            f"✅ Ticket #{ticket_id} deleted.",
            load_ticket_table(),
            load_stats(),
        )
    except Exception as e:
        return f"❌ Error: {e}", load_ticket_table(), load_stats()


def on_ticket_select(ticket_id_str):
    if not ticket_id_str:
        return "", "", "", "", "", "", ""
    try:
        tid = int(ticket_id_str)
        title, status, priority, category, created_by, created_at = load_ticket_detail(tid)
        messages = load_messages(tid)
        status_display = STATUS_EMOJI.get(status, status)
        return title, status_display, priority, category, created_by, created_at, messages
    except Exception as e:
        return f"Error: {e}", "", "", "", "", "", ""


# ─────────────────────────────────────────
# GRADIO UI
# ─────────────────────────────────────────

with gr.Blocks(title="🎫 Support Ticketing System", theme=gr.themes.Soft()) as demo:

    gr.Markdown("# 🎫 Lakebase Support Ticketing System")
    gr.Markdown("*Powered by Databricks Lakebase (managed Postgres) · Bootcamp Day 1*")

    stats_display = gr.Markdown(load_stats())

    # ── TAB 1: All Tickets ───────────────
    with gr.Tab("📋 All Tickets"):
        with gr.Row():
            filter_dd   = gr.Dropdown(choices=FILTER_OPTIONS, value="All", label="Filter by status", scale=1)
            refresh_btn = gr.Button("🔄 Refresh", scale=1)

        ticket_table = gr.Dataframe(
            headers=["ID", "Title", "Status", "Priority", "Category", "Created By", "Created At", "Messages"],
            value=load_ticket_table(),
            interactive=False,
            wrap=True,
        )

        filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
        refresh_btn.click(fn=lambda f: load_ticket_table(f), inputs=filter_dd, outputs=ticket_table)

    # ── TAB 2: View / Update Ticket ──────
    with gr.Tab("🔍 View / Update Ticket"):
        with gr.Row():
            ticket_id_input = gr.Number(label="Enter Ticket ID", precision=0, scale=1)
            load_btn        = gr.Button("Load Ticket →", variant="primary", scale=1)

        with gr.Row():
            detail_title  = gr.Textbox(label="Title", interactive=False, scale=3)
            detail_status = gr.Textbox(label="Status", interactive=False, scale=1)

        with gr.Row():
            detail_priority   = gr.Textbox(label="Priority", interactive=False, scale=1)
            detail_category   = gr.Textbox(label="Category", interactive=False, scale=1)
            detail_created_by = gr.Textbox(label="Created By", interactive=False, scale=1)
            detail_created_at = gr.Textbox(label="Created At", interactive=False, scale=1)

        gr.Markdown("### 💬 Message Thread")
        message_thread = gr.Markdown("_Load a ticket to see messages._")

        gr.Markdown("### 🔄 Update Status")
        with gr.Row():
            new_status_dd     = gr.Dropdown(choices=STATUS_OPTIONS, value="open", label="New status", scale=2)
            update_status_btn = gr.Button("✅ Update Status", variant="primary", scale=1)
            delete_btn        = gr.Button("🗑️ Delete Ticket", variant="stop", scale=1)

        gr.Markdown("### ➕ Add Message")
        with gr.Row():
            msg_author = gr.Textbox(label="Your name", placeholder="e.g. jay.dolai", scale=1)
            msg_text   = gr.Textbox(label="Message", placeholder="Type your message...", scale=3)
        send_btn = gr.Button("📨 Send Message", variant="primary")

        action_result = gr.Markdown("")

        load_btn.click(
            fn=on_ticket_select,
            inputs=ticket_id_input,
            outputs=[detail_title, detail_status, detail_priority,
                     detail_category, detail_created_by, detail_created_at, message_thread],
        )
        update_status_btn.click(
            fn=on_update_status,
            inputs=[ticket_id_input, new_status_dd],
            outputs=[action_result, detail_status],
        )
        delete_btn.click(
            fn=on_delete_ticket,
            inputs=ticket_id_input,
            outputs=[action_result, ticket_table, stats_display],
        )
        send_btn.click(
            fn=on_add_message,
            inputs=[ticket_id_input, msg_author, msg_text],
            outputs=[action_result, message_thread],
        )

    # ── TAB 3: Create Ticket ─────────────
    with gr.Tab("➕ Create Ticket"):
        gr.Markdown("Fields marked * are required.")
        new_title      = gr.Textbox(label="Title *", placeholder="Short description of the issue")
        with gr.Row():
            new_priority = gr.Dropdown(choices=PRIORITY_OPTIONS, value="medium", label="Priority *")
            new_category = gr.Textbox(label="Category", placeholder="e.g. infra, access, data, billing")
        new_created_by = gr.Textbox(label="Your name / email *", placeholder="e.g. jay.dolai")
        create_btn     = gr.Button("🚀 Create Ticket", variant="primary")
        create_result  = gr.Markdown("")

        create_btn.click(
            fn=on_create_ticket,
            inputs=[new_title, new_priority, new_category, new_created_by],
            outputs=[create_result, ticket_table, stats_display],
        )


# ─────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        show_error=True,
    )
