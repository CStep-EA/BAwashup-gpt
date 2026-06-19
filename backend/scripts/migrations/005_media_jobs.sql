-- Sprint 14: Media Pipeline — media_jobs table
-- Run in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS media_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  r2_path TEXT NOT NULL,
  status TEXT DEFAULT 'pending'
    CHECK (status IN ('pending','processing','complete','failed')),
  result_report_id UUID REFERENCES reports(id),
  error_message TEXT,
  frames_extracted INT,
  frames_analyzed INT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_media_jobs_user_id ON media_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_media_jobs_status ON media_jobs(status);
