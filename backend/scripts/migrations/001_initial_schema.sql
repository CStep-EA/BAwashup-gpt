-- ═══════════════════════════════════════════════════════════════════════════════
-- Bower Ag CowCare Tool — Initial Database Schema
-- Migration 001 | Sprint 1 | v0.0.1
--
-- RUN THIS IN: Supabase SQL Editor (paste entire file, execute)
-- PREREQ: Enable pgvector extension first:
--   Database > Extensions > search "vector" > Enable
--
-- Tables (10): locations, products, product_sellability, pricing, profiles,
--              audit_log, document_chunks, bug_reports, version_log, system_config
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- EXTENSION: pgvector (must be enabled before creating embedding columns)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS vector;


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 1: locations
-- Branch locations where Bower Ag operates. Used for pricing lock + sellability.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    region TEXT,
    branch_code TEXT UNIQUE NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 2: products
-- Master product catalog. Source of truth for product existence.
-- product_type: what category the product falls into
-- usage_timing: when teat dip is applied (pre-milking, post-milking, or both)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_name TEXT NOT NULL,
    part_number TEXT UNIQUE,
    category TEXT NOT NULL,
    product_type TEXT NOT NULL,
    active_ingredient TEXT,
    chemistry_type TEXT,
    germicide_type TEXT,
    usage_timing TEXT,
    is_concentrate BOOLEAN DEFAULT false,
    emollient_pct NUMERIC,
    emollient_type TEXT,
    notes TEXT,
    sds_verified BOOLEAN DEFAULT false,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT valid_product_type CHECK (product_type IN ('teat_dip', 'chemical', 'cip')),
    CONSTRAINT valid_usage_timing CHECK (
        usage_timing IS NULL OR usage_timing IN ('pre', 'post', 'both')
    )
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 3: product_sellability
-- Location hard-lock enforcement table. Binary: can this product be sold here?
-- Governance engine queries this — never the LLM.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS product_sellability (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    sellable BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(product_id, location_id)
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 4: pricing
-- Versioned pricing — never delete, always supersede.
-- superseded_date IS NULL = current active price.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    location_id UUID NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    container_size TEXT NOT NULL,
    uom TEXT NOT NULL,
    price_per_unit NUMERIC(10,4) NOT NULL,
    extended_price NUMERIC(10,4),
    version INTEGER DEFAULT 1,
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    superseded_date DATE,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 5: profiles
-- Extends Supabase auth.users. Defines role + location assignment.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'consultant',
    location_id UUID REFERENCES locations(id),
    customer_operation TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT valid_role CHECK (role IN (
        'org_admin', 'admin_manager', 'consultant',
        'technician', 'account_manager', 'customer'
    ))
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 6: audit_log
-- Every query, every governance check, every LLM call is logged here.
-- The audit trail for governance compliance and analytics.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id),
    action TEXT NOT NULL,
    domain TEXT,
    query_text TEXT,
    location_locked TEXT,
    governance_result JSONB,
    llm_called BOOLEAN DEFAULT false,
    response_summary TEXT,
    feedback_rating SMALLINT,
    duration_ms INTEGER,
    app_version TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 7: document_chunks
-- RAG layer storage. Advisory documents chunked by section with embeddings.
-- pgvector enables similarity search for troubleshooting/advisory queries.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc TEXT NOT NULL,
    section_title TEXT,
    domain TEXT,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 8: bug_reports
-- In-app bug reporting. Reps file from chat, admins triage in portal.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS bug_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id UUID REFERENCES profiles(id),
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    version_tag TEXT,
    steps_to_reproduce TEXT,
    expected_behavior TEXT,
    actual_behavior TEXT,
    fix_notes TEXT,
    conversation_id UUID,
    user_role TEXT,
    resolved_by UUID REFERENCES profiles(id),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    CONSTRAINT valid_bug_status CHECK (status IN ('open', 'in_progress', 'resolved', 'wontfix'))
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 9: version_log
-- Release history. Every deployment gets a version entry.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS version_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_tag TEXT NOT NULL,
    release_date DATE DEFAULT CURRENT_DATE,
    release_notes TEXT,
    breaking_changes TEXT,
    bugs_resolved TEXT[],
    deployed_by UUID REFERENCES profiles(id),
    created_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 10: system_config
-- Feature toggles and system settings. Admin-editable, no code deploy needed.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSONB,
    description TEXT,
    editable_by TEXT DEFAULT 'admin_manager',
    updated_by UUID REFERENCES profiles(id),
    updated_at TIMESTAMPTZ DEFAULT now()
);


-- ═══════════════════════════════════════════════════════════════════════════════
-- INDEXES
-- Performance-critical queries get dedicated indexes.
-- ═══════════════════════════════════════════════════════════════════════════════

