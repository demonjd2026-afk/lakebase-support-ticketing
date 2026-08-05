import os
import gradio as gr
from db import (
    get_all_tickets, get_ticket_by_id, get_messages,
    get_stats, create_ticket, add_message, update_status, delete_ticket,
)

PORT = int(os.environ.get("DATABRICKS_APP_PORT", 8000))

STATUS_OPTIONS   = ["open", "in_progress", "resolved"]
PRIORITY_OPTIONS = ["low", "medium", "high"]
FILTER_OPTIONS   = ["All", "open", "in_progress", "resolved"]

STATUS_BADGE   = {"open": "🟡 Open", "in_progress": "🔵 In Progress", "resolved": "🟢 Resolved"}
PRIORITY_BADGE = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟢 Low"}

def fmt_time(ts):
    if ts is None: return ""
    if hasattr(ts, "strftime"): return ts.strftime("%d %b %Y, %H:%M")
    return str(ts)

def load_ticket_table(status_filter="All"):
    try:
        tickets = get_all_tickets(status_filter=status_filter if status_filter != "All" else None)
        return [[int(t["ticket_id"]), t["title"],
                 STATUS_BADGE.get(t["status"], t["status"]),
                 PRIORITY_BADGE.get(t["priority"], t["priority"]),
                 t.get("category") or "general", t["created_by"],
                 fmt_time(t["created_at"]), int(t.get("message_count", 0))]
                for t in tickets]
    except Exception as e:
        return [[f"❌ {e}", "", "", "", "", "", "", ""]]

def load_stats():
    try:
        s = get_stats()
        return (f"### 📊 Dashboard\n"
                f"| Total | 🟡 Open | 🔵 In Progress | 🟢 Resolved |\n"
                f"|:-----:|:-------:|:--------------:|:-----------:|\n"
                f"| **{s.get('total',0)}** | **{s.get('open',0)}** | "
                f"**{s.get('in_progress',0)}** | **{s.get('resolved',0)}** |")
    except Exception as e:
        return f"⚠️ {e}"

def load_messages(ticket_id):
    try:
        msgs = get_messages(int(ticket_id))
        if not msgs: return "*No messages yet. Add the first one below.*"
        lines = []
        for i, m in enumerate(msgs):
            lines.append(
                f"**💬 {m['author']}** &nbsp;&nbsp; `{fmt_time(m['created_at'])}`\n\n"
                f"{m['message_text']}" + ("\n\n---" if i < len(msgs)-1 else ""))
        return "\n\n".join(lines)
    except Exception as e:
        return f"❌ {e}"

def on_ticket_select(ticket_id_str):
    if not ticket_id_str: return "", "", "", "", "", "", ""
    try:
        t = get_ticket_by_id(int(ticket_id_str))
        if not t: return "❌ Ticket not found", "", "", "", "", "", ""
        return (f"#{t['ticket_id']} — {t['title']}",
                STATUS_BADGE.get(t["status"], t["status"]),
                PRIORITY_BADGE.get(t["priority"], t["priority"]),
                t.get("category") or "general", t["created_by"],
                fmt_time(t["created_at"]), load_messages(int(ticket_id_str)))
    except Exception as e:
        return f"❌ {e}", "", "", "", "", "", ""

def on_filter_change(f): return load_ticket_table(f)

def on_create_ticket(title, priority, category, created_by):
    if not title.strip():      return "❌ Title is required.", load_ticket_table(), load_stats()
    if not created_by.strip(): return "❌ Name is required.",  load_ticket_table(), load_stats()
    try:
        new_id = create_ticket(title.strip(), created_by.strip(), priority, category.strip() or None)
        return f"✅ Ticket **#{new_id}** created successfully!", load_ticket_table(), load_stats()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats()

