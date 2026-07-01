-- Migration 006: Ensure feedback table exists
-- This migration re-creates the feedback table if it was missing from the schema cache.
-- Run this in the Supabase SQL Editor if you see PGRST205 errors for public.feedback.
-- 
-- After running this SQL, reload the PostgREST schema cache:
--   SELECT pg_notify('pgrst', 'reload schema');

-- Create feedback table (IF NOT EXISTS is safe to re-run)
CREATE TABLE IF NOT EXISTS public.feedback (
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

-- Ensure RLS is enabled
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- Re-create policies (DROP IF EXISTS first for idempotency)
DROP POLICY IF EXISTS "Users can insert own feedback" ON public.feedback;
DROP POLICY IF EXISTS "Users can read own feedback" ON public.feedback;
DROP POLICY IF EXISTS "Service role full access feedback" ON public.feedback;

CREATE POLICY "Users can insert own feedback"
  ON public.feedback FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read own feedback"
  ON public.feedback FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Service role full access feedback"
  ON public.feedback FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON public.feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON public.feedback(created_at DESC);

-- CRITICAL: Reload PostgREST schema cache so the table appears
SELECT pg_notify('pgrst', 'reload schema');
