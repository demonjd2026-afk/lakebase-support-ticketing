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


def load_stats_html():
    try:
        s = get_stats()
        return f"""
        <div class="stat-panel">
            <div class="stat-panel-title">Overview</div>
            <div class="stat-item stat-total">
                <div class="stat-value">{s.get('total',0)}</div>
                <div class="stat-label">Total Tickets</div>
            </div>
            <div class="stat-item stat-open">
                <div class="stat-value">{s.get('open',0)}</div>
                <div class="stat-label">🟡 Open</div>
            </div>
            <div class="stat-item stat-progress">
                <div class="stat-value">{s.get('in_progress',0)}</div>
                <div class="stat-label">🔵 In Progress</div>
            </div>
            <div class="stat-item stat-resolved">
                <div class="stat-value">{s.get('resolved',0)}</div>
                <div class="stat-label">🟢 Resolved</div>
            </div>
            <div class="stat-footer">
                <div class="stat-footer-label">Data Source</div>
                <div class="stat-footer-value">Databricks Lakebase</div>
                <div class="stat-footer-sub">Managed PostgreSQL · OLTP</div>
            </div>
        </div>
        """
    except Exception as e:
        return f'<div class="stat-panel"><div class="stat-error">⚠️ {e}</div></div>'


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
    if not title.strip():      return "❌ Title is required.", load_ticket_table(), load_stats_html()
    if not created_by.strip(): return "❌ Name is required.",  load_ticket_table(), load_stats_html()
    try:
        new_id = create_ticket(title.strip(), created_by.strip(), priority, category.strip() or None)
        return f"✅ Ticket **#{new_id}** created successfully!", load_ticket_table(), load_stats_html()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats_html()


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
    if not ticket_id: return "❌ No ticket loaded.", "", load_stats_html()
    try:
        update_status(int(ticket_id), new_status)
        return f"✅ Status updated to **{new_status}**", STATUS_BADGE.get(new_status, new_status), load_stats_html()
    except Exception as e:
        return f"❌ {e}", "", load_stats_html()


def on_delete_ticket(ticket_id, confirmed):
    if not ticket_id: return "❌ No ticket loaded.", load_ticket_table(), load_stats_html()
    if not confirmed: return "⚠️ Please tick the confirmation box before deleting.", load_ticket_table(), load_stats_html()
    try:
        delete_ticket(int(ticket_id))
        return f"✅ Ticket #{int(ticket_id)} deleted.", load_ticket_table(), load_stats_html()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats_html()


