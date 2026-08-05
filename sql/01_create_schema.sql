-- =============================================================
-- 01_create_schema.sql
-- Lakebase Support Ticketing System — Schema
-- Run this inside your Databricks notebook via psycopg2
-- =============================================================

-- Drop tables if re-running (safe for dev only)
DROP TABLE IF EXISTS ticket_messages;
DROP TABLE IF EXISTS tickets;

-- ─────────────────────────────────────────
-- TABLE: tickets
-- ─────────────────────────────────────────
CREATE TABLE tickets (
    ticket_id   SERIAL       PRIMARY KEY,
    title       TEXT         NOT NULL,
    status      TEXT         NOT NULL DEFAULT 'open',    -- open | in_progress | resolved
    priority    TEXT         NOT NULL DEFAULT 'medium',  -- low | medium | high
    category    TEXT,                                    -- e.g. infra, access, data, billing
    created_by  TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- TABLE: ticket_messages
-- ─────────────────────────────────────────
CREATE TABLE ticket_messages (
    message_id   SERIAL       PRIMARY KEY,
    ticket_id    INT          NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    message_text TEXT         NOT NULL,
    author       TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────
CREATE INDEX idx_messages_ticket_id ON ticket_messages(ticket_id);
CREATE INDEX idx_tickets_status     ON tickets(status);
CREATE INDEX idx_tickets_priority   ON tickets(priority);

-- Verify
SELECT 'tickets'         AS table_name, COUNT(*) AS row_count FROM tickets
UNION ALL
SELECT 'ticket_messages' AS table_name, COUNT(*) AS row_count FROM ticket_messages;
