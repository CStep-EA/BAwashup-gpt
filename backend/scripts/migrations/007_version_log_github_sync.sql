-- Migration 007: Add GitHub sync columns to version_log
-- Sprint 21: Auto-populate versions from GitHub PRs and releases
-- Run in Supabase SQL Editor

-- Add new columns for GitHub sync data
ALTER TABLE public.version_log
  ADD COLUMN IF NOT EXISTS source text DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS pr_number int,
  ADD COLUMN IF NOT EXISTS pr_title text,
  ADD COLUMN IF NOT EXISTS pr_url text;

-- Index for dedup checks
CREATE INDEX IF NOT EXISTS idx_version_log_pr_number ON public.version_log(pr_number)
  WHERE pr_number IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_version_log_source ON public.version_log(source);

-- Reload PostgREST schema cache
SELECT pg_notify('pgrst', 'reload schema');
