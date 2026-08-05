-- =============================================================
-- 02_seed_data.sql
-- Lakebase Support Ticketing System — Sample Data
-- At least 3 tickets, 3 statuses, 2+ messages per ticket
-- =============================================================

-- ─────────────────────────────────────────
-- TICKETS  (3 tickets, 3 different statuses)
-- ─────────────────────────────────────────
INSERT INTO tickets (title, status, priority, category, created_by, created_at) VALUES
(
    'Databricks cluster auto-terminates during pipeline run',
    'open',
    'high',
    'infra',
    'jay.dolai',
    NOW() - INTERVAL '3 days'
),
(
    'Unable to access Unity Catalog schema after permission update',
    'in_progress',
    'high',
    'access',
    'priya.sharma',
    NOW() - INTERVAL '2 days'
),
(
    'Delta table OPTIMIZE job taking longer than expected',
    'resolved',
    'medium',
    'data',
    'ravi.kumar',
    NOW() - INTERVAL '5 days'
),
(
    'Lakebase connection string not recognized in Databricks App',
    'open',
    'medium',
    'infra',
    'jay.dolai',
    NOW() - INTERVAL '1 day'
);

-- ─────────────────────────────────────────
-- MESSAGES  (2+ messages per ticket)
-- ─────────────────────────────────────────

-- Ticket 1: cluster auto-terminates
INSERT INTO ticket_messages (ticket_id, message_text, author, created_at) VALUES
(
    1,
    'The cluster keeps shutting down at the 2-hour mark even though auto-termination is set to 240 minutes. This is breaking our daily ingestion pipeline.',
    'jay.dolai',
    NOW() - INTERVAL '3 days'
),
(
    1,
    'Checked the cluster event log — looks like a spot instance preemption. Try switching the worker node type to on-demand for this job cluster.',
    'support.bot',
    NOW() - INTERVAL '2 days' - INTERVAL '18 hours'
),
(
    1,
    'Switched to on-demand workers as suggested. Will monitor tonight''s run and update the ticket tomorrow.',
    'jay.dolai',
    NOW() - INTERVAL '2 days'
);

-- Ticket 2: Unity Catalog access
INSERT INTO ticket_messages (ticket_id, message_text, author, created_at) VALUES
(
    2,
    'After our admin ran an access policy update yesterday, I can no longer query the gold.sales_summary table. Getting: PERMISSION_DENIED: User does not have SELECT privilege.',
    'priya.sharma',
    NOW() - INTERVAL '2 days'
),
(
    2,
    'Confirmed the issue. The policy update accidentally revoked the data_reader group privilege on the gold schema. We are working on a fix — estimated 2 hours.',
    'admin.team',
    NOW() - INTERVAL '2 days' + INTERVAL '3 hours'
),
(
    2,
    'Partial fix applied — you should now have read access. Could you test and confirm? We are still auditing other affected schemas.',
    'admin.team',
    NOW() - INTERVAL '1 day'
);

-- Ticket 3: OPTIMIZE job slow (resolved)
INSERT INTO ticket_messages (ticket_id, message_text, author, created_at) VALUES
(
    3,
    'Our weekly OPTIMIZE + ZORDER job on the events Delta table (800 GB) is taking 6+ hours. It used to finish in 90 minutes before we migrated to the new cluster policy.',
    'ravi.kumar',
    NOW() - INTERVAL '5 days'
),
(
    3,
    'The new cluster policy caps workers at 4 nodes. Your previous runs used 12. Recommend requesting an exception for this job or splitting OPTIMIZE into smaller partition ranges.',
    'support.bot',
    NOW() - INTERVAL '4 days'
),
(
    3,
    'Switched to partition-range OPTIMIZE (by month). Job now completes in 95 minutes. Marking as resolved — thanks!',
    'ravi.kumar',
    NOW() - INTERVAL '3 days'
);

-- Ticket 4: Lakebase connection string
INSERT INTO ticket_messages (ticket_id, message_text, author, created_at) VALUES
(
    4,
    'When I set LAKEBASE_CONN as an environment variable in Databricks Apps and try psycopg2.connect(os.environ["LAKEBASE_CONN"]), I get: connection refused on port 5432.',
    'jay.dolai',
    NOW() - INTERVAL '1 day'
),
(
    4,
    'Make sure you are using the internal Lakebase hostname (not the external one) and that the App is in the same Databricks workspace region. Also confirm port 5432 is not blocked by your workspace network policy.',
    'support.bot',
    NOW() - INTERVAL '20 hours'
);

-- ─────────────────────────────────────────
-- VERIFY
-- ─────────────────────────────────────────
SELECT t.ticket_id, t.title, t.status, t.priority, COUNT(m.message_id) AS message_count
FROM tickets t
LEFT JOIN ticket_messages m ON t.ticket_id = m.ticket_id
GROUP BY t.ticket_id, t.title, t.status, t.priority
ORDER BY t.ticket_id;
