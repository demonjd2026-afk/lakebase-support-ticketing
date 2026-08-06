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


def load_detail_html(t):
    """Render ticket details as clean HTML instead of disabled textboxes."""
    if not t:
        return '<div class="td-empty">Enter a ticket ID above and click Load ticket.</div>'
    st  = t["status"]
    pr  = t["priority"]
    return f"""
    <div class="td">
      <div class="td-title-row">
        <div class="td-title">#{t['ticket_id']} — {t['title']}</div>
        <span class="chip chip-{st}">{STATUS_BADGE.get(st, st)}</span>
      </div>
      <div class="td-grid">
        <div class="td-f"><div class="td-k">Priority</div>
          <div class="td-v"><span class="chip chip-p-{pr}">{PRIORITY_BADGE.get(pr, pr)}</span></div></div>
        <div class="td-f"><div class="td-k">Category</div>
          <div class="td-v">{t.get('category') or 'general'}</div></div>
        <div class="td-f"><div class="td-k">Created by</div>
          <div class="td-v">{t['created_by']}</div></div>
        <div class="td-f"><div class="td-k">Created at</div>
          <div class="td-v">{fmt_time(t['created_at'])}</div></div>
      </div>
    </div>
    """


def on_ticket_select(tid):
    if not tid:
        return load_detail_html(None), "_Enter a ticket ID above and click Load ticket._"
    try:
        t = get_ticket_by_id(int(tid))
        if not t:
            return '<div class="td-empty">Ticket not found.</div>', ""
        return load_detail_html(t), load_messages(int(tid))
    except Exception as e:
        return f'<div class="td-empty">Error: {e}</div>', ""


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
    if not tid: return "⚠️ No ticket loaded", load_detail_html(None), load_stats_html()
    try:
        update_status(int(tid), new_status)
        t = get_ticket_by_id(int(tid))
        return f"✅ Status updated to {new_status}", load_detail_html(t), load_stats_html()
    except Exception as e:
        return f"❌ {e}", load_detail_html(None), load_stats_html()


