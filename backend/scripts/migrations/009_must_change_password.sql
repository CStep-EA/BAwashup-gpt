-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration 009: Add must_change_password flag to profiles
-- Used to force users to change their password on first login when an admin
-- sets a temporary password for them.
-- ═══════════════════════════════════════════════════════════════════════════════

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;

-- Allow users to update their own must_change_password flag (to clear it after changing password)
-- This is needed because the frontend clears the flag after password change.
CREATE POLICY "Users can clear own must_change_password" ON profiles
  FOR UPDATE TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);