-- Fast sellability lookups by product
CREATE INDEX IF NOT EXISTS idx_product_sellability_product
    ON product_sellability(product_id);

-- Fast sellability lookups by location
CREATE INDEX IF NOT EXISTS idx_product_sellability_location
    ON product_sellability(location_id);

-- Active pricing only (where superseded_date IS NULL)
CREATE INDEX IF NOT EXISTS idx_pricing_active
    ON pricing(product_id, location_id)
    WHERE superseded_date IS NULL;

-- Audit log time-series queries
CREATE INDEX IF NOT EXISTS idx_audit_log_created
    ON audit_log(created_at DESC);

-- Audit log user queries
CREATE INDEX IF NOT EXISTS idx_audit_log_user
    ON audit_log(user_id);

-- Product name search (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_products_name
    ON products USING gin (product_name gin_trgm_ops);

-- pgvector similarity search on document chunks
-- NOTE: ivfflat requires rows to exist before building. Run AFTER embedding.
-- For initial setup, use HNSW which works on empty tables:
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops);


-- ═══════════════════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS)
-- Governance enforcement at the database layer.
-- ═══════════════════════════════════════════════════════════════════════════════

-- Enable RLS on security-sensitive tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_sellability ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- PROFILES: Users can read their own profile. Service role bypasses for backend.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE POLICY own_profile_read ON profiles
    FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY own_profile_update ON profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ─────────────────────────────────────────────────────────────────────────────
-- PRICING: Only authenticated non-customer users can view pricing.
-- Customers NEVER see raw pricing data.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE POLICY pricing_auth_only ON pricing
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND (
            SELECT role FROM profiles WHERE id = auth.uid()
        ) != 'customer'
    );

-- ─────────────────────────────────────────────────────────────────────────────
-- AUDIT_LOG: Users can see their own audit entries. Admins see all (via service role).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE POLICY audit_own_read ON audit_log
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY audit_insert_own ON audit_log
    FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- ─────────────────────────────────────────────────────────────────────────────
-- PRODUCT_SELLABILITY: Only authenticated non-customer users can view.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE POLICY sellability_auth_only ON product_sellability
    FOR SELECT
    USING (
        auth.role() = 'authenticated'
        AND (
            SELECT role FROM profiles WHERE id = auth.uid()
        ) != 'customer'
    );


-- ═══════════════════════════════════════════════════════════════════════════════
-- SEED DATA
-- Initial locations and system configuration for beta launch.
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─────────────────────────────────────────────────────────────────────────────
-- 5 Branch Locations
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO locations (name, state, region, branch_code) VALUES
    ('Evans', 'CO', 'Colorado', 'EVANS'),
    ('Ulysses', 'KS', 'Kansas', 'ULYSSES'),
    ('Jerome', 'ID', 'Idaho', 'JEROME'),
    ('Turlock', 'CA', 'California', 'TURLOCK'),
    ('Tulare', 'CA', 'California', 'TULARE')
ON CONFLICT (branch_code) DO NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7 System Configuration Keys
-- ─────────────────────────────────────────────────────────────────────────────
INSERT INTO system_config (key, value, description, editable_by) VALUES
    (
        'feature.video_upload',
        'false'::jsonb,
        'Enable video/image upload for reps in chat interface',
        'org_admin'
    ),
    (
        'feature.customer_portal',
        'true'::jsonb,
        'Enable customer-facing report portal for shared reports',
        'admin_manager'
    ),
    (
        'feature.proposal_generator',
        'false'::jsonb,
        'Enable automatic proposal generation from conversation data',
        'org_admin'
    ),
    (
        'feature.spanish_mode',
        'false'::jsonb,
        'Enable Spanish language toggle in chat interface',
        'org_admin'
    ),
    (
        'pricing.visible_to_roles',
        '["consultant", "technician", "account_manager", "admin_manager", "org_admin"]'::jsonb,
        'Roles that can view pricing data through governance endpoints',
        'admin_manager'
    ),
    (
        'chat.max_history_length',
        '20'::jsonb,
        'Maximum number of messages stored per chat session',
        'org_admin'
    ),
    (
        'maintenance.mode',
        'false'::jsonb,
        'Show maintenance banner and disable chat. Use for deployments.',
        'org_admin'
    )
ON CONFLICT (key) DO NOTHING;


-- ═══════════════════════════════════════════════════════════════════════════════
-- TRIGGER: Auto-update updated_at on products table
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ═══════════════════════════════════════════════════════════════════════════════
-- DONE
-- Run verify_schema.py to confirm all tables and seed data are correct.
-- ═══════════════════════════════════════════════════════════════════════════════
