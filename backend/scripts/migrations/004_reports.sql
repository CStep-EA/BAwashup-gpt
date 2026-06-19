-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration 004: Reports Table
-- Sprint 9: Customer-facing report storage with RLS.
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_by UUID REFERENCES profiles(id),
    customer_name TEXT NOT NULL,
    operation_name TEXT NOT NULL,
    location_code TEXT NOT NULL,
    product_ids UUID[],
    findings TEXT,
    recommendations TEXT,
    rep_name TEXT,
    rep_title TEXT,
    include_pricing BOOLEAN DEFAULT false,
    report_content TEXT,
    docx_r2_path TEXT,
    status TEXT DEFAULT 'generating'
        CHECK (status IN ('generating', 'complete', 'failed', 'deleted')),
    shared_with_customer BOOLEAN DEFAULT false,
    shared_with_user_ids UUID[],
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;

-- Reps can see their own reports
CREATE POLICY rep_own_reports ON reports
    FOR SELECT USING (auth.uid() = created_by);

-- Reps can insert their own reports
CREATE POLICY rep_insert_reports ON reports
    FOR INSERT WITH CHECK (auth.uid() = created_by);

-- Reps can update their own reports
CREATE POLICY rep_update_own_reports ON reports
    FOR UPDATE USING (auth.uid() = created_by);

-- Customers can see reports shared with them
CREATE POLICY customer_shared_reports ON reports
    FOR SELECT USING (
        auth.uid() = ANY(shared_with_user_ids)
        AND shared_with_customer = true
    );

-- Admins can see and manage all reports
CREATE POLICY admin_all_reports ON reports
    FOR ALL USING (
        (SELECT role FROM profiles WHERE id = auth.uid())
        IN ('org_admin', 'admin_manager')
    );

-- Indexes
CREATE INDEX IF NOT EXISTS idx_reports_created_by ON reports(created_by);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status) WHERE status != 'deleted';
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_reports_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_reports_updated_at
    BEFORE UPDATE ON reports
    FOR EACH ROW
    EXECUTE FUNCTION update_reports_updated_at();