def on_add_message(ticket_id, author, text):
    if not ticket_id:      return "❌ No ticket loaded.", ""
    if not author.strip(): return "❌ Name required.", load_messages(ticket_id)
    if not text.strip():   return "❌ Message cannot be empty.", load_messages(ticket_id)
    try:
        add_message(int(ticket_id), text.strip(), author.strip())
        return "✅ Message sent!", load_messages(ticket_id)
    except Exception as e:
        return f"❌ {e}", load_messages(ticket_id)

def on_update_status(ticket_id, new_status):
    if not ticket_id: return "❌ No ticket loaded.", ""
    try:
        update_status(int(ticket_id), new_status)
        return f"✅ Status updated to **{new_status}**", STATUS_BADGE.get(new_status, new_status)
    except Exception as e:
        return f"❌ {e}", ""

def on_delete_ticket(ticket_id, confirmed):
    if not ticket_id: return "❌ No ticket loaded.", load_ticket_table(), load_stats()
    if not confirmed: return "⚠️ Please tick the confirmation box before deleting.", load_ticket_table(), load_stats()
    try:
        delete_ticket(int(ticket_id))
        return f"✅ Ticket #{int(ticket_id)} deleted.", load_ticket_table(), load_stats()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats()

CSS = """
/* ── Page ── */
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; padding: 24px !important; }
footer { display: none !important; }

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #1a2744 100%);
    border: 1px solid #2d4a7a; border-radius: 14px;
    padding: 24px 32px; margin-bottom: 20px;
}
.app-header h1 { font-size: 24px; font-weight: 700; color: #e8f0fe; margin: 0 0 6px 0; }
.app-header p  { color: #90a4c8; font-size: 13px; margin: 0; }

/* ── Stats card ── */
.stats-card {
    background: #1a2035; border: 1px solid #2a3550;
    border-radius: 12px; padding: 16px 24px; margin-bottom: 20px;
}
.stats-card table { border-collapse: separate; border-spacing: 8px; }
.stats-card th { font-size: 12px !important; font-weight: 600 !important;
    color: #90a4c8 !important; padding: 8px 24px !important; text-align: center !important; }
.stats-card td { font-size: 22px !important; font-weight: 700 !important;
    color: #e8f0fe !important; padding: 4px 24px !important; text-align: center !important; }

/* ── Tabs ── */
.tab-nav { border-bottom: 2px solid #2a3550 !important; margin-bottom: 20px !important; gap: 4px !important; }
.tab-nav button {
    background: transparent !important; color: #64748b !important;
    border: none !important; border-bottom: 3px solid transparent !important;
    border-radius: 0 !important; font-size: 14px !important; font-weight: 500 !important;
    padding: 12px 24px !important; margin-bottom: -2px !important; transition: all 0.2s !important;
}
.tab-nav button.selected {
    color: #60a5fa !important; border-bottom-color: #60a5fa !important;
    background: rgba(96,165,250,0.05) !important;
}
.tab-nav button:hover { color: #94a3b8 !important; background: rgba(255,255,255,0.03) !important; }

/* ── Section headings inside tabs ── */
.section-title { font-size: 13px !important; font-weight: 600 !important;
    color: #64748b !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important; margin: 20px 0 10px 0 !important; }

/* ── Cards / Groups ── */
.card {
    background: #1a2035; border: 1px solid #2a3550;
    border-radius: 12px; padding: 20px; margin-bottom: 16px;
}
.danger-card {
    background: #1f1215; border: 1px solid #5c2020;
    border-radius: 12px; padding: 16px; margin-top: 12px;
}

/* ── Inputs & Dropdowns ── */
input[type="text"], input[type="number"], textarea, select,
.gr-input, .gr-textarea, .gr-dropdown {
    background: #0f1623 !important; border: 1.5px solid #2a3550 !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
    font-size: 14px !important; padding: 10px 14px !important;
    transition: border-color 0.2s !important;
}
input:focus, textarea:focus {
    border-color: #60a5fa !important;
    box-shadow: 0 0 0 3px rgba(96,165,250,0.12) !important;
    outline: none !important;
}
label span {
    color: #90a4c8 !important; font-size: 12px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── Buttons ── */
button.primary {
    background: #2563eb !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-size: 14px !important; font-weight: 600 !important;
    padding: 10px 20px !important; height: auto !important;
    transition: background 0.2s !important;
}
button.primary:hover { background: #1d4ed8 !important; }

button.secondary {
    background: #1a2035 !important; color: #94a3b8 !important;
    border: 1.5px solid #2a3550 !important; border-radius: 8px !important;
    font-size: 14px !important; font-weight: 500 !important;
    padding: 10px 20px !important; height: auto !important;
}
button.secondary:hover { border-color: #60a5fa !important; color: #e2e8f0 !important; }

button.stop {
    background: #991b1b !important; color: #fff !important;
    border: none !important; border-radius: 8px !important;
    font-size: 14px !important; font-weight: 600 !important;
    padding: 10px 20px !important; height: auto !important;
}
button.stop:hover { background: #7f1d1d !important; }

/* ── Message thread ── */
.msg-thread {
    background: #0f1623; border: 1px solid #2a3550;
    border-radius: 10px; padding: 16px 20px;
    min-height: 100px; font-size: 14px; line-height: 1.7;
}

/* ── Action result feedback ── */
.feedback { font-size: 14px !important; padding: 4px 0 !important; min-height: 26px !important; }

/* ── App footer ── */
.app-footer {
    text-align: center; padding: 16px; color: #374151;
    font-size: 12px; margin-top: 16px; border-top: 1px solid #1e2a3a;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0f1623; }
::-webkit-scrollbar-thumb { background: #2a3550; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #3b4f70; }
"""

