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
        if not msgs: return "*No messages yet.*"
        lines = []
        for i, m in enumerate(msgs):
            lines.append(f"**💬 {m['author']}** &nbsp; `{fmt_time(m['created_at'])}`\n\n{m['message_text']}"
                         + ("\n\n---" if i < len(msgs)-1 else ""))
        return "\n\n".join(lines)
    except Exception as e:
        return f"❌ {e}"

def on_ticket_select(ticket_id_str):
    if not ticket_id_str: return "", "", "", "", "", "", ""
    try:
        t = get_ticket_by_id(int(ticket_id_str))
        if not t: return "❌ Not found", "", "", "", "", "", ""
        return (f"#{t['ticket_id']} — {t['title']}",
                STATUS_BADGE.get(t["status"], t["status"]),
                PRIORITY_BADGE.get(t["priority"], t["priority"]),
                t.get("category") or "general", t["created_by"],
                fmt_time(t["created_at"]), load_messages(int(ticket_id_str)))
    except Exception as e:
        return f"❌ {e}", "", "", "", "", "", ""

def on_filter_change(f): return load_ticket_table(f)

def on_create_ticket(title, priority, category, created_by):
    if not title.strip(): return "❌ Title is required.", load_ticket_table(), load_stats()
    if not created_by.strip(): return "❌ Name is required.", load_ticket_table(), load_stats()
    try:
        new_id = create_ticket(title.strip(), created_by.strip(), priority, category.strip() or None)
        return f"✅ Ticket **#{new_id}** created successfully!", load_ticket_table(), load_stats()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats()

def on_add_message(ticket_id, author, text):
    if not ticket_id: return "❌ No ticket loaded.", ""
    if not author.strip(): return "❌ Name required.", load_messages(ticket_id)
    if not text.strip():   return "❌ Message required.", load_messages(ticket_id)
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

def on_delete_ticket(ticket_id):
    if not ticket_id: return "❌ No ticket loaded.", load_ticket_table(), load_stats()
    try:
        delete_ticket(int(ticket_id))
        return f"✅ Ticket #{int(ticket_id)} deleted.", load_ticket_table(), load_stats()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats()

