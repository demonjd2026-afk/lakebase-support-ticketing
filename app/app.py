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
        <div class="sb">
          <div class="sb-h">Overview</div>
          <div class="sb-c"><span class="sb-n">{s.get('total',0)}</span><span class="sb-l">Total tickets</span></div>
          <div class="sb-c sb-o"><span class="sb-n">{s.get('open',0)}</span><span class="sb-l">Open</span></div>
          <div class="sb-c sb-p"><span class="sb-n">{s.get('in_progress',0)}</span><span class="sb-l">In progress</span></div>
          <div class="sb-c sb-r"><span class="sb-n">{s.get('resolved',0)}</span><span class="sb-l">Resolved</span></div>
          <div class="sb-f">
            <div class="sb-fk">Data source</div>
            <div class="sb-fv">Databricks Lakebase</div>
            <div class="sb-fs">Managed PostgreSQL · OLTP</div>
          </div>
        </div>
        """
    except Exception as e:
        return f'<div class="sb"><div class="sb-e">{e}</div></div>'


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
/* ═══ FORCE LIGHT THEME EVERYWHERE ═══ */
*, *::before, *::after { color-scheme: light !important; }

body, .gradio-container, .app, .main, .wrap, .contain,
.block, .form, .panel, .gap, .styler, .container,
[class*="svelte"], [class*="block"], [class*="form"] {
    background: transparent !important;
    background-color: transparent !important;
    border-color: #e5e7eb !important;
}

.gradio-container {
    max-width: 1340px !important; margin: 0 auto !important;
    padding: 0 24px 24px 24px !important;
    background: #f9fafb !important; color: #111827 !important;
}
body { background: #f9fafb !important; }
footer { display: none !important; }

/* ═══ ALL TEXT DARK ═══ */
p, span, div, label, h1, h2, h3, h4, h5, h6, li, td, th {
    color: #374151 !important;
}

/* ═══ TOP BAR ═══ */
.topbar {
    background: #ffffff !important; border-bottom: 1px solid #e5e7eb !important;
    padding: 14px 22px; margin: 0 -24px 18px -24px;
    display: flex; align-items: center; justify-content: space-between;
}
.tb-l { display: flex; align-items: center; gap: 11px; }
.tb-i { width: 32px; height: 32px; border-radius: 8px; background: #f3f4f6 !important;
        display: flex; align-items: center; justify-content: center; font-size: 16px; }
.tb-t { font-size: 15px !important; font-weight: 650 !important; color: #111827 !important; }
.tb-s { font-size: 11.5px !important; color: #9ca3af !important; margin-top: 1px; }
.tb-b { background: #eef2ff !important; color: #4338ca !important; border: 1px solid #e0e7ff !important;
        padding: 4px 11px; border-radius: 6px; font-size: 10.5px !important; font-weight: 600 !important; }
.tb-m { font-size: 10.5px !important; color: #9ca3af !important; margin-top: 5px; text-align: right; }

/* ═══ SIDEBAR ═══ */
.sb { background: #ffffff !important; border: 1px solid #e5e7eb !important; border-radius: 10px;
      padding: 15px 13px; position: sticky; top: 13px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.sb-h { font-size: 10px !important; font-weight: 700 !important; color: #9ca3af !important;
        text-transform: uppercase; letter-spacing: 0.08em;
        padding-bottom: 9px; margin-bottom: 11px; border-bottom: 1px solid #f3f4f6 !important; }
.sb-c { display: block; padding: 10px 12px; margin-bottom: 6px; border-radius: 8px;
        background: #f9fafb !important; border-left: 3px solid #9ca3af; }
.sb-o { border-left-color: #f59e0b !important; background: #fffbeb !important; }
.sb-p { border-left-color: #3b82f6 !important; background: #eff6ff !important; }
.sb-r { border-left-color: #10b981 !important; background: #ecfdf5 !important; }
.sb-n { display: block; font-size: 22px !important; font-weight: 700 !important;
        color: #111827 !important; line-height: 1.15; }
.sb-l { display: block; font-size: 11px !important; color: #6b7280 !important;
        margin-top: 2px; font-weight: 500 !important; }
.sb-f { margin-top: 13px; padding-top: 11px; border-top: 1px solid #f3f4f6 !important; }
.sb-fk { font-size: 9px !important; color: #9ca3af !important; text-transform: uppercase;
         letter-spacing: 0.08em; font-weight: 700 !important; }
.sb-fv { font-size: 12px !important; color: #374151 !important; font-weight: 600 !important; margin-top: 3px; }
.sb-fs { font-size: 10px !important; color: #9ca3af !important; margin-top: 1px; }
.sb-e  { color: #dc2626 !important; font-size: 11px !important; }

/* ═══ TABS ═══ */
.tab-nav { border-bottom: 1px solid #e5e7eb !important; margin-bottom: 16px !important;
           gap: 4px !important; background: transparent !important; }
.tab-nav button {
    background: transparent !important; color: #6b7280 !important;
    border: none !important; border-bottom: 2px solid transparent !important;
    border-radius: 0 !important; font-size: 13px !important; font-weight: 600 !important;
    padding: 10px 16px !important; margin-bottom: -1px !important;
}
.tab-nav button.selected { color: #4338ca !important; border-bottom-color: #4338ca !important; }
.tab-nav button:hover { color: #4b5563 !important; }

/* ═══ PANELS / GROUPS ═══ */
.pnl, .pnl > *, .pnl .block, .pnl .form {
    background: #ffffff !important; border-radius: 10px !important;
}
.pnl {
    border: 1px solid #e5e7eb !important; padding: 16px !important;
    margin-bottom: 12px !important; box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
}
.pnl-d, .pnl-d > *, .pnl-d .block, .pnl-d .form {
    background: #fef2f2 !important; border-radius: 10px !important;
}
.pnl-d { border: 1px solid #fecaca !important; padding: 14px !important; margin-top: 10px !important; }

.ph, .ph * {
    font-size: 10.5px !important; font-weight: 700 !important; color: #9ca3af !important;
    text-transform: uppercase !important; letter-spacing: 0.08em !important;
    background: transparent !important;
}
.ph { margin: 0 0 11px 0 !important; padding-bottom: 8px !important;
      border-bottom: 1px solid #f3f4f6 !important; }
.hint, .hint * { font-size: 12.5px !important; color: #6b7280 !important;
                 background: transparent !important; margin: 0 0 12px 0 !important; }

/* ═══ INPUTS ═══ */
input[type="text"], input[type="number"], textarea, select {
    background: #ffffff !important; border: 1px solid #d1d5db !important;
    border-radius: 7px !important; color: #111827 !important;
    font-size: 13px !important; padding: 9px 12px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
}
input:focus, textarea:focus, select:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.10) !important; outline: none !important;
}
input::placeholder, textarea::placeholder { color: #9ca3af !important; }
label, label span {
    color: #374151 !important; font-size: 12px !important; font-weight: 600 !important;
    text-transform: none !important; letter-spacing: 0 !important;
    background: transparent !important;
}

/* ═══ BUTTONS ═══ */
button.primary, button.secondary, button.stop {
    border-radius: 7px !important; font-size: 13px !important; font-weight: 600 !important;
    padding: 0 18px !important; height: 36px !important; min-height: 36px !important;
    max-height: 36px !important; line-height: 36px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
button.primary { background: #4f46e5 !important; color: #ffffff !important; border: none !important; }
button.primary:hover { background: #4338ca !important; }
button.primary span { color: #ffffff !important; }

button.secondary { background: #ffffff !important; color: #374151 !important;
                   border: 1px solid #d1d5db !important; }
button.secondary:hover { background: #f9fafb !important; }
button.secondary span { color: #374151 !important; }

button.stop { background: #dc2626 !important; color: #ffffff !important; border: none !important; }
button.stop:hover { background: #b91c1c !important; }
button.stop span { color: #ffffff !important; }

/* ═══ DATAFRAME ═══ */
table, table th, table td { background: #ffffff !important; color: #374151 !important; }
table th { background: #f9fafb !important; color: #6b7280 !important;
           font-size: 11px !important; font-weight: 600 !important; }
table td { font-size: 12.5px !important; border-color: #f3f4f6 !important; }

/* ═══ MESSAGE THREAD ═══ */
.msg, .msg * { background: transparent !important; }
.msg { background: #f9fafb !important; border: 1px solid #e5e7eb !important;
       border-radius: 8px; padding: 14px 16px; min-height: 80px;
       font-size: 12.5px !important; line-height: 1.65; max-height: 300px;
       overflow-y: auto; color: #4b5563 !important; }
.msg strong { color: #111827 !important; font-weight: 600 !important; }
.msg code { background: #eef2ff !important; padding: 1px 6px; border-radius: 4px;
            font-size: 10.5px !important; color: #4338ca !important; }
.msg hr { border: none; border-top: 1px solid #e5e7eb; margin: 10px 0; }

/* ═══ FEEDBACK ═══ */
.fb, .fb * { font-size: 13px !important; color: #374151 !important;
             font-weight: 500 !important; background: transparent !important; }
.fb { padding: 6px 0 !important; min-height: 24px !important; }

/* ═══ CHECKBOX ═══ */
input[type="checkbox"] { accent-color: #4f46e5 !important; }

/* ═══ FOOTER ═══ */
.ft, .ft * { text-align: center; color: #9ca3af !important; font-size: 11px !important;
             background: transparent !important; }
.ft { padding: 14px; border-top: 1px solid #e5e7eb; margin-top: 18px; }

/* ═══ SCROLLBAR ═══ */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f3f4f6; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
"""

