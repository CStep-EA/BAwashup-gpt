-- Migration: Add shared_with_emails column to reports table
-- Supports sharing reports with external email addresses (admin/manager feature)

ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS shared_with_emails text[] DEFAULT '{}';

-- Add comment for documentation
COMMENT ON COLUMN reports.shared_with_emails IS 'External email addresses the report has been shared with (admin/manager only)';