CSS = """
/* ══ FULL WIDTH LAYOUT ══ */
.gradio-container {
    max-width: 100% !important;
    width: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
}
.gradio-container > .main { padding: 0 !important; }
footer { display: none !important; }

/* ══ TOP NAV BAR ══ */
.top-nav {
    background: linear-gradient(90deg, #0c1628 0%, #142440 100%);
    border-bottom: 2px solid #1e3a5f;
    padding: 14px 32px;
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 0 !important;
}
.nav-brand { display: flex; align-items: center; gap: 12px; }
.nav-logo { font-size: 22px; }
.nav-title { font-size: 17px; font-weight: 700; color: #e8f0fe; letter-spacing: -0.2px; }
.nav-sub   { font-size: 11px; color: #6b8bb5; margin-top: 1px; }
.nav-right { font-size: 11px; color: #4a6b94; text-align: right; }
.nav-badge {
    display: inline-block; background: #1e3a5f; color: #7fb3ff;
    padding: 3px 10px; border-radius: 20px; font-size: 10px;
    font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase;
}

/* ══ SIDEBAR STAT PANEL ══ */
.stat-panel {
    background: #111a2e; border: 1px solid #1e2d47;
    border-radius: 10px; padding: 18px 16px;
    position: sticky; top: 16px;
}
.stat-panel-title {
    font-size: 11px; font-weight: 700; color: #4a6b94;
    text-transform: uppercase; letter-spacing: 0.1em;
    padding-bottom: 12px; margin-bottom: 14px;
    border-bottom: 1px solid #1e2d47;
}
.stat-item {
    padding: 12px 14px; margin-bottom: 8px;
    border-radius: 8px; border-left: 3px solid;
    background: #0c1424;
}
.stat-total    { border-left-color: #60a5fa; }
.stat-open     { border-left-color: #fbbf24; }
.stat-progress { border-left-color: #3b82f6; }
.stat-resolved { border-left-color: #34d399; }
.stat-value { font-size: 26px; font-weight: 700; color: #e8f0fe; line-height: 1.1; }
.stat-label { font-size: 11px; color: #6b8bb5; margin-top: 3px; font-weight: 500; }
.stat-footer {
    margin-top: 16px; padding-top: 14px;
    border-top: 1px solid #1e2d47;
}
.stat-footer-label { font-size: 10px; color: #4a6b94; text-transform: uppercase;
    letter-spacing: 0.08em; font-weight: 600; }
.stat-footer-value { font-size: 13px; color: #7fb3ff; font-weight: 600; margin-top: 4px; }
.stat-footer-sub   { font-size: 10px; color: #4a6b94; margin-top: 2px; }
.stat-error { color: #f87171; font-size: 12px; }

/* ══ TABS ══ */
.tab-nav {
    border-bottom: 2px solid #1e2d47 !important;
    margin-bottom: 18px !important; gap: 2px !important;
    padding-top: 0 !important;
}
.tab-nav button {
    background: transparent !important; color: #5a7ba6 !important;
    border: none !important; border-bottom: 3px solid transparent !important;
    border-radius: 0 !important; font-size: 13px !important;
    font-weight: 600 !important; padding: 11px 20px !important;
    margin-bottom: -2px !important; letter-spacing: 0.01em !important;
    transition: all 0.15s !important;
}
.tab-nav button.selected {
    color: #7fb3ff !important; border-bottom-color: #3b82f6 !important;
    background: rgba(59,130,246,0.06) !important;
}
.tab-nav button:hover { color: #94b8dd !important; }

/* ══ CONTENT CARDS ══ */
.panel {
    background: #111a2e; border: 1px solid #1e2d47;
    border-radius: 10px; padding: 18px; margin-bottom: 14px;
}
.panel-danger {
    background: #1a1015; border: 1px solid #4a1e1e;
    border-radius: 10px; padding: 16px; margin-top: 12px;
}
.panel-head {
    font-size: 12px !important; font-weight: 700 !important;
    color: #5a7ba6 !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important; margin: 0 0 12px 0 !important;
    padding-bottom: 8px !important; border-bottom: 1px solid #1e2d47 !important;
}
.hint { font-size: 12px !important; color: #4a6b94 !important; margin: 0 0 12px 0 !important; }

/* ══ INPUTS ══ */
input[type="text"], input[type="number"], textarea, select {
    background: #0c1424 !important; border: 1.5px solid #1e2d47 !important;
    border-radius: 7px !important; color: #dce7f5 !important;
    font-size: 13px !important; padding: 9px 12px !important;
}
input:focus, textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important; outline: none !important;
}
label span {
    color: #5a7ba6 !important; font-size: 11px !important;
    font-weight: 600 !important; text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ══ BUTTONS ══ */
button.primary {
    background: #2563eb !important; color: #fff !important; border: none !important;
    border-radius: 7px !important; font-size: 13px !important; font-weight: 600 !important;
    padding: 10px 18px !important; height: auto !important; transition: background 0.15s !important;
}
button.primary:hover { background: #1d4ed8 !important; }
button.secondary {
    background: #111a2e !important; color: #7fb3ff !important;
    border: 1.5px solid #1e3a5f !important; border-radius: 7px !important;
    font-size: 13px !important; font-weight: 600 !important;
    padding: 10px 18px !important; height: auto !important;
}
button.secondary:hover { background: #16233d !important; border-color: #3b82f6 !important; }
button.stop {
    background: #991b1b !important; color: #fff !important; border: none !important;
    border-radius: 7px !important; font-size: 13px !important; font-weight: 600 !important;
    padding: 10px 18px !important; height: auto !important;
}
button.stop:hover { background: #7f1d1d !important; }

/* ══ MESSAGE THREAD ══ */
.msg-thread {
    background: #0c1424; border: 1px solid #1e2d47; border-radius: 9px;
    padding: 16px 18px; min-height: 90px; font-size: 13px; line-height: 1.7;
    max-height: 340px; overflow-y: auto;
}

/* ══ FEEDBACK ══ */
.feedback { font-size: 13px !important; padding: 6px 0 !important; min-height: 24px !important; }

/* ══ FOOTER ══ */
.app-footer {
    text-align: center; padding: 14px; color: #2d3f5c;
    font-size: 11px; border-top: 1px solid #16233d; margin-top: 20px;
}

/* ══ SCROLLBAR ══ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0c1424; }
::-webkit-scrollbar-thumb { background: #1e2d47; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2d4266; }
"""

