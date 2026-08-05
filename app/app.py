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

STATUS_BADGE   = {"open": "Open", "in_progress": "In Progress", "resolved": "Resolved"}
PRIORITY_BADGE = {"high": "High", "medium": "Medium", "low": "Low"}


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
        return [[f"Error: {e}", "", "", "", "", "", "", ""]]


def load_stats_html():
    try:
        s = get_stats()
        return f"""
        <div class="sidebar">
          <div class="sb-title">Overview</div>
          <div class="sb-stat sb-total">
            <span class="sb-num">{s.get('total',0)}</span>
            <span class="sb-lbl">Total tickets</span>
          </div>
          <div class="sb-stat sb-open">
            <span class="sb-num">{s.get('open',0)}</span>
            <span class="sb-lbl">Open</span>
          </div>
          <div class="sb-stat sb-prog">
            <span class="sb-num">{s.get('in_progress',0)}</span>
            <span class="sb-lbl">In progress</span>
          </div>
          <div class="sb-stat sb-res">
            <span class="sb-num">{s.get('resolved',0)}</span>
            <span class="sb-lbl">Resolved</span>
          </div>
          <div class="sb-foot">
            <div class="sb-foot-k">Data source</div>
            <div class="sb-foot-v">Databricks Lakebase</div>
            <div class="sb-foot-s">Managed PostgreSQL · OLTP</div>
          </div>
        </div>
        """
    except Exception as e:
        return f'<div class="sidebar"><div class="sb-err">{e}</div></div>'


def load_messages(ticket_id):
    try:
        msgs = get_messages(int(ticket_id))
        if not msgs: return "_No messages yet._"
        out = []
        for i, m in enumerate(msgs):
            out.append(f"**{m['author']}** &nbsp; `{fmt_time(m['created_at'])}`\n\n{m['message_text']}"
                       + ("\n\n---" if i < len(msgs)-1 else ""))
        return "\n\n".join(out)
    except Exception as e:
        return f"Error: {e}"


def on_ticket_select(tid):
    if not tid: return "", "", "", "", "", "", ""
    try:
        t = get_ticket_by_id(int(tid))
        if not t: return "Ticket not found", "", "", "", "", "", ""
        return (f"#{t['ticket_id']} — {t['title']}",
                STATUS_BADGE.get(t["status"], t["status"]),
                PRIORITY_BADGE.get(t["priority"], t["priority"]),
                t.get("category") or "general", t["created_by"],
                fmt_time(t["created_at"]), load_messages(int(tid)))
    except Exception as e:
        return f"Error: {e}", "", "", "", "", "", ""


def on_filter_change(f): return load_ticket_table(f)


def on_create_ticket(title, priority, category, created_by):
    if not title.strip():      return "⚠️ Title is required", load_ticket_table(), load_stats_html()
    if not created_by.strip(): return "⚠️ Name is required",  load_ticket_table(), load_stats_html()
    try:
        nid = create_ticket(title.strip(), created_by.strip(), priority, category.strip() or None)
        return f"✅ Ticket #{nid} created successfully", load_ticket_table(), load_stats_html()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats_html()


def on_add_message(tid, author, text):
    if not tid:            return "⚠️ No ticket loaded", ""
    if not author.strip(): return "⚠️ Name is required", load_messages(tid)
    if not text.strip():   return "⚠️ Message cannot be empty", load_messages(tid)
    try:
        add_message(int(tid), text.strip(), author.strip())
        return "✅ Message sent", load_messages(tid)
    except Exception as e:
        return f"❌ {e}", load_messages(tid)


def on_update_status(tid, new_status):
    if not tid: return "⚠️ No ticket loaded", "", load_stats_html()
    try:
        update_status(int(tid), new_status)
        return f"✅ Status updated to {new_status}", STATUS_BADGE.get(new_status, new_status), load_stats_html()
    except Exception as e:
        return f"❌ {e}", "", load_stats_html()


def on_delete_ticket(tid, confirmed):
    if not tid:       return "⚠️ No ticket loaded", load_ticket_table(), load_stats_html()
    if not confirmed: return "⚠️ Tick the confirmation box first", load_ticket_table(), load_stats_html()
    try:
        delete_ticket(int(tid))
        return f"✅ Ticket #{int(tid)} deleted", load_ticket_table(), load_stats_html()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats_html()