CSS = """
/* ── Base ── */
.gradio-container { background:#0d1117 !important; font-family:'Inter',sans-serif !important; }
footer { display:none !important; }

/* ── Header card ── */
.app-header {
    background: linear-gradient(135deg,#161b27,#1a2236);
    border:1px solid #21293d; border-radius:12px;
    padding:20px 28px; margin-bottom:12px;
}
.app-header h1 { font-size:22px; font-weight:700; color:#e2e8f0; margin:0 0 4px 0; }
.app-header p  { color:#64748b; font-size:13px; margin:0; }

/* ── Stats card ── */
.stats-card { background:#161b27; border:1px solid #21293d; border-radius:10px; padding:14px 20px; margin-bottom:10px; }
.stats-card table { width:auto !important; }
.stats-card th, .stats-card td { padding:6px 20px !important; font-size:14px !important; text-align:center !important; }

/* ── Tabs ── */
.tab-nav { border-bottom:1px solid #21293d !important; }
.tab-nav button { background:transparent !important; color:#64748b !important; border:none !important;
    border-bottom:2px solid transparent !important; border-radius:0 !important;
    font-size:13px !important; font-weight:500 !important; padding:8px 16px !important; margin-right:4px !important; }
.tab-nav button.selected { color:#3b82f6 !important; border-bottom-color:#3b82f6 !important; }
.tab-nav button:hover { color:#94a3b8 !important; }

/* ── Inputs ── */
input, textarea, select {
    background:#161b27 !important; border:1px solid #21293d !important;
    border-radius:6px !important; color:#e2e8f0 !important; font-size:13px !important;
}
input:focus, textarea:focus { border-color:#3b82f6 !important; box-shadow:0 0 0 2px rgba(59,130,246,0.15) !important; }
label { color:#94a3b8 !important; font-size:11px !important; font-weight:600 !important;
    text-transform:uppercase !important; letter-spacing:0.05em !important; }

/* ── Buttons — compact ── */
button { font-size:13px !important; font-weight:500 !important;
    padding:7px 16px !important; border-radius:6px !important;
    min-width:0 !important; height:34px !important; line-height:1 !important; }
button.primary { background:#2563eb !important; border:none !important; color:#fff !important; }
button.primary:hover { background:#1d4ed8 !important; }
button.secondary { background:#161b27 !important; border:1px solid #21293d !important; color:#94a3b8 !important; }
button.secondary:hover { border-color:#3b82f6 !important; color:#e2e8f0 !important; }
button.stop { background:#dc2626 !important; border:none !important; color:#fff !important; }
button.stop:hover { background:#b91c1c !important; }

/* ── Make Load Ticket button compact ── */
#load-btn { max-width:160px !important; }
#refresh-btn { max-width:120px !important; }

/* ── Dataframe ── */
.dataframe { border:1px solid #21293d !important; border-radius:8px !important; overflow:hidden !important; }
.dataframe thead tr th { background:#161b27 !important; color:#64748b !important;
    font-size:11px !important; font-weight:600 !important; text-transform:uppercase !important;
    letter-spacing:0.05em !important; padding:8px 12px !important; border-bottom:1px solid #21293d !important; }
.dataframe tbody tr td { background:#0d1117 !important; color:#e2e8f0 !important;
    font-size:12px !important; padding:8px 12px !important;
    border-bottom:1px solid #161b27 !important; }
.dataframe tbody tr:hover td { background:#161b27 !important; }

/* ── Message thread ── */
.msg-thread { background:#161b27; border:1px solid #21293d; border-radius:8px;
    padding:14px 16px; min-height:80px; font-size:13px; line-height:1.6; }

/* ── Section headings ── */
.section-head { font-size:11px !important; font-weight:700 !important; color:#64748b !important;
    text-transform:uppercase !important; letter-spacing:0.08em !important; margin:12px 0 6px 0 !important; }

/* ── Ticket detail fields ── */
.detail-row textarea { font-size:13px !important; padding:6px 10px !important; min-height:36px !important; }

/* ── Action result ── */
.action-result { font-size:13px !important; min-height:22px !important; }

/* ── Footer ── */
.app-footer { text-align:center; padding:12px; color:#374151; font-size:11px; margin-top:8px; }

/* ── Form group ── */
.form-group { background:#161b27; border:1px solid #21293d; border-radius:8px; padding:16px; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:#0d1117; }
::-webkit-scrollbar-thumb { background:#21293d; border-radius:3px; }
"""

