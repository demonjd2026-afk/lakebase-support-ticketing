# =============================================================
# app.py — Lakebase Support Ticketing System
# Gradio UI — Enhanced Design
# =============================================================

import os
import gradio as gr
from db import (
    get_all_tickets, get_ticket_by_id, get_messages,
    get_stats, create_ticket, add_message, update_status, delete_ticket,
)

PORT = int(os.environ.get("DATABRICKS_APP_PORT", 8000))

# ─────────────────────────────────────────
# CONSTANTS & HELPERS
# ─────────────────────────────────────────

STATUS_OPTIONS   = ["open", "in_progress", "resolved"]
PRIORITY_OPTIONS = ["low", "medium", "high"]
FILTER_OPTIONS   = ["All", "open", "in_progress", "resolved"]

STATUS_BADGE = {
    "open":        "🟡 Open",
    "in_progress": "🔵 In Progress",
    "resolved":    "🟢 Resolved",
}
PRIORITY_BADGE = {
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
                int(t["ticket_id"]),
                t["title"],
                STATUS_BADGE.get(t["status"], t["status"]),
                PRIORITY_BADGE.get(t["priority"], t["priority"]),
                t.get("category") or "general",
                t["created_by"],
                fmt_time(t["created_at"]),
                int(t.get("message_count", 0)),
            ])
        return rows
    except Exception as e:
        return [[f"❌ {e}", "", "", "", "", "", "", ""]]

def load_stats():
    try:
        s = get_stats()
        return (
            f"### 📊 Dashboard\n"
            f"| Total | 🟡 Open | 🔵 In Progress | 🟢 Resolved |\n"
            f"|:-----:|:-------:|:--------------:|:-----------:|\n"
            f"| **{s.get('total',0)}** | **{s.get('open',0)}** | "
            f"**{s.get('in_progress',0)}** | **{s.get('resolved',0)}** |"
        )
    except Exception as e:
        return f"⚠️ Could not load stats: {e}"

def load_messages(ticket_id):
    try:
        msgs = get_messages(int(ticket_id))
        if not msgs:
            return "*No messages yet. Be the first to reply below.*"
        lines = []
        for i, m in enumerate(msgs):
            lines.append(
                f"#### 💬 {m['author']}  `{fmt_time(m['created_at'])}`\n"
                f"{m['message_text']}\n"
                f"{'---' if i < len(msgs)-1 else ''}"
            )
        return "\n\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"

def on_ticket_select(ticket_id_str):
    if not ticket_id_str:
        return "", "", "", "", "", "", ""
    try:
        tid = int(ticket_id_str)
        t = get_ticket_by_id(tid)
        if not t:
            return "❌ Ticket not found", "", "", "", "", "", ""
        return (
            f"#{t['ticket_id']} — {t['title']}",
            STATUS_BADGE.get(t["status"], t["status"]),
            PRIORITY_BADGE.get(t["priority"], t["priority"]),
            t.get("category") or "general",
            t["created_by"],
            fmt_time(t["created_at"]),
            load_messages(tid),
        )
    except Exception as e:
        return f"❌ {e}", "", "", "", "", "", ""

def on_filter_change(f):
    return load_ticket_table(f)

def on_create_ticket(title, priority, category, created_by):
    errors = []
    if not title.strip():   errors.append("Title is required")
    if not created_by.strip(): errors.append("Name is required")
    if errors:
        return "❌ " + " · ".join(errors), load_ticket_table(), load_stats()
    try:
        new_id = create_ticket(title.strip(), created_by.strip(), priority, category.strip() or None)
        return f"✅ Ticket **#{new_id}** created!", load_ticket_table(), load_stats()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats()

def on_add_message(ticket_id, author, text):
    if not ticket_id: return "❌ No ticket loaded", ""
    if not author.strip(): return "❌ Name required", load_messages(ticket_id)
    if not text.strip():   return "❌ Message required", load_messages(ticket_id)
    try:
        add_message(int(ticket_id), text.strip(), author.strip())
        return "✅ Message sent!", load_messages(ticket_id)
    except Exception as e:
        return f"❌ {e}", load_messages(ticket_id)

