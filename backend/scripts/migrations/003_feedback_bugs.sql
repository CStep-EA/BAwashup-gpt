-- Sprint 7: Feedback and Bug Reports tables
-- Run in Supabase SQL Editor

-- Feedback table for thumbs up/down
CREATE TABLE IF NOT EXISTS feedback (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id),
  conversation_id text,
  message_index int,
  rating int NOT NULL CHECK (rating IN (-1, 0, 1)),
  comment text,
  session_id text,
  user_role text,
  app_version text DEFAULT '0.0.1',
  created_at timestamptz DEFAULT now()
);

-- Bug reports table
CREATE TABLE IF NOT EXISTS bug_reports (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id),
  title text NOT NULL,
  what_happened text NOT NULL,
  expected_behavior text,
  severity text NOT NULL DEFAULT 'medium' CHECK (severity IN ('critical', 'high', 'medium', 'low')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'fixed', 'wont_fix', 'duplicate')),
  conversation_id text,
  session_id text,
  user_role text,
  location_code text,
  app_version text DEFAULT '0.0.1',
  admin_notes text,
  resolved_at timestamptz,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- RLS policies
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE bug_reports ENABLE ROW LEVEL SECURITY;

-- Feedback: users can insert their own, admins can read all
CREATE POLICY "Users can insert own feedback"
  ON feedback FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own feedback"
  ON feedback FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Bug reports: any authenticated user can insert, admins can read all
CREATE POLICY "Users can insert bug reports"
  ON bug_reports FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own bug reports"
  ON bug_reports FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Service role bypass for API server
CREATE POLICY "Service role full access feedback"
  ON feedback FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access bug_reports"
  ON bug_reports FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bug_reports_status ON bug_reports(status);
CREATE INDEX IF NOT EXISTS idx_bug_reports_severity ON bug_reports(severity);
CREATE INDEX IF NOT EXISTS idx_bug_reports_created_at ON bug_reports(created_at DESC);
