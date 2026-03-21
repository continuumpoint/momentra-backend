-- Development seed data — DO NOT run in production
-- Assumes migration 001 has been applied

-- Sample organizer (password: "password123")
INSERT INTO organizers (id, email, password_hash) VALUES (
    '00000000-0000-0000-0000-000000000001',
    'demo@snapgather.dev',
    '$2b$12$KIX/4iBcm5xDPpBXm8mEpOlWBPzE7jV4eN5oLw/VmTAEqyeKHmMuG'
) ON CONFLICT DO NOTHING;

-- Sample event
INSERT INTO events (id, organizer_id, event_name, event_start_time, event_end_time) VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Demo Wedding 2025',
    NOW() - INTERVAL '2 hours',
    NOW() + INTERVAL '6 hours'
) ON CONFLICT DO NOTHING;
