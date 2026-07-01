-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration 005: Fix bug_reports table — add missing columns
-- The table was created from 001_initial_schema which has different columns
-- than what the session.py endpoint expects (from 003_feedback_bugs schema).
-- ═══════════════════════════════════════════════════════════════════════════════

-- Add missing columns that the API expects
ALTER TABLE bug_reports ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE bug_reports ADD COLUMN IF NOT EXISTS what_happened TEXT;
ALTER TABLE bug_reports ADD COLUMN IF NOT EXISTS session_id TEXT;
ALTER TABLE bug_reports ADD COLUMN IF NOT EXISTS location_code TEXT;
ALTER TABLE bug_reports ADD COLUMN IF NOT EXISTS user_role TEXT;
ALTER TABLE bug_reports ADD COLUMN IF NOT EXISTS app_version TEXT DEFAULT '0.1.0-beta';

-- Backfill user_id from reporter_id if it exists
UPDATE bug_reports SET user_id = reporter_id WHERE user_id IS NULL AND reporter_id IS NOT NULL;

-- Backfill what_happened from description if it exists
UPDATE bug_reports SET what_happened = description WHERE what_happened IS NULL AND description IS NOT NULL;