CSS = """
/* ═══ LAYOUT ═══ */
.gradio-container {
    max-width: 1400px !important;
    margin: 0 auto !important;
    padding: 0 28px 28px 28px !important;
    background: #fafbfc !important;
}
footer { display: none !important; }

/* ═══ TOP BAR ═══ */
.topbar {
    background: #ffffff;
    border-bottom: 1px solid #e3e8ef;
    padding: 16px 24px;
    margin: 0 -28px 20px -28px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 1px 3px rgba(16,24,40,0.04);
}
.tb-left { display: flex; align-items: center; gap: 12px; }
.tb-icon {
    width: 34px; height: 34px; border-radius: 8px;
    background: #eef2f6; display: flex; align-items: center;
    justify-content: center; font-size: 17px;
}
.tb-title { font-size: 15px; font-weight: 650; color: #101828; letter-spacing: -0.1px; }
.tb-sub   { font-size: 11.5px; color: #667085; margin-top: 1px; }
.tb-badge {
    background: #f0f4f8; color: #475467; border: 1px solid #e3e8ef;
    padding: 4px 11px; border-radius: 6px; font-size: 11px; font-weight: 600;
}
.tb-meta { font-size: 11px; color: #98a2b3; margin-top: 5px; text-align: right; }

/* ═══ SIDEBAR ═══ */
.sidebar {
    background: #ffffff; border: 1px solid #e3e8ef; border-radius: 10px;
    padding: 16px 14px; position: sticky; top: 14px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}
.sb-title {
    font-size: 10.5px; font-weight: 700; color: #98a2b3;
    text-transform: uppercase; letter-spacing: 0.07em;
    padding-bottom: 10px; margin-bottom: 12px; border-bottom: 1px solid #f0f2f5;
}
.sb-stat {
    display: block; padding: 10px 12px; margin-bottom: 7px;
    border-radius: 8px; background: #fafbfc; border-left: 3px solid;
}
.sb-total { border-left-color: #475467; }
.sb-open  { border-left-color: #dc9820; }
.sb-prog  { border-left-color: #3d6fd6; }
.sb-res   { border-left-color: #199873; }
.sb-num { display: block; font-size: 23px; font-weight: 700; color: #101828; line-height: 1.15; }
.sb-lbl { display: block; font-size: 11px; color: #667085; margin-top: 2px; font-weight: 500; }
.sb-foot { margin-top: 14px; padding-top: 12px; border-top: 1px solid #f0f2f5; }
.sb-foot-k { font-size: 9.5px; color: #98a2b3; text-transform: uppercase;
    letter-spacing: 0.07em; font-weight: 700; }
.sb-foot-v { font-size: 12px; color: #344054; font-weight: 600; margin-top: 3px; }
.sb-foot-s { font-size: 10px; color: #98a2b3; margin-top: 1px; }
.sb-err { color: #b42318; font-size: 11.5px; }

/* ═══ TABS ═══ */
.tab-nav {
    border-bottom: 1px solid #e3e8ef !important;
    margin-bottom: 16px !important; gap: 2px !important; background: transparent !important;
}
.tab-nav button {
    background: transparent !important; color: #667085 !important;
    border: none !important; border-bottom: 2px solid transparent !important;
    border-radius: 0 !important; font-size: 13px !important; font-weight: 600 !important;
    padding: 9px 16px !important; margin-bottom: -1px !important;
    transition: all 0.15s !important; letter-spacing: -0.01em !important;
}
.tab-nav button.selected {
    color: #344054 !important; border-bottom-color: #344054 !important;
}
.tab-nav button:hover { color: #344054 !important; }

/* ═══ PANELS ═══ */
.panel {
    background: #ffffff !important; border: 1px solid #e3e8ef !important;
    border-radius: 10px !important; padding: 16px !important; margin-bottom: 12px !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.03) !important;
}
.panel-danger {
    background: #fffbfa !important; border: 1px solid #fecdca !important;
    border-radius: 10px !important; padding: 14px !important; margin-top: 10px !important;
}
.phead {
    font-size: 10.5px !important; font-weight: 700 !important; color: #98a2b3 !important;
    text-transform: uppercase !important; letter-spacing: 0.07em !important;
    margin: 0 0 11px 0 !important; padding-bottom: 8px !important;
    border-bottom: 1px solid #f0f2f5 !important;
}
.hint { font-size: 12.5px !important; color: #667085 !important; margin: 0 0 12px 0 !important; }

/* ═══ INPUTS ═══ */
input[type="text"], input[type="number"], textarea, select {
    background: #ffffff !important; border: 1px solid #d0d5dd !important;
    border-radius: 7px !important; color: #101828 !important;
    font-size: 13px !important; padding: 8px 11px !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04) !important;
}
input:focus, textarea:focus {
    border-color: #84a9e0 !important;
    box-shadow: 0 0 0 3px rgba(61,111,214,0.10) !important; outline: none !important;
}
label span {
    color: #344054 !important; font-size: 11.5px !important;
    font-weight: 600 !important; text-transform: none !important;
    letter-spacing: 0 !important;
}

/* ═══ BUTTONS — compact ═══ */
button.primary {
    background: #344054 !important; color: #fff !important; border: none !important;
    border-radius: 7px !important; font-size: 12.5px !important; font-weight: 600 !important;
    padding: 8px 15px !important; height: 36px !important; min-height: 36px !important;
    max-height: 36px !important; line-height: 1 !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.06) !important; transition: background 0.15s !important;
}
button.primary:hover { background: #1d2939 !important; }

button.secondary {
    background: #ffffff !important; color: #344054 !important;
    border: 1px solid #d0d5dd !important; border-radius: 7px !important;
    font-size: 12.5px !important; font-weight: 600 !important;
    padding: 8px 15px !important; height: 36px !important; min-height: 36px !important;
    max-height: 36px !important; line-height: 1 !important;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04) !important;
}
button.secondary:hover { background: #f9fafb !important; border-color: #98a2b3 !important; }

button.stop {
    background: #b42318 !important; color: #fff !important; border: none !important;
    border-radius: 7px !important; font-size: 12.5px !important; font-weight: 600 !important;
    padding: 8px 15px !important; height: 36px !important; min-height: 36px !important;
    max-height: 36px !important; line-height: 1 !important;
}
button.stop:hover { background: #912018 !important; }

/* ═══ MESSAGE THREAD ═══ */
.msg-thread {
    background: #fafbfc; border: 1px solid #e3e8ef; border-radius: 8px;
    padding: 14px 16px; min-height: 80px; font-size: 12.5px; line-height: 1.65;
    max-height: 300px; overflow-y: auto; color: #344054;
}
.msg-thread strong { color: #101828; }
.msg-thread code { background: #f0f2f5; padding: 1px 5px; border-radius: 4px;
    font-size: 10.5px; color: #667085; }
.msg-thread hr { border: none; border-top: 1px solid #eaecf0; margin: 10px 0; }

/* ═══ FEEDBACK ═══ */
.feedback { font-size: 12.5px !important; padding: 5px 0 !important;
    min-height: 22px !important; color: #344054 !important; font-weight: 500 !important; }

/* ═══ FOOTER ═══ */
.appfoot {
    text-align: center; padding: 14px; color: #98a2b3;
    font-size: 11px; border-top: 1px solid #e3e8ef; margin-top: 18px;
}

/* ═══ SCROLLBAR ═══ */
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-track { background: #f0f2f5; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #98a2b3; }
"""