with gr.Blocks(
    title="Support Ticketing — Lakebase",
    theme=gr.themes.Default(primary_hue="indigo", neutral_hue="gray",
                            font=gr.themes.GoogleFont("Inter")),
    css=CSS,
) as demo:

    gr.HTML("""
    <div class="topbar">
      <div class="tb-l">
        <div class="tb-i">🎫</div>
        <div>
          <div class="tb-t">Support Ticketing System</div>
          <div class="tb-s">Internal IT support portal</div>
        </div>
      </div>
      <div>
        <span class="tb-b">Databricks Lakebase</span>
        <div class="tb-m">Bootcamp Day 1 · 2026</div>
      </div>
    </div>
    """)

    with gr.Row(equal_height=False):

        with gr.Column(scale=1, min_width=185):
            stats_html = gr.HTML(load_stats_html())

        with gr.Column(scale=7):

            with gr.Tab("All Tickets"):
                gr.Markdown("Browse and filter every ticket in the support queue.", elem_classes=["hint"])
                with gr.Row(equal_height=True):
                    filter_dd   = gr.Dropdown(choices=FILTER_OPTIONS, value="All",
                                              label="Filter by status", scale=6)
                    refresh_btn = gr.Button("Refresh", variant="secondary", scale=1)

                ticket_table = gr.Dataframe(
                    headers=["ID", "Title", "Status", "Priority", "Category",
                             "Created by", "Created at", "Msgs"],
                    value=load_ticket_table(), interactive=False, wrap=True)

                filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
                refresh_btn.click(fn=lambda f: load_ticket_table(f),
                                  inputs=filter_dd, outputs=ticket_table)

            with gr.Tab("View & Update"):
                gr.Markdown("Load a ticket by ID to see its details, history, and take action.",
                            elem_classes=["hint"])

                with gr.Row(equal_height=True):
                    ticket_id_input = gr.Number(label="Ticket ID", precision=0, scale=6)
                    load_btn = gr.Button("Load ticket", variant="primary", scale=1)

                with gr.Group(elem_classes=["pnl"]):
                    gr.Markdown("Ticket details", elem_classes=["ph"])
                    with gr.Row():
                        detail_title  = gr.Textbox(label="Title",  interactive=False, scale=4)
                        detail_status = gr.Textbox(label="Status", interactive=False, scale=1)
                    with gr.Row():
                        detail_priority   = gr.Textbox(label="Priority",   interactive=False, scale=1)
                        detail_category   = gr.Textbox(label="Category",   interactive=False, scale=1)
                        detail_created_by = gr.Textbox(label="Created by", interactive=False, scale=1)
                        detail_created_at = gr.Textbox(label="Created at", interactive=False, scale=2)

                with gr.Group(elem_classes=["pnl"]):
                    gr.Markdown("Message thread", elem_classes=["ph"])
                    message_thread = gr.Markdown("_Enter a ticket ID above and click Load ticket._",
                                                 elem_classes=["msg"])

                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes=["pnl"]):
                            gr.Markdown("Update status", elem_classes=["ph"])
                            new_status_dd = gr.Dropdown(choices=STATUS_OPTIONS, value="open",
                                                        label="New status")
                            update_status_btn = gr.Button("Update status", variant="primary")

                        with gr.Group(elem_classes=["pnl-d"]):
                            gr.Markdown("Danger zone", elem_classes=["ph"])
                            confirm_delete = gr.Checkbox(
                                label="I confirm permanent deletion of this ticket and its messages",
                                value=False)
                            delete_btn = gr.Button("Delete ticket", variant="stop")

                    with gr.Column(scale=3):
                        with gr.Group(elem_classes=["pnl"]):
                            gr.Markdown("Add message", elem_classes=["ph"])
                            msg_author = gr.Textbox(label="Your name", placeholder="e.g. jay.dolai")
                            msg_text   = gr.Textbox(label="Message",
                                                    placeholder="Type your reply...", lines=5)
                            send_btn   = gr.Button("Send message", variant="primary")

                action_result = gr.Markdown("", elem_classes=["fb"])

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

            with gr.Tab("New Ticket"):
                gr.Markdown("Raise a new support request. Fields marked * are required.",
                            elem_classes=["hint"])

                with gr.Group(elem_classes=["pnl"]):
                    gr.Markdown("Ticket information", elem_classes=["ph"])
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
                create_result = gr.Markdown("", elem_classes=["fb"])

                create_btn.click(fn=on_create_ticket,
                    inputs=[new_title, new_priority, new_category, new_created_by],
                    outputs=[create_result, ticket_table, stats_html])

    gr.HTML("""
    <div class="ft">
      Support Ticketing System · Powered by Databricks Lakebase · Built with Gradio · Bootcamp Day 1 · 2026
    </div>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT, show_error=True)