def on_update_status(ticket_id, new_status):
    if not ticket_id: return "❌ No ticket loaded", ""
    try:
        update_status(int(ticket_id), new_status)
        return f"✅ Status → **{new_status}**", STATUS_BADGE.get(new_status, new_status)
    except Exception as e:
        return f"❌ {e}", ""

def on_delete_ticket(ticket_id):
    if not ticket_id: return "❌ No ticket loaded", load_ticket_table(), load_stats()
    try:
        delete_ticket(int(ticket_id))
        return f"✅ Ticket #{int(ticket_id)} deleted", load_ticket_table(), load_stats()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats()

# ─────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────

CSS = """
/* Page background */
.gradio-container { background: #0f1117 !important; color: #e8eaf0 !important; }

/* Header */
.app-header { 
    background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 16px;
}
.app-header h1 { font-size: 28px; font-weight: 700; color: #e2e8f0; margin: 0; }
.app-header p  { color: #718096; margin: 4px 0 0 0; font-size: 14px; }

/* Stats card */
.stats-card {
    background: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 16px 24px;
    margin-bottom: 12px;
}

/* Tab styling */
.tab-nav button {
    background: #1a1f2e !important;
    color: #a0aec0 !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px 8px 0 0 !important;
    font-weight: 600 !important;
    padding: 10px 20px !important;
}
.tab-nav button.selected {
    background: #2563eb !important;
    color: #ffffff !important;
    border-color: #2563eb !important;
}

/* Buttons */
button.primary { 
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; color: white !important;
}
button.secondary {
    background: #1a1f2e !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important; color: #a0aec0 !important;
}
button.stop { 
    background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important; color: white !important;
}

/* Inputs */
input, textarea, select {
    background: #1a1f2e !important;
    border: 1px solid #2d3748 !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
input:focus, textarea:focus {
    border-color: #2563eb !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.15) !important;
}

/* Dataframe */
.dataframe th {
    background: #1e293b !important;
    color: #94a3b8 !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    padding: 10px 14px !important;
}
.dataframe td {
    background: #0f1117 !important;
    color: #e2e8f0 !important;
    border-bottom: 1px solid #1e293b !important;
    padding: 10px 14px !important;
    font-size: 13px !important;
}
.dataframe tr:hover td { background: #1a1f2e !important; }

/* Ticket detail card */
.ticket-detail {
    background: #1a1f2e;
    border: 1px solid #2563eb;
    border-radius: 10px;
    padding: 20px;
}

/* Message thread */
.message-thread {
    background: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 16px;
    max-height: 400px;
    overflow-y: auto;
}

/* Labels */
label { color: #94a3b8 !important; font-size: 12px !important; font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; }

/* Result feedback */
.result-ok  { color: #34d399; font-weight: 600; }
.result-err { color: #f87171; font-weight: 600; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f1117; }
::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }
"""

# ─────────────────────────────────────────
# GRADIO UI
# ─────────────────────────────────────────