with gr.Blocks(
    title="🎫 Support Ticketing — Lakebase",
    theme=gr.themes.Soft(
        primary_hue="blue",
        neutral_hue="slate",
        font=gr.themes.GoogleFont("Inter"),
    ),
    css=CSS,
) as demo:

    # ── Header ──────────────────────────────────────────────────
    gr.HTML("""
    <div class="app-header">
        <h1>🎫 Lakebase Support Ticketing System</h1>
        <p>Powered by Databricks Lakebase (managed Postgres) &nbsp;·&nbsp; Bootcamp Day 1 · 2026</p>
    </div>
    """)

    stats_md = gr.Markdown(load_stats(), elem_classes=["stats-card"])

    # ── TAB 1: All Tickets ──────────────────────────────────────
    with gr.Tab("📋  All Tickets"):
        gr.Markdown("Browse and filter all support tickets.", elem_classes=["section-title"])
        with gr.Row(equal_height=True):
            filter_dd   = gr.Dropdown(
                choices=FILTER_OPTIONS, value="All",
                label="🔍 Filter by status", scale=4,
            )
            refresh_btn = gr.Button("🔄  Refresh", variant="secondary", scale=1)

        ticket_table = gr.Dataframe(
            headers=["ID", "Title", "Status", "Priority", "Category", "Created By", "Created At", "💬"],
            value=load_ticket_table(),
            interactive=False,
            wrap=True,
        )

        filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
        refresh_btn.click(fn=lambda f: load_ticket_table(f), inputs=filter_dd, outputs=ticket_table)

    # ── TAB 2: View & Update ────────────────────────────────────
    with gr.Tab("🔍  View & Update Ticket"):
        gr.Markdown("Load any ticket to view details, messages, and take action.", elem_classes=["section-title"])

        with gr.Row(equal_height=True):
            ticket_id_input = gr.Number(label="Ticket ID", precision=0, scale=2,
                                        info="Enter the ticket ID from the list above")
            load_btn = gr.Button("📂  Load Ticket", variant="primary", scale=1)

        gr.Markdown("### 📄 Ticket Details")
        with gr.Group(elem_classes=["card"]):
            with gr.Row():
                detail_title  = gr.Textbox(label="Title",  interactive=False, scale=4)
                detail_status = gr.Textbox(label="Status", interactive=False, scale=1)
            with gr.Row():
                detail_priority   = gr.Textbox(label="Priority",   interactive=False, scale=1)
                detail_category   = gr.Textbox(label="Category",   interactive=False, scale=1)
                detail_created_by = gr.Textbox(label="Created By", interactive=False, scale=1)
                detail_created_at = gr.Textbox(label="Created At", interactive=False, scale=2)

        gr.Markdown("### 💬 Message Thread")
        message_thread = gr.Markdown(
            "*Enter a ticket ID above and click Load Ticket.*",
            elem_classes=["msg-thread"],
        )

        gr.Markdown("### ⚙️ Actions")
        with gr.Row():
            # Left: Status + Delete
            with gr.Column(scale=1):
                with gr.Group(elem_classes=["card"]):
                    gr.Markdown("**🔄 Update Status**")
                    new_status_dd = gr.Dropdown(
                        choices=STATUS_OPTIONS, value="open",
                        label="New status",
                    )
                    update_status_btn = gr.Button("✅  Update Status", variant="primary")

                with gr.Group(elem_classes=["danger-card"]):
                    gr.Markdown("**🗑️ Danger Zone**")
                    confirm_delete = gr.Checkbox(
                        label="I confirm I want to permanently delete this ticket and all its messages",
                        value=False,
                    )
                    delete_btn = gr.Button("🗑️  Delete Ticket", variant="stop")

            # Right: Add message
            with gr.Column(scale=2):
                with gr.Group(elem_classes=["card"]):
                    gr.Markdown("**➕ Add Message**")
                    msg_author = gr.Textbox(
                        label="Your name", placeholder="e.g. jay.dolai",
                    )
                    msg_text = gr.Textbox(
                        label="Message", placeholder="Type your reply here...", lines=4,
                    )
                    send_btn = gr.Button("📨  Send Message", variant="primary")

        action_result = gr.Markdown("", elem_classes=["feedback"])

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
            fn=on_delete_ticket, inputs=[ticket_id_input, confirm_delete],
            outputs=[action_result, ticket_table, stats_md],
        )
        send_btn.click(
            fn=on_add_message, inputs=[ticket_id_input, msg_author, msg_text],
            outputs=[action_result, message_thread],
        )

    # ── TAB 3: Create Ticket ────────────────────────────────────
    with gr.Tab("➕  Create New Ticket"):
        gr.Markdown("Fill in the details below to open a new support ticket.", elem_classes=["section-title"])

        with gr.Group(elem_classes=["card"]):
            new_title = gr.Textbox(
                label="Title *",
                placeholder="Briefly describe the issue...",
                info="Required — be specific so the team can triage quickly",
            )
            with gr.Row():
                new_priority = gr.Dropdown(
                    choices=PRIORITY_OPTIONS, value="medium",
                    label="Priority *", scale=1,
                    info="How urgently does this need attention?",
                )
                new_category = gr.Textbox(
                    label="Category",
                    placeholder="e.g. infra, access, data, billing",
                    scale=2,
                    info="Optional — helps route the ticket",
                )
            new_created_by = gr.Textbox(
                label="Your name / email *",
                placeholder="e.g. jay.dolai",
                info="Required — so the team knows who to contact",
            )

        create_btn    = gr.Button("🚀  Create Ticket", variant="primary")
        create_result = gr.Markdown("", elem_classes=["feedback"])

        create_btn.click(
            fn=on_create_ticket,
            inputs=[new_title, new_priority, new_category, new_created_by],
            outputs=[create_result, ticket_table, stats_md],
        )

    # ── Footer ──────────────────────────────────────────────────
    gr.HTML("""
    <div class="app-footer">
        🎫 Lakebase Support Ticketing &nbsp;·&nbsp;
        Built with Gradio &amp; Databricks Lakebase &nbsp;·&nbsp;
        Bootcamp Day 1 · 2026
    </div>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT, show_error=True)
