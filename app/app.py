# =============================================================
# app.py — Lakebase Support Ticketing System
# Streamlit UI — Phase 3
#
# Run locally:
#   export LAKEBASE_CONN="postgresql://token:<PAT>@dbc-291b687e-da89.cloud.databricks.com:5432/databricks_postgres"
#   streamlit run app.py
#
# Deployed via Databricks Apps:
#   LAKEBASE_CONN set as environment variable in App config
# =============================================================

import streamlit as st
import pandas as pd
from datetime import datetime
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

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────

st.set_page_config(
    page_title="Support Ticketing System",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────

st.markdown("""
<style>
    /* Status badges */
    .badge-open        { background:#fff3cd; color:#856404; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
    .badge-in_progress { background:#cce5ff; color:#004085; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }
    .badge-resolved    { background:#d4edda; color:#155724; padding:3px 10px; border-radius:12px; font-size:12px; font-weight:600; }

    /* Priority badges */
    .priority-high   { background:#f8d7da; color:#721c24; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
    .priority-medium { background:#fff3cd; color:#856404; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }
    .priority-low    { background:#d4edda; color:#155724; padding:2px 8px; border-radius:10px; font-size:11px; font-weight:600; }

    /* Message bubbles */
    .msg-bubble {
        background: #f8f9fa;
        border-left: 4px solid #0d6efd;
        padding: 10px 14px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
    }
    .msg-author { font-weight: 600; font-size: 13px; color: #0d6efd; }
    .msg-time   { font-size: 11px; color: #6c757d; margin-left: 8px; }
    .msg-text   { margin-top: 4px; font-size: 14px; }

    /* Ticket card */
    .ticket-header {
        background: linear-gradient(90deg, #0d6efd11, #ffffff00);
        border-left: 5px solid #0d6efd;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 16px;
    }

    /* Section divider */
    .section-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #6c757d;
        margin: 16px 0 8px 0;
    }

    /* Stat cards */
    div[data-testid="metric-container"] {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 8px;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────

if "selected_ticket_id" not in st.session_state:
    st.session_state.selected_ticket_id = None
if "view" not in st.session_state:
    st.session_state.view = "list"          # list | detail | create
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False
if "status_filter" not in st.session_state:
    st.session_state.status_filter = "All"


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

STATUS_OPTIONS  = ["open", "in_progress", "resolved"]
PRIORITY_OPTIONS = ["low", "medium", "high"]
FILTER_OPTIONS  = ["All", "open", "in_progress", "resolved"]

STATUS_LABELS = {
    "open":        "🟡 Open",
    "in_progress": "🔵 In Progress",
    "resolved":    "🟢 Resolved",
}

PRIORITY_LABELS = {
    "high":   "🔴 High",
    "medium": "🟠 Medium",
    "low":    "🟢 Low",
}

def badge_html(status):
    label = status.replace("_", " ").title()
    return f'<span class="badge-{status}">{label}</span>'

def priority_html(priority):
    return f'<span class="priority-{priority}">{priority.title()}</span>'

def fmt_time(ts):
    if ts is None:
        return ""
    if hasattr(ts, "strftime"):
        return ts.strftime("%d %b %Y, %H:%M")
    return str(ts)

def go_list():
    st.session_state.view = "list"
    st.session_state.selected_ticket_id = None
    st.session_state.confirm_delete = False

def go_detail(ticket_id):
    st.session_state.view = "detail"
    st.session_state.selected_ticket_id = ticket_id
    st.session_state.confirm_delete = False

def go_create():
    st.session_state.view = "create"
    st.session_state.confirm_delete = False


# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────

with st.sidebar:
    st.title("🎫 Support Tickets")
    st.divider()

    # Stats panel
    try:
        stats = get_stats()
        st.markdown('<p class="section-label">📊 Overview</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        col1.metric("Total",       stats.get("total", 0))
        col2.metric("🟡 Open",     stats.get("open", 0))
        col3, col4 = st.columns(2)
        col3.metric("🔵 In Progress", stats.get("in_progress", 0))
        col4.metric("🟢 Resolved",    stats.get("resolved", 0))
    except Exception as e:
        st.error(f"Could not load stats: {e}")

    st.divider()

    # Status filter
    st.markdown('<p class="section-label">🔍 Filter by status</p>', unsafe_allow_html=True)
    selected_filter = st.selectbox(
        label="Status filter",
        options=FILTER_OPTIONS,
        index=FILTER_OPTIONS.index(st.session_state.status_filter),
        label_visibility="collapsed",
    )
    st.session_state.status_filter = selected_filter

    st.divider()

    # Navigation buttons
    if st.button("➕ New Ticket", use_container_width=True, type="primary"):
        go_create()

    if st.session_state.view != "list":
        if st.button("← Back to Ticket List", use_container_width=True):
            go_list()

    st.divider()
    st.caption("Powered by Databricks Lakebase")
    st.caption("Databricks Bootcamp · Day 1 · 2026")


# ─────────────────────────────────────────
# MAIN PANEL — TICKET LIST
# ─────────────────────────────────────────

def render_ticket_list():
    st.title("🎫 Support Ticket Dashboard")

    try:
        tickets = get_all_tickets(
            status_filter=st.session_state.status_filter
            if st.session_state.status_filter != "All" else None
        )
    except Exception as e:
        st.error(f"❌ Could not load tickets from Lakebase: {e}")
        return

    if not tickets:
        st.info("No tickets found. Create one using '➕ New Ticket' in the sidebar.")
        return

    # Summary line
    filter_label = (
        f"showing **{st.session_state.status_filter}** tickets"
        if st.session_state.status_filter != "All"
        else "showing **all** tickets"
    )
    st.markdown(f"**{len(tickets)} ticket(s)** — {filter_label}")
    st.divider()

    # Ticket cards
    for t in tickets:
        with st.container():
            col_main, col_btn = st.columns([8, 1])
            with col_main:
                st.markdown(
                    f"**#{t['ticket_id']} — {t['title']}**  "
                    f"&nbsp;&nbsp;{badge_html(t['status'])}"
                    f"&nbsp;{priority_html(t['priority'])}",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"📁 {t.get('category') or 'general'} &nbsp;|&nbsp; "
                    f"👤 {t['created_by']} &nbsp;|&nbsp; "
                    f"🕐 {fmt_time(t['created_at'])} &nbsp;|&nbsp; "
                    f"💬 {t.get('message_count', 0)} message(s)"
                )
            with col_btn:
                if st.button("Open →", key=f"open_{t['ticket_id']}"):
                    go_detail(t['ticket_id'])
        st.divider()


# ─────────────────────────────────────────
# MAIN PANEL — TICKET DETAIL
# ─────────────────────────────────────────

def render_ticket_detail():
    ticket_id = st.session_state.selected_ticket_id

    try:
        ticket = get_ticket_by_id(ticket_id)
        messages = get_messages(ticket_id)
    except Exception as e:
        st.error(f"❌ Could not load ticket: {e}")
        return

    if not ticket:
        st.error("Ticket not found.")
        return

    # ── Header ──────────────────────────
    st.markdown(
        f'<div class="ticket-header">'
        f'<h2 style="margin:0">#{ticket["ticket_id"]} — {ticket["title"]}</h2>'
        f'<p style="margin:6px 0 0 0">'
        f'{badge_html(ticket["status"])} &nbsp; {priority_html(ticket["priority"])}'
        f'</p></div>',
        unsafe_allow_html=True,
    )

    # ── Metadata row ────────────────────
    meta1, meta2, meta3 = st.columns(3)
    meta1.markdown(f"**👤 Created by**  \n{ticket['created_by']}")
    meta2.markdown(f"**📁 Category**  \n{ticket.get('category') or 'general'}")
    meta3.markdown(f"**🕐 Created at**  \n{fmt_time(ticket['created_at'])}")

    st.divider()

    # ── Status update + Delete ──────────
    col_status, col_spacer, col_delete = st.columns([3, 4, 2])

    with col_status:
        st.markdown('<p class="section-label">Update status</p>', unsafe_allow_html=True)
        new_status = st.selectbox(
            "Status",
            options=STATUS_OPTIONS,
            index=STATUS_OPTIONS.index(ticket["status"]),
            label_visibility="collapsed",
            key="status_select",
        )
        if st.button("✅ Update Status", type="primary"):
            if new_status == ticket["status"]:
                st.warning("Status is already set to that value.")
            else:
                try:
                    update_status(ticket_id, new_status)
                    st.success(f"Status updated to **{new_status}**!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Update failed: {e}")

    with col_delete:
        st.markdown('<p class="section-label">Danger zone</p>', unsafe_allow_html=True)
        if not st.session_state.confirm_delete:
            if st.button("🗑️ Delete Ticket", type="secondary"):
                st.session_state.confirm_delete = True
                st.rerun()
        else:
            st.warning("Are you sure? This cannot be undone.")
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                if st.button("Yes, delete", type="primary"):
                    try:
                        delete_ticket(ticket_id)
                        st.success("Ticket deleted.")
                        go_list()
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Delete failed: {e}")
            with dcol2:
                if st.button("Cancel"):
                    st.session_state.confirm_delete = False
                    st.rerun()

    st.divider()

    # ── Message thread ───────────────────
    st.markdown('<p class="section-label">💬 Message thread</p>', unsafe_allow_html=True)

    if not messages:
        st.info("No messages yet. Add the first one below.")
    else:
        for msg in messages:
            st.markdown(
                f'<div class="msg-bubble">'
                f'<span class="msg-author">👤 {msg["author"]}</span>'
                f'<span class="msg-time">{fmt_time(msg["created_at"])}</span>'
                f'<div class="msg-text">{msg["message_text"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Add message ──────────────────────
    st.markdown('<p class="section-label">➕ Add a message</p>', unsafe_allow_html=True)

    with st.form("add_message_form", clear_on_submit=True):
        msg_author = st.text_input(
            "Your name",
            placeholder="e.g. jay.dolai",
            key="msg_author",
        )
        msg_text = st.text_area(
            "Message",
            placeholder="Type your message here...",
            height=100,
            key="msg_text",
        )
        submitted = st.form_submit_button("📨 Send Message", type="primary")

        if submitted:
            errors = []
            if not msg_author.strip():
                errors.append("Name is required.")
            if not msg_text.strip():
                errors.append("Message cannot be empty.")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                try:
                    add_message(ticket_id, msg_text, msg_author)
                    st.success("✅ Message sent!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Could not send message: {e}")


# ─────────────────────────────────────────
# MAIN PANEL — CREATE TICKET
# ─────────────────────────────────────────

def render_create_ticket():
    st.title("➕ Create New Ticket")
    st.markdown("Fill in the details below. Fields marked **\*** are required.")
    st.divider()

    with st.form("create_ticket_form", clear_on_submit=True):
        title = st.text_input(
            "Title *",
            placeholder="Short description of the issue",
            max_chars=200,
        )

        col1, col2 = st.columns(2)
        with col1:
            priority = st.selectbox(
                "Priority *",
                options=PRIORITY_OPTIONS,
                index=1,  # default: medium
            )
        with col2:
            category = st.text_input(
                "Category",
                placeholder="e.g. infra, access, data, billing",
            )

        created_by = st.text_input(
            "Your name / email *",
            placeholder="e.g. jay.dolai",
        )

        submitted = st.form_submit_button("🚀 Create Ticket", type="primary")

        if submitted:
            errors = []
            if not title.strip():
                errors.append("Title is required.")
            if not created_by.strip():
                errors.append("Name / email is required.")

            if errors:
                for err in errors:
                    st.error(f"❌ {err}")
            else:
                try:
                    new_id = create_ticket(
                        title=title,
                        created_by=created_by,
                        priority=priority,
                        category=category.strip() or None,
                    )
                    st.success(f"✅ Ticket #{new_id} created successfully!")
                    st.info("Opening ticket...")
                    go_detail(new_id)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Could not create ticket: {e}")

    st.divider()
    if st.button("← Cancel — back to ticket list"):
        go_list()
        st.rerun()


# ─────────────────────────────────────────
# ROUTER — render the right view
# ─────────────────────────────────────────

view = st.session_state.view

if view == "list":
    render_ticket_list()
elif view == "detail":
    render_ticket_detail()
elif view == "create":
    render_create_ticket()
else:
    render_ticket_list()