with gr.Blocks(
    title="🎫 Support Ticketing — Lakebase",
    theme=gr.themes.Base(primary_hue="blue", neutral_hue="slate",
                         font=gr.themes.GoogleFont("Inter")),
    css=CSS,
) as demo:

    # Header
    gr.HTML("""<div class="app-header">
        <h1>🎫 Lakebase Support Ticketing System</h1>
        <p>Powered by Databricks Lakebase (managed Postgres) &nbsp;·&nbsp; Bootcamp Day 1 · 2026</p>
    </div>""")

    stats_md = gr.Markdown(load_stats(), elem_classes=["stats-card"])

    # ── TAB 1: All Tickets ──────────────────────────────────────
    with gr.Tab("📋 All Tickets"):
        with gr.Row(equal_height=True):
            filter_dd   = gr.Dropdown(choices=FILTER_OPTIONS, value="All",
                                      label="Filter by status", scale=3)
            refresh_btn = gr.Button("🔄 Refresh", scale=1, variant="secondary",
                                    elem_id="refresh-btn")

        ticket_table = gr.Dataframe(
            headers=["ID","Title","Status","Priority","Category","Created By","Created At","💬"],
            value=load_ticket_table(),
            interactive=False, wrap=True,
            column_widths=["4%","34%","11%","10%","10%","12%","13%","6%"],
        )
        filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
        refresh_btn.click(fn=lambda f: load_ticket_table(f), inputs=filter_dd, outputs=ticket_table)

    # ── TAB 2: View & Update ────────────────────────────────────
    with gr.Tab("🔍 View & Update Ticket"):
        with gr.Row(equal_height=True):
            ticket_id_input = gr.Number(label="Ticket ID", precision=0, scale=2)
            load_btn = gr.Button("Load Ticket →", variant="primary", scale=1,
                                 elem_id="load-btn")

        gr.Markdown("#### 📄 Ticket Details")
        with gr.Group(elem_classes=["form-group"]):
            with gr.Row(elem_classes=["detail-row"]):
                detail_title  = gr.Textbox(label="Title",  interactive=False, scale=4)
                detail_status = gr.Textbox(label="Status", interactive=False, scale=1)
            with gr.Row(elem_classes=["detail-row"]):
                detail_priority   = gr.Textbox(label="Priority",   interactive=False, scale=1)
                detail_category   = gr.Textbox(label="Category",   interactive=False, scale=1)
                detail_created_by = gr.Textbox(label="Created By", interactive=False, scale=1)
                detail_created_at = gr.Textbox(label="Created At", interactive=False, scale=2)

        gr.Markdown("#### 💬 Message Thread")
        message_thread = gr.Markdown("*Load a ticket to see its messages.*",
                                     elem_classes=["msg-thread"])

        with gr.Row():
            # Status update — left column
            with gr.Column(scale=2):
                gr.Markdown("#### 🔄 Update Status")
                with gr.Row():
                    new_status_dd     = gr.Dropdown(choices=STATUS_OPTIONS, value="open",
                                                    label="New status", scale=2)
                    update_status_btn = gr.Button("✅ Update", variant="primary", scale=1)
                    delete_btn        = gr.Button("🗑️ Delete", variant="stop",    scale=1)

            # Add message — right column
            with gr.Column(scale=3):
                gr.Markdown("#### ➕ Add Message")
                with gr.Row():
                    msg_author = gr.Textbox(label="Your name",
                                            placeholder="e.g. jay.dolai", scale=1)
                msg_text = gr.Textbox(label="Message", placeholder="Type your reply...",
                                      lines=2, scale=1)
                send_btn = gr.Button("📨 Send Message", variant="primary")

        action_result = gr.Markdown("", elem_classes=["action-result"])

        load_btn.click(fn=on_ticket_select, inputs=ticket_id_input,
            outputs=[detail_title, detail_status, detail_priority,
                     detail_category, detail_created_by, detail_created_at, message_thread])
        update_status_btn.click(fn=on_update_status, inputs=[ticket_id_input, new_status_dd],
            outputs=[action_result, detail_status])
        delete_btn.click(fn=on_delete_ticket, inputs=ticket_id_input,
            outputs=[action_result, ticket_table, stats_md])
        send_btn.click(fn=on_add_message, inputs=[ticket_id_input, msg_author, msg_text],
            outputs=[action_result, message_thread])

    # ── TAB 3: Create Ticket ────────────────────────────────────
    with gr.Tab("➕ Create New Ticket"):
        gr.Markdown("#### 🚀 Open a New Support Ticket")
        with gr.Group(elem_classes=["form-group"]):
            new_title = gr.Textbox(label="Title *", placeholder="Describe the issue briefly...")
            with gr.Row():
                new_priority = gr.Dropdown(choices=PRIORITY_OPTIONS, value="medium",
                                           label="Priority *", scale=1)
                new_category = gr.Textbox(label="Category",
                                          placeholder="e.g. infra, access, data, billing",
                                          scale=2)
            new_created_by = gr.Textbox(label="Your name / email *",
                                        placeholder="e.g. jay.dolai")

        create_btn    = gr.Button("🚀 Create Ticket", variant="primary")
        create_result = gr.Markdown("", elem_classes=["action-result"])

        create_btn.click(fn=on_create_ticket,
            inputs=[new_title, new_priority, new_category, new_created_by],
            outputs=[create_result, ticket_table, stats_md])

    gr.HTML("""<div class="app-footer">
        🎫 Lakebase Support Ticketing &nbsp;·&nbsp;
        Built with Gradio &amp; Databricks Lakebase &nbsp;·&nbsp; Bootcamp Day 1 · 2026
    </div>""")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT, show_error=True)