with gr.Blocks(
    title="Support Ticketing — Lakebase",
    theme=gr.themes.Soft(primary_hue="slate", neutral_hue="slate",
                         font=gr.themes.GoogleFont("Inter")),
    css=CSS,
) as demo:

    # ═══ TOP BAR ════════════════════════════════════════════════
    gr.HTML("""
    <div class="topbar">
      <div class="tb-left">
        <div class="tb-icon">🎫</div>
        <div>
          <div class="tb-title">Support Ticketing System</div>
          <div class="tb-sub">Internal IT support portal</div>
        </div>
      </div>
      <div>
        <span class="tb-badge">Databricks Lakebase</span>
        <div class="tb-meta">Bootcamp Day 1 · 2026</div>
      </div>
    </div>
    """)

    with gr.Row(equal_height=False):

        # ── SIDEBAR ─────────────────────────────────────────────
        with gr.Column(scale=1, min_width=190):
            stats_html = gr.HTML(load_stats_html())

        # ── CONTENT ─────────────────────────────────────────────
        with gr.Column(scale=7):

            # ══ TAB 1 ══════════════════════════════════════════
            with gr.Tab("All Tickets"):
                gr.Markdown("Browse and filter every ticket in the support queue.",
                            elem_classes=["hint"])
                with gr.Row(equal_height=True):
                    filter_dd   = gr.Dropdown(choices=FILTER_OPTIONS, value="All",
                                              label="Filter by status", scale=6)
                    refresh_btn = gr.Button("Refresh", variant="secondary", scale=1)

                ticket_table = gr.Dataframe(
                    headers=["ID", "Title", "Status", "Priority", "Category",
                             "Created by", "Created at", "Msgs"],
                    value=load_ticket_table(), interactive=False, wrap=True,
                )
                filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
                refresh_btn.click(fn=lambda f: load_ticket_table(f),
                                  inputs=filter_dd, outputs=ticket_table)

            # ══ TAB 2 ══════════════════════════════════════════
            with gr.Tab("View & Update"):
                gr.Markdown("Load a ticket by ID to see its details, history, and take action.",
                            elem_classes=["hint"])

                with gr.Row(equal_height=True):
                    ticket_id_input = gr.Number(label="Ticket ID", precision=0, scale=6)
                    load_btn = gr.Button("Load ticket", variant="primary", scale=1)

                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("Ticket details", elem_classes=["phead"])
                    with gr.Row():
                        detail_title  = gr.Textbox(label="Title",  interactive=False, scale=4)
                        detail_status = gr.Textbox(label="Status", interactive=False, scale=1)
                    with gr.Row():
                        detail_priority   = gr.Textbox(label="Priority",   interactive=False, scale=1)
                        detail_category   = gr.Textbox(label="Category",   interactive=False, scale=1)
                        detail_created_by = gr.Textbox(label="Created by", interactive=False, scale=1)
                        detail_created_at = gr.Textbox(label="Created at", interactive=False, scale=2)

                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("Message thread", elem_classes=["phead"])
                    message_thread = gr.Markdown(
                        "_Enter a ticket ID above and click Load ticket._",
                        elem_classes=["msg-thread"])

                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes=["panel"]):
                            gr.Markdown("Update status", elem_classes=["phead"])
                            new_status_dd = gr.Dropdown(choices=STATUS_OPTIONS, value="open",
                                                        label="New status")
                            update_status_btn = gr.Button("Update status", variant="primary")

                        with gr.Group(elem_classes=["panel-danger"]):
                            gr.Markdown("Danger zone", elem_classes=["phead"])
                            confirm_delete = gr.Checkbox(
                                label="I confirm permanent deletion of this ticket and its messages",
                                value=False)
                            delete_btn = gr.Button("Delete ticket", variant="stop")

                    with gr.Column(scale=3):
                        with gr.Group(elem_classes=["panel"]):
                            gr.Markdown("Add message", elem_classes=["phead"])
                            msg_author = gr.Textbox(label="Your name", placeholder="e.g. jay.dolai")
                            msg_text   = gr.Textbox(label="Message",
                                                    placeholder="Type your reply...", lines=5)
                            send_btn   = gr.Button("Send message", variant="primary")

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

            # ══ TAB 3 ══════════════════════════════════════════
            with gr.Tab("New Ticket"):
                gr.Markdown("Raise a new support request. Fields marked * are required.",
                            elem_classes=["hint"])

                with gr.Group(elem_classes=["panel"]):
                    gr.Markdown("Ticket information", elem_classes=["phead"])
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

                create_btn    = gr.Button("Create ticket", variant="primary")
                create_result = gr.Markdown("", elem_classes=["feedback"])

                create_btn.click(fn=on_create_ticket,
                    inputs=[new_title, new_priority, new_category, new_created_by],
                    outputs=[create_result, ticket_table, stats_html])

    gr.HTML("""
    <div class="appfoot">
      Support Ticketing System · Powered by Databricks Lakebase · Built with Gradio · Bootcamp Day 1 · 2026
    </div>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT, show_error=True)
