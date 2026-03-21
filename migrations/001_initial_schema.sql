-- SnapGather Database Migration
-- Run this in your Supabase SQL editor or psql client
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Organizers ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS organizers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Events ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organizer_id        UUID NOT NULL REFERENCES organizers(id) ON DELETE CASCADE,
    event_name          VARCHAR(255) NOT NULL,
    event_start_time    TIMESTAMPTZ NOT NULL,
    event_end_time      TIMESTAMPTZ NOT NULL,
    upload_deadline     TIMESTAMPTZ NOT NULL,  -- computed as event_end_time + 36h in app layer
    qr_code_url         TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_event_times CHECK (event_end_time > event_start_time)
);

CREATE INDEX IF NOT EXISTS idx_events_organizer ON events(organizer_id);

-- ─── Photos ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS photos (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id            UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    guest_name          VARCHAR(255) NOT NULL,
    device_fingerprint  VARCHAR(255) NOT NULL,
    file_url            TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'approved', 'rejected')),
    uploaded_at         TIMESTAMPTZ DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ,
    file_size_bytes     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_photos_event_status  ON photos(event_id, status);
CREATE INDEX IF NOT EXISTS idx_photos_device_event  ON photos(device_fingerprint, event_id);
CREATE INDEX IF NOT EXISTS idx_photos_uploaded_at   ON photos(uploaded_at DESC);

-- ─── Guest Sessions ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS guest_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id            UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    device_fingerprint  VARCHAR(255) NOT NULL,
    guest_name          VARCHAR(255) NOT NULL,
    photo_count         INTEGER NOT NULL DEFAULT 0 CHECK (photo_count >= 0),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(event_id, device_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_sessions_event ON guest_sessions(event_id);

-- ─── Updated-at trigger ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_organizers_updated_at ON organizers;
CREATE TRIGGER trg_organizers_updated_at
    BEFORE UPDATE ON organizers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_events_updated_at ON events;
CREATE TRIGGER trg_events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ─── Row Level Security ───────────────────────────────────────────────────────
ALTER TABLE organizers      ENABLE ROW LEVEL SECURITY;
ALTER TABLE events          ENABLE ROW LEVEL SECURITY;
ALTER TABLE photos          ENABLE ROW LEVEL SECURITY;
ALTER TABLE guest_sessions  ENABLE ROW LEVEL SECURITY;

-- Backend uses service_role key (bypasses RLS), so these policies protect
-- against accidental direct client access.

-- Block all direct anon/user access — backend service_role key bypasses RLS.
CREATE POLICY "deny_anon_organizers"     ON organizers     FOR ALL TO anon USING (false);
CREATE POLICY "deny_anon_events"         ON events         FOR ALL TO anon USING (false);
CREATE POLICY "deny_anon_photos"         ON photos         FOR ALL TO anon USING (false);
CREATE POLICY "deny_anon_sessions"       ON guest_sessions FOR ALL TO anon USING (false);

-- ─── Storage Buckets ──────────────────────────────────────────────────────────
-- Run these via Supabase Dashboard > Storage, or via the management API.
-- Bucket: event-photos (private)
-- Bucket: qr-codes     (public)
--
-- INSERT INTO storage.buckets (id, name, public) VALUES ('event-photos', 'event-photos', false);
-- INSERT INTO storage.buckets (id, name, public) VALUES ('qr-codes',     'qr-codes',     true);