with gr.Blocks(
    title="🎫 Support Ticketing — Lakebase",
    theme=gr.themes.Base(
        primary_hue="blue",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=CSS,
) as demo:

    # ── Header ──────────────────────────
    gr.HTML("""
    <div class="app-header">
        <h1>🎫 Lakebase Support Ticketing System</h1>
        <p>Powered by Databricks Lakebase (managed Postgres) &nbsp;·&nbsp; Bootcamp Day 1 · 2026</p>
    </div>
    """)

    # ── Stats ────────────────────────────
    stats_md = gr.Markdown(load_stats(), elem_classes=["stats-card"])

    # ─────────────────────────────────────
    # TAB 1 — All Tickets
    # ─────────────────────────────────────
    with gr.Tab("📋  All Tickets"):
        with gr.Row(equal_height=True):
            filter_dd   = gr.Dropdown(
                choices=FILTER_OPTIONS, value="All",
                label="🔍 Filter by status", scale=2,
            )
            refresh_btn = gr.Button("🔄  Refresh", scale=1, variant="secondary")

        ticket_table = gr.Dataframe(
            headers=["ID", "Title", "Status", "Priority", "Category", "Created By", "Created At", "💬"],
            value=load_ticket_table(),
            interactive=False,
            wrap=True,
            column_widths=["4%","35%","10%","10%","10%","12%","13%","6%"],
        )

        filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
        refresh_btn.click(fn=lambda f: load_ticket_table(f), inputs=filter_dd, outputs=ticket_table)

    # ─────────────────────────────────────
    # TAB 2 — View / Update Ticket
    # ─────────────────────────────────────
    with gr.Tab("🔍  View & Update Ticket"):

        with gr.Row(equal_height=True):
            ticket_id_input = gr.Number(
                label="🎫 Ticket ID", precision=0, scale=1,
            )
            load_btn = gr.Button("Load Ticket →", variant="primary", scale=1)

        gr.Markdown("#### 📄 Ticket Details")
        with gr.Group():
            with gr.Row():
                detail_title    = gr.Textbox(label="Title", interactive=False, scale=3)
                detail_status   = gr.Textbox(label="Status", interactive=False, scale=1)
            with gr.Row():
                detail_priority   = gr.Textbox(label="Priority", interactive=False)
                detail_category   = gr.Textbox(label="Category", interactive=False)
                detail_created_by = gr.Textbox(label="Created By", interactive=False)
                detail_created_at = gr.Textbox(label="Created At", interactive=False)

        gr.Markdown("#### 💬 Message Thread")
        message_thread = gr.Markdown(
            "*Enter a ticket ID above and click Load Ticket.*",
            elem_classes=["message-thread"],
        )

        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("#### 🔄 Update Status")
                with gr.Row():
                    new_status_dd     = gr.Dropdown(choices=STATUS_OPTIONS, value="open", label="New Status", scale=2)
                    update_status_btn = gr.Button("✅ Update", variant="primary", scale=1)
                    delete_btn        = gr.Button("🗑️ Delete", variant="stop", scale=1)

            with gr.Column(scale=3):
                gr.Markdown("#### ➕ Add Message")
                msg_author = gr.Textbox(label="Your name", placeholder="e.g. jay.dolai")
                msg_text   = gr.Textbox(label="Message", placeholder="Type your reply...", lines=3)
                send_btn   = gr.Button("📨 Send Message", variant="primary")

        action_result = gr.Markdown("")

        # Wire events
        load_btn.click(
            fn=on_ticket_select, inputs=ticket_id_input,
            outputs=[detail_title, detail_status, detail_priority,
                     detail_category, detail_created_by, detail_created_at, message_thread],
        )
        update_status_btn.click(
            fn=on_update_status, inputs=[ticket_id_input, new_status_dd],
            outputs=[action_result, detail_status],
        )
        delete_btn.click(
            fn=on_delete_ticket, inputs=ticket_id_input,
            outputs=[action_result, ticket_table, stats_md],
        )
        send_btn.click(
            fn=on_add_message, inputs=[ticket_id_input, msg_author, msg_text],
            outputs=[action_result, message_thread],
        )

    # ─────────────────────────────────────
    # TAB 3 — Create Ticket
    # ─────────────────────────────────────
    with gr.Tab("➕  Create New Ticket"):
        gr.Markdown("#### 🚀 Open a New Support Ticket")
        gr.Markdown("*Fields marked with \* are required.*")

        with gr.Group():
            new_title = gr.Textbox(
                label="Title *",
                placeholder="Describe the issue briefly...",
                lines=1,
            )
            with gr.Row():
                new_priority = gr.Dropdown(
                    choices=PRIORITY_OPTIONS, value="medium",
                    label="Priority *",
                )
                new_category = gr.Textbox(
                    label="Category",
                    placeholder="e.g. infra, access, data, billing",
                )
            new_created_by = gr.Textbox(
                label="Your name / email *",
                placeholder="e.g. jay.dolai",
            )

        create_btn    = gr.Button("🚀 Create Ticket", variant="primary", size="lg")
        create_result = gr.Markdown("")

        create_btn.click(
            fn=on_create_ticket,
            inputs=[new_title, new_priority, new_category, new_created_by],
            outputs=[create_result, ticket_table, stats_md],
        )

    # ── Footer ───────────────────────────
    gr.HTML("""
    <div style="text-align:center; padding: 16px; color: #4a5568; font-size: 12px; margin-top: 8px;">
        🎫 Lakebase Support Ticketing &nbsp;·&nbsp; Built with Gradio &amp; Databricks Lakebase
        &nbsp;·&nbsp; Bootcamp Day 1 · 2026
    </div>
    """)


# ─────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=PORT,
        show_error=True,
    )