with gr.Blocks(
    title="Support Ticketing — Lakebase",
    theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate",
                         font=gr.themes.GoogleFont("Inter")),
    css=CSS,
) as demo:

    # ══ TOP NAVIGATION BAR ══════════════════════════════════════
    gr.HTML("""
    <div class="top-nav">
        <div class="nav-brand">
            <span class="nav-logo">🎫</span>
            <div>
                <div class="nav-title">Support Ticketing System</div>
                <div class="nav-sub">Internal IT Support Portal</div>
            </div>
        </div>
        <div class="nav-right">
            <span class="nav-badge">Databricks Lakebase</span>
            <div style="margin-top:5px">Bootcamp Day 1 · 2026</div>
        </div>
    </div>
    """)

    # ══ MAIN LAYOUT: Sidebar + Content ══════════════════════════
    with gr.Row(equal_height=False):

        # ── LEFT SIDEBAR (stats) ────────────────────────────────
        with gr.Column(scale=1, min_width=210):
            stats_html = gr.HTML(load_stats_html())

        # ── RIGHT CONTENT AREA (tabs) ───────────────────────────
        with gr.Column(scale=6):

            # ── TAB 1: All Tickets ──────────────────────────────
            with gr.Tab("📋  All Tickets"):
                gr.Markdown("Browse, filter, and monitor all support tickets in the queue.",
                            elem_classes=["hint"])
                with gr.Row(equal_height=True):
                    filter_dd = gr.Dropdown(choices=FILTER_OPTIONS, value="All",
                                            label="Filter by status", scale=5)
                    refresh_btn = gr.Button("🔄  Refresh", variant="secondary", scale=1)

                ticket_table = gr.Dataframe(
                    headers=["ID", "Title", "Status", "Priority", "Category",
                             "Created By", "Created At", "💬"],
                    value=load_ticket_table(), interactive=False, wrap=True,
                )
                filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
                refresh_btn.click(fn=lambda f: load_ticket_table(f),
                                  inputs=filter_dd, outputs=ticket_table)

            # ── TAB 2: View & Update ────────────────────────────
            with gr.Tab("🔍  View & Update"):
                gr.Markdown("Load a ticket by ID to view its full detail, message history, and take action.",
                            elem_classes=["hint"])

                with gr.Row(equal_height=True):
                    ticket_id_input = gr.Number(label="Ticket ID", precision=0, scale=5)
                    load_btn = gr.Button("📂  Load Ticket", variant="primary", scale=1)

                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("Ticket Details", elem_classes=["panel-head"])
                    with gr.Row():
                        detail_title  = gr.Textbox(label="Title",  interactive=False, scale=4)
                        detail_status = gr.Textbox(label="Status", interactive=False, scale=1)
                    with gr.Row():
                        detail_priority   = gr.Textbox(label="Priority",   interactive=False, scale=1)
                        detail_category   = gr.Textbox(label="Category",   interactive=False, scale=1)
                        detail_created_by = gr.Textbox(label="Created By", interactive=False, scale=1)
                        detail_created_at = gr.Textbox(label="Created At", interactive=False, scale=2)

                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("Message Thread", elem_classes=["panel-head"])
                    message_thread = gr.Markdown(
                        "*Enter a ticket ID above and click Load Ticket.*",
                        elem_classes=["msg-thread"])

                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes=["panel"]):
                            gr.Markdown("Update Status", elem_classes=["panel-head"])
                            new_status_dd = gr.Dropdown(choices=STATUS_OPTIONS, value="open",
                                                        label="New status")
                            update_status_btn = gr.Button("✅  Update Status", variant="primary")

                        with gr.Group(elem_classes=["panel-danger"]):
                            gr.Markdown("⚠️ Danger Zone", elem_classes=["panel-head"])
                            confirm_delete = gr.Checkbox(
                                label="I confirm permanent deletion of this ticket and all its messages",
                                value=False)
                            delete_btn = gr.Button("🗑️  Delete Ticket", variant="stop")

                    with gr.Column(scale=3):
                        with gr.Group(elem_classes=["panel"]):
                            gr.Markdown("Add Message", elem_classes=["panel-head"])
                            msg_author = gr.Textbox(label="Your name", placeholder="e.g. jay.dolai")
                            msg_text   = gr.Textbox(label="Message",
                                                    placeholder="Type your reply here...", lines=5)
                            send_btn   = gr.Button("📨  Send Message", variant="primary")

                action_result = gr.Markdown("", elem_classes=["feedback"])

                load_btn.click(fn=on_ticket_select, inputs=ticket_id_input,
                    outputs=[detail_title, detail_status, detail_priority,
                             detail_category, detail_created_by, detail_created_at, message_thread])
                update_status_btn.click(fn=on_update_status,
                    inputs=[ticket_id_input, new_status_dd],
                    outputs=[action_result, detail_status, stats_html])
                delete_btn.click(fn=on_delete_ticket,
                    inputs=[ticket_id_input, confirm_delete],
                    outputs=[action_result, ticket_table, stats_html])
                send_btn.click(fn=on_add_message,
                    inputs=[ticket_id_input, msg_author, msg_text],
                    outputs=[action_result, message_thread])

            # ── TAB 3: Create Ticket ────────────────────────────
            with gr.Tab("➕  New Ticket"):
                gr.Markdown("Raise a new support request. Fields marked with * are required.",
                            elem_classes=["hint"])

                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("Ticket Information", elem_classes=["panel-head"])
                    new_title = gr.Textbox(label="Title *",
                                           placeholder="Briefly describe the issue...")
                    with gr.Row():
                        new_priority = gr.Dropdown(choices=PRIORITY_OPTIONS, value="medium",
                                                   label="Priority *", scale=1)
                        new_category = gr.Textbox(label="Category",
                                                  placeholder="e.g. infra, access, data, billing",
                                                  scale=2)
                    new_created_by = gr.Textbox(label="Your name / email *",
                                                placeholder="e.g. jay.dolai")

                create_btn    = gr.Button("🚀  Create Ticket", variant="primary")
                create_result = gr.Markdown("", elem_classes=["feedback"])

                create_btn.click(fn=on_create_ticket,
                    inputs=[new_title, new_priority, new_category, new_created_by],
                    outputs=[create_result, ticket_table, stats_html])

    # ══ FOOTER ══════════════════════════════════════════════════
    gr.HTML("""
    <div class="app-footer">
        Support Ticketing System &nbsp;·&nbsp; Powered by Databricks Lakebase
        &nbsp;·&nbsp; Built with Gradio &nbsp;·&nbsp; Bootcamp Day 1 · 2026
    </div>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT, show_error=True)