def on_delete_ticket(tid, confirmed):
    if not tid:       return "⚠️ No ticket loaded", load_ticket_table(), load_stats_html()
    if not confirmed: return "⚠️ Tick the confirmation box first", load_ticket_table(), load_stats_html()
    try:
        delete_ticket(int(tid))
        return f"✅ Ticket #{int(tid)} deleted", load_ticket_table(), load_stats_html()
    except Exception as e:
        return f"❌ {e}", load_ticket_table(), load_stats_html()


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ════════ RESET & BASE ════════ */
* { color-scheme: light !important; }
body { background: #eef1f6 !important; }
.gradio-container {
    max-width: 1340px !important; margin: 0 auto !important;
    padding: 0 24px 28px 24px !important;
    background: #eef1f6 !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
}
footer { display: none !important; }

/* Kill Gradio's dark backgrounds ONLY on layout wrappers */
.gradio-container .gap, .gradio-container .styler,
.gradio-container .row, .gradio-container .column,
.gradio-container .contain, .gradio-container .wrap:not(.msg) {
    background: transparent !important;
}
.gradio-container .block { background: transparent !important; border: none !important; box-shadow: none !important; }
.gradio-container .form  { background: transparent !important; border: none !important; box-shadow: none !important; }
.gradio-container .padded { background: transparent !important; }

/* ════════ TYPOGRAPHY ════════ */
.gradio-container, .gradio-container p, .gradio-container span,
.gradio-container div, .gradio-container td, .gradio-container th,
.gradio-container li, .gradio-container label {
    font-family: 'Inter', -apple-system, sans-serif !important;
    color: #334155;
}

/* ════════ TOP BAR ════════ */
.topbar {
    background: #ffffff !important; border-bottom: 1px solid #e2e8f0 !important;
    padding: 15px 24px; margin: 0 -24px 20px -24px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}
.tb-l { display: flex; align-items: center; gap: 12px; }
.tb-i { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff !important;
        display: flex; align-items: center; justify-content: center; font-size: 18px; }
.tb-t { font-size: 16px !important; font-weight: 700 !important; color: #0f172a !important; }
.tb-s { font-size: 12px !important; color: #94a3b8 !important; margin-top: 1px; }
.tb-b { background: #eef2ff !important; color: #4f46e5 !important; border: 1px solid #e0e7ff !important;
        padding: 5px 12px; border-radius: 7px; font-size: 11px !important; font-weight: 600 !important; }
.tb-m { font-size: 11px !important; color: #94a3b8 !important; margin-top: 5px; text-align: right; }

/* ════════ SIDEBAR ════════ */
.sb { background: #ffffff !important; border: 1px solid #e2e8f0 !important;
      border-radius: 14px; padding: 18px 15px; position: sticky; top: 14px;
      box-shadow: 0 1px 4px rgba(15,23,42,0.06); }
.sb-h { font-size: 11px !important; font-weight: 700 !important; color: #475569 !important;
        text-transform: uppercase; letter-spacing: 0.08em;
        padding-bottom: 11px; margin-bottom: 13px; border-bottom: 1px solid #f1f5f9 !important; }
.sb-c { display: block; padding: 12px 14px; margin-bottom: 8px; border-radius: 10px;
        background: #f8fafc !important; border-left: 3px solid #94a3b8; }
.sb-o { border-left-color: #f59e0b !important; background: #fffbeb !important; }
.sb-p { border-left-color: #3b82f6 !important; background: #eff6ff !important; }
.sb-r { border-left-color: #10b981 !important; background: #ecfdf5 !important; }
.sb-n { display: block; font-size: 24px !important; font-weight: 800 !important;
        color: #0f172a !important; line-height: 1.1; }
.sb-l { display: block; font-size: 11.5px !important; color: #64748b !important;
        margin-top: 3px; font-weight: 500 !important; }
.sb-f { margin-top: 15px; padding-top: 13px; border-top: 1px solid #f1f5f9 !important; }
.sb-fk { font-size: 9.5px !important; color: #94a3b8 !important; text-transform: uppercase;
         letter-spacing: 0.08em; font-weight: 700 !important; }
.sb-fv { font-size: 12.5px !important; color: #334155 !important; font-weight: 600 !important; margin-top: 4px; }
.sb-fs { font-size: 10.5px !important; color: #94a3b8 !important; margin-top: 2px; }
.sb-e  { color: #dc2626 !important; font-size: 11px !important; }

/* ════════ TABS ════════ */
.tab-nav { border-bottom: 1px solid #dbe1ea !important; margin-bottom: 18px !important;
           gap: 6px !important; background: transparent !important; }
.tab-nav button {
    background: transparent !important; color: #64748b !important;
    border: 1px solid transparent !important; border-bottom: none !important;
    border-radius: 10px 10px 0 0 !important; font-size: 13.5px !important;
    font-weight: 600 !important; padding: 11px 22px !important;
    margin-bottom: -1px !important; transition: all 0.15s ease !important;
}
.tab-nav button:hover { background: #e0e7ff !important; color: #4f46e5 !important; }
.tab-nav button.selected {
    background: #ffffff !important; color: #4f46e5 !important;
    border-color: #dbe1ea !important; border-bottom: 1px solid #ffffff !important;
    box-shadow: 0 -2px 4px rgba(15,23,42,0.03) !important;
}

/* ════════ PANELS ════════ */
.pnl {
    background: #ffffff !important; border: 1px solid #e2e8f0 !important;
    border-radius: 14px !important; padding: 20px !important;
    margin-bottom: 14px !important; box-shadow: 0 1px 4px rgba(15,23,42,0.05) !important;
}
.pnl-d {
    background: #fff5f5 !important; border: 1px solid #fecaca !important;
    border-radius: 14px !important; padding: 18px !important; margin-top: 12px !important;
}
/* Panels keep their own children transparent so panel bg shows */
.pnl .block, .pnl .form, .pnl .gap, .pnl .row, .pnl .column, .pnl .styler,
.pnl-d .block, .pnl-d .form, .pnl-d .gap, .pnl-d .row, .pnl-d .column, .pnl-d .styler {
    background: transparent !important; border: none !important; box-shadow: none !important;
}
.ph { font-size: 11.5px !important; font-weight: 700 !important; color: #475569 !important;
      text-transform: uppercase !important; letter-spacing: 0.08em !important;
      margin: 0 0 14px 0 !important; padding-bottom: 10px !important;
      border-bottom: 1px solid #f1f5f9 !important; background: transparent !important; }
.ph * { color: #475569 !important; background: transparent !important;
        font-size: 11.5px !important; font-weight: 700 !important;
        text-transform: uppercase !important; letter-spacing: 0.08em !important; }
.hint { font-size: 13px !important; color: #64748b !important;
        background: transparent !important; margin: 2px 0 16px 0 !important; }
.hint * { color: #64748b !important; background: transparent !important; font-size: 13px !important; }

/* ════════ LABELS — dark, clean, no bg ════════ */
.gradio-container label,
.gradio-container label > span,
.gradio-container [data-testid="block-label"] {
    background: transparent !important; background-color: transparent !important;
    color: #1e293b !important; font-size: 13px !important;
    font-weight: 600 !important; border: none !important;
    box-shadow: none !important; padding: 0 0 6px 0 !important;
    position: static !important;
}

/* ════════ TEXT INPUTS ════════ */
.gradio-container textarea,
.gradio-container input[type="text"],
.gradio-container input[type="number"] {
    background: #ffffff !important; border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important; color: #0f172a !important;
    font-size: 13.5px !important; padding: 11px 13px !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.03) !important;
}
.gradio-container textarea:focus,
.gradio-container input:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.13) !important; outline: none !important;
}
.gradio-container input::placeholder,
.gradio-container textarea::placeholder { color: #94a3b8 !important; opacity: 1 !important; }

/* ════════ DROPDOWNS — visible value + floating menu ════════ */
.gradio-container .secondary-wrap input,
.gradio-container [data-testid="dropdown"] input {
    background: #ffffff !important; border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important;
    color: #0f172a !important; -webkit-text-fill-color: #0f172a !important;
    font-size: 13.5px !important; font-weight: 500 !important;
    padding: 11px 13px !important; cursor: pointer !important;
    opacity: 1 !important;
}
/* The options list floats above everything */
.gradio-container ul.options {
    background: #ffffff !important; border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    box-shadow: 0 12px 32px rgba(15,23,42,0.18) !important;
    z-index: 999999 !important;
    max-height: 230px !important; overflow-y: auto !important;
    padding: 6px !important;
}
.gradio-container ul.options li {
    background: #ffffff !important; color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
    font-size: 13.5px !important; font-weight: 500 !important;
    padding: 10px 13px !important; border-radius: 7px !important;
    cursor: pointer !important; list-style: none !important;
    display: flex !important; align-items: center !important;
}
.gradio-container ul.options li:hover {
    background: #eef2ff !important; color: #4f46e5 !important;
    -webkit-text-fill-color: #4f46e5 !important;
}
.gradio-container ul.options li.selected {
    background: #e0e7ff !important; color: #4f46e5 !important;
    -webkit-text-fill-color: #4f46e5 !important; font-weight: 600 !important;
}

/* ════════ BUTTONS — always visible ════════ */
.gradio-container button.primary,
.gradio-container button[variant="primary"] {
    background: #4f46e5 !important; background-color: #4f46e5 !important;
    color: #ffffff !important; border: none !important;
    border-radius: 9px !important; font-size: 13.5px !important; font-weight: 600 !important;
    height: 44px !important; min-height: 44px !important; padding: 0 22px !important;
    box-shadow: 0 1px 3px rgba(79,70,229,0.3) !important;
    transition: all 0.15s !important; cursor: pointer !important;
}
.gradio-container button.primary:hover { background: #4338ca !important; }
.gradio-container button.primary *,
.gradio-container button.primary span {
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    background: transparent !important;
}

.gradio-container button.secondary {
    background: #ffffff !important; background-color: #ffffff !important;
    color: #334155 !important; border: 1px solid #cbd5e1 !important;
    border-radius: 9px !important; font-size: 13.5px !important; font-weight: 600 !important;
    height: 44px !important; min-height: 44px !important; padding: 0 22px !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.05) !important; cursor: pointer !important;
}
.gradio-container button.secondary:hover { background: #f8fafc !important; border-color: #94a3b8 !important; }
.gradio-container button.secondary *,
.gradio-container button.secondary span {
    color: #334155 !important; -webkit-text-fill-color: #334155 !important;
    background: transparent !important;
}

.gradio-container button.stop {
    background: #dc2626 !important; background-color: #dc2626 !important;
    color: #ffffff !important; border: none !important;
    border-radius: 9px !important; font-size: 13.5px !important; font-weight: 600 !important;
    height: 44px !important; min-height: 44px !important; padding: 0 22px !important;
    box-shadow: 0 1px 3px rgba(220,38,38,0.3) !important; cursor: pointer !important;
}
.gradio-container button.stop:hover { background: #b91c1c !important; }
.gradio-container button.stop *,
.gradio-container button.stop span {
    color: #ffffff !important; -webkit-text-fill-color: #ffffff !important;
    background: transparent !important;
}

/* ════════ EQUAL ROW ════════ */

/* ════════ TABLE ════════ */
.gradio-container table {
    border-collapse: collapse !important; width: 100% !important;
    background: #ffffff !important; border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important; overflow: hidden !important;
}
.gradio-container table thead th {
    background: #f1f5f9 !important; color: #475569 !important;
    font-size: 11px !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.05em !important;
    padding: 13px 15px !important;
    border-bottom: 2px solid #cbd5e1 !important;
    border-right: 1px solid #e2e8f0 !important;
}
.gradio-container table tbody td {
    background: #ffffff !important; color: #334155 !important;
    font-size: 13px !important; padding: 12px 15px !important;
    border-bottom: 1px solid #e8edf3 !important;
    border-right: 1px solid #f1f5f9 !important;
}
.gradio-container table tbody tr:nth-child(even) td { background: #f8fafc !important; }
.gradio-container table tbody tr:hover td { background: #eef2ff !important; }

/* ════════ TABLE — scrollable container ════════ */
.gradio-container [data-testid="dataframe"] {
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    overflow: hidden !important;
}

/* The scroll viewport — tall enough for ~5 rows, scrolls beyond */
.gradio-container [data-testid="dataframe"] .table-wrap,
.gradio-container [data-testid="dataframe"] [class*="table-wrap"],
.gradio-container [data-testid="dataframe"] .wrap > div {
    max-height: 600px !important;
    overflow-y: auto !important;
    overflow-x: auto !important;
    scrollbar-width: thin !important;
    scrollbar-color: #94a3b8 #f1f5f9 !important;
}

/* Always-visible scrollbars */
.gradio-container [data-testid="dataframe"] .table-wrap::-webkit-scrollbar {
    width: 11px !important; height: 11px !important;
    -webkit-appearance: none !important;
}
.gradio-container [data-testid="dataframe"] .table-wrap::-webkit-scrollbar-track {
    background: #f1f5f9 !important;
}
.gradio-container [data-testid="dataframe"] .table-wrap::-webkit-scrollbar-thumb {
    background: #94a3b8 !important; border-radius: 6px !important;
    border: 2px solid #f1f5f9 !important;
}
.gradio-container [data-testid="dataframe"] .table-wrap::-webkit-scrollbar-thumb:hover {
    background: #64748b !important;
}

/* Sticky header while scrolling */
.gradio-container [data-testid="dataframe"] thead th {
    position: sticky !important; top: 0 !important; z-index: 5 !important;
    background: #f1f5f9 !important;
}

/* Table body: no border override, no min-width forcing */
.gradio-container [data-testid="dataframe"] table {
    border: none !important;
    width: 100% !important;
}

/* ════════ TICKET DETAILS ════════ */
.td { padding: 2px 0; }
.td-title-row { display: flex; align-items: center; justify-content: space-between;
                gap: 12px; padding-bottom: 14px; margin-bottom: 14px;
                border-bottom: 1px solid #f1f5f9; }
.td-title { font-size: 15.5px !important; font-weight: 700 !important; color: #0f172a !important; }
.td-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
.td-k { font-size: 10.5px !important; font-weight: 700 !important; color: #475569 !important;
        text-transform: uppercase; letter-spacing: 0.07em; margin-bottom: 6px; }
.td-v { font-size: 13.5px !important; color: #334155 !important; font-weight: 500 !important; }
.td-empty { font-size: 13px !important; color: #94a3b8 !important;
            font-style: italic; padding: 14px 0; }

/* ════════ CHIPS ════════ */
.chip { display: inline-block; padding: 5px 12px; border-radius: 20px;
        font-size: 11.5px !important; font-weight: 600 !important; white-space: nowrap; }
.chip-open        { background: #fef3c7 !important; color: #92400e !important; }
.chip-in_progress { background: #dbeafe !important; color: #1e40af !important; }
.chip-resolved    { background: #d1fae5 !important; color: #065f46 !important; }
.chip-p-high   { background: #fee2e2 !important; color: #991b1b !important; }
.chip-p-medium { background: #ffedd5 !important; color: #9a3412 !important; }
.chip-p-low    { background: #d1fae5 !important; color: #065f46 !important; }

/* ════════ MESSAGE THREAD ════════ */
.msg { background: #f8fafc !important; border: 1px solid #e2e8f0 !important;
       border-radius: 11px; padding: 17px 19px; min-height: 80px;
       font-size: 13px !important; line-height: 1.7; max-height: 310px;
       overflow-y: auto; color: #475569 !important; }
.msg * { background: transparent !important; }
.msg strong { color: #0f172a !important; font-weight: 600 !important; }
.msg code { background: #eef2ff !important; padding: 2px 8px; border-radius: 5px;
            font-size: 11px !important; color: #4f46e5 !important; }
.msg hr { border: none; border-top: 1px solid #e2e8f0; margin: 13px 0; }
.msg p, .msg span, .msg div { color: #475569 !important; font-size: 13px !important; }

/* ════════ CHECKBOX ════════ */
.gradio-container input[type="checkbox"] {
    accent-color: #4f46e5 !important; width: 17px !important; height: 17px !important;
    cursor: pointer !important;
}
.gradio-container label:has(input[type="checkbox"]) {
    display: inline-flex !important; align-items: center !important;
    gap: 9px !important; color: #334155 !important;
    font-weight: 500 !important; font-size: 13px !important;
    cursor: pointer !important;
}

/* ════════ FEEDBACK ════════ */
.fb { font-size: 13px !important; padding: 8px 0 !important; min-height: 26px !important; }
.fb * { color: #334155 !important; font-weight: 500 !important;
        font-size: 13px !important; background: transparent !important; }

/* ════════ FOOTER ════════ */
.ft { text-align: center; padding: 16px; border-top: 1px solid #e2e8f0; margin-top: 22px; }
.ft, .ft * { color: #94a3b8 !important; font-size: 11.5px !important; background: transparent !important; }

/* ════════ MICRO-INTERACTIONS ════════ */
.gradio-container button.primary:active,
.gradio-container button.secondary:active,
.gradio-container button.stop:active { transform: scale(0.985) !important; }

/* Number input spinners subtle */
input[type=number]::-webkit-inner-spin-button { opacity: 0.4; }

/* Selection color */
::selection { background: #e0e7ff; color: #4338ca; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 4px; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

/* ════════ REFRESH BUTTON LOADING SWEEP (scoped strictly) ════════ */
#refresh-btn button.sweeping::after {
    content: "" !important;
    position: absolute !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important; height: 100% !important;
    background: linear-gradient(
        100deg,
        rgba(255,255,255,0)    0%,
        rgba(255,255,255,0)   35%,
        rgba(255,255,255,0.6) 50%,
        rgba(255,255,255,0)   65%,
        rgba(255,255,255,0)  100%
    ) !important;
    background-size: 200% 100% !important;
    background-repeat: no-repeat !important;
    animation: btnSweep 1s linear infinite !important;
    pointer-events: none !important;
    border-radius: 9px !important;
}

@keyframes btnSweep {
    0%   { background-position: -100% 0; }
    100% { background-position:  200% 0; }
}
}

/* ════════ FILTER ROW — align dropdown and Refresh button ════════ */
.eq-row { align-items: stretch !important; gap: 14px !important; }
.eq-row > * { margin-bottom: 0 !important; }

/* Both action buttons: align vertically centered against the input beside them.
   Neighbor column = label (~28px) + bordered container (~86px). Input center ≈ 71px.
   Button 46px → top offset = 71 - 23 = 48px. */
#refresh-btn, #load-btn {
    display: flex !important;
    align-items: flex-start !important;
    padding-top: 48px !important;
    margin: 0 !important;
}
#refresh-btn button, #load-btn button {
    width: 100% !important;
    height: 46px !important;
    min-height: 46px !important;
    max-height: 46px !important;
    padding: 0 !important;
    margin: 0 !important;
    border-radius: 9px !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    overflow: hidden !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
    text-align: center !important;
}
#refresh-btn button > *, #load-btn button > * {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
    text-align: center !important;
}
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
                with gr.Row(equal_height=True, elem_classes=["eq-row"]):
                    filter_dd   = gr.Dropdown(choices=FILTER_OPTIONS, value="All",
                                              label="Filter by status", scale=4)
                    refresh_btn = gr.Button("Refresh", variant="primary", scale=1,
                                            elem_id="refresh-btn")

                ticket_table = gr.Dataframe(
                    headers=["ID", "Title", "Status", "Priority", "Category",
                             "Created by", "Created at", "Msgs"],
                    datatype=["number", "str", "str", "str", "str", "str", "str", "number"],
                    value=load_ticket_table(), interactive=False, wrap=True)

                filter_dd.change(fn=on_filter_change, inputs=filter_dd, outputs=ticket_table)
                refresh_btn.click(fn=lambda f: load_ticket_table(f),
                                  inputs=filter_dd, outputs=ticket_table)

            with gr.Tab("View & Update"):
                gr.Markdown("Load a ticket by ID to see its details, history, and take action.",
                            elem_classes=["hint"])

                with gr.Row(equal_height=True, elem_classes=["eq-row"]):
                    ticket_id_input = gr.Number(label="Ticket ID", precision=0, scale=4)
                    load_btn = gr.Button("Load ticket", variant="primary", scale=1,
                                         elem_id="load-btn")

                with gr.Group(elem_classes=["pnl"]):
                    gr.Markdown("Ticket details", elem_classes=["ph"])
                    detail_html = gr.HTML(load_detail_html(None))

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
                    outputs=[detail_html, message_thread])
                update_status_btn.click(fn=on_update_status,
                    inputs=[ticket_id_input, new_status_dd],
                    outputs=[action_result, detail_html, stats_html])
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
    <script>
    (function() {
        document.addEventListener('click', function(e) {
            var wrap = e.target.closest('#refresh-btn');
            if (!wrap) return;
            var btn = wrap.tagName === 'BUTTON' ? wrap : wrap.querySelector('button');
            if (!btn) return;
            btn.classList.add('sweeping');
            setTimeout(function() { btn.classList.remove('sweeping'); }, 900);
        }, true);
    })();
    </script>
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=PORT, show_error=True)
