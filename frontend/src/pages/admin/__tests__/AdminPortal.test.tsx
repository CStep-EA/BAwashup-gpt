/**
 * AdminPortal Tests — Sprint 12
 * 11 required tests covering all 6 admin pages.
 *
 * Uses Vitest + React Testing Library with mocked API calls.
 *
 * Tests:
 *  1. AdminDashboard: renders 8 metric cards on successful fetch
 *  2. AdminDashboard: renders error state with retry button
 *  3. AdminDashboard: date range selector changes active button
 *  4. AdminUsers: renders user table with role badges
 *  5. AdminUsers: shows invite modal on button click
 *  6. AdminConfig: renders config items with toggle for boolean values
 *  7. AdminConfig: shows org_admin badge on restricted config
 *  8. AdminBugs: renders bug list with severity badges
 *  9. AdminBugs: opens detail panel on row click
 * 10. AdminVersions: renders version accordion items
 * 11. AuditLogPage: renders audit log table entries
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type {
  AnalyticsSummary,
  TopProduct,
  DailyUsage,
  AdminUserItem,
  ConfigItem,
  AdminBugReport,
  VersionLogItem,
  AuditLogEntry,
} from '@/lib/api'

// ─── Mocks ───────────────────────────────────────────────────────────────────

vi.mock('@/lib/api', () => ({
  fetchAnalyticsSummary: vi.fn(),
  fetchTopProducts: vi.fn(),
  fetchUsageByDay: vi.fn(),
  fetchAdminUsers: vi.fn(),
  inviteUser: vi.fn(),
  updateUser: vi.fn(),
  deactivateUser: vi.fn(),
  fetchAdminConfig: vi.fn(),
  updateConfig: vi.fn(),
  fetchAdminBugs: vi.fn(),
  fetchAdminBugDetail: vi.fn(),
  updateAdminBug: vi.fn(),
  getAdminBugsExportUrl: vi.fn().mockReturnValue('/admin/bugs/export'),
  fetchAdminVersions: vi.fn(),
  createVersion: vi.fn(),
  getVersionsExportUrl: vi.fn().mockReturnValue('/admin/versions/export'),
  fetchAuditLog: vi.fn(),
  getAuditExportUrl: vi.fn().mockReturnValue('/admin/audit/export'),
}))

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: null }),
        }),
      }),
    }),
  },
}))

// Mock auth store — default to org_admin
const mockAuthState = {
  user: { id: 'user-org-1', email: 'admin@bowerag.test' },
  profile: { id: 'user-org-1', full_name: 'Org Admin', role: 'org_admin', location_id: null, customer_operation: null, active: true },
  role: 'org_admin',
  locationCode: null,
  isLoading: false,
  isAuthenticated: true,
  error: null,
  login: vi.fn(),
  logout: vi.fn(),
  initialize: vi.fn(),
  setLocationCode: vi.fn(),
  clearError: vi.fn(),
}

vi.mock('@/store/auth', () => ({
  useAuthStore: vi.fn(() => mockAuthState),
}))

// Mock recharts to avoid SVG rendering issues in jsdom
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  Line: () => null,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
}))

import {
  fetchAnalyticsSummary,
  fetchTopProducts,
  fetchUsageByDay,
  fetchAdminUsers,
  fetchAdminConfig,
  fetchAdminBugs,
  fetchAdminVersions,
  fetchAuditLog,
} from '@/lib/api'

const mockFetchAnalyticsSummary = vi.mocked(fetchAnalyticsSummary)
const mockFetchTopProducts = vi.mocked(fetchTopProducts)
const mockFetchUsageByDay = vi.mocked(fetchUsageByDay)
const mockFetchAdminUsers = vi.mocked(fetchAdminUsers)
const mockFetchAdminConfig = vi.mocked(fetchAdminConfig)
const mockFetchAdminBugs = vi.mocked(fetchAdminBugs)
const mockFetchAdminVersions = vi.mocked(fetchAdminVersions)
const mockFetchAuditLog = vi.mocked(fetchAuditLog)

// ─── Test Data ───────────────────────────────────────────────────────────────

const MOCK_SUMMARY: AnalyticsSummary = {
  total_queries: 150,
  queries_today: 12,
  active_users: 8,
  queries_by_domain: [
    { domain: 'conversation', count: 100 },
    { domain: 'governance', count: 50 },
  ],
  queries_by_location: [
    { location_locked: 'EVANS', count: 80 },
    { location_locked: 'JEROME', count: 70 },
  ],
  avg_response_ms: 245.3,
  governance_blocks: 5,
  claude_api_calls: 120,
  thumbs_up: 30,
  thumbs_down: 3,
  open_bugs: 4,
  open_critical_bugs: 1,
}

const MOCK_TOP_PRODUCTS: TopProduct[] = [
  { product_name: 'Udder Comfort', mention_count: 25 },
  { product_name: 'BarrierMax', mention_count: 15 },
]

const MOCK_USAGE: DailyUsage[] = [
  { date: '2026-05-12', query_count: 40, active_users: 5 },
  { date: '2026-05-13', query_count: 55, active_users: 7 },
]

const MOCK_USERS: AdminUserItem[] = [
  {
    id: 'u1',
    full_name: 'Alice Admin',
    email: 'alice@bowerag.test',
    role: 'org_admin',
    location_name: 'Evans',
    active: true,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'u2',
    full_name: 'Bob Consultant',
    email: 'bob@bowerag.test',
    role: 'consultant',
    location_name: 'Jerome',
    active: true,
    created_at: '2026-02-01T00:00:00Z',
  },
]

const MOCK_CONFIG: ConfigItem[] = [
  {
    key: 'maintenance_mode',
    value: false,
    description: 'Enable maintenance mode',
    editable_by: 'org_admin',
    updated_by: null,
    updated_at: null,
  },
  {
    key: 'max_conversation_length',
    value: 50,
    description: 'Max messages per conversation',
    editable_by: 'admin_manager',
    updated_by: null,
    updated_at: null,
  },
]

const MOCK_BUGS: AdminBugReport[] = [
  {
    id: 'bug1',
    title: 'Login fails on Safari',
    description: 'Users cannot log in using Safari browser',
    severity: 'critical',
    status: 'open',
    version_tag: 'v1.0.0',
    reporter_name: 'Bob Consultant',
    reporter_email: null,
    steps_to_reproduce: '1. Open Safari 2. Try to log in',
    expected_behavior: 'Should log in successfully',
    actual_behavior: 'Gets blank screen',
    fix_notes: null,
    resolved_at: null,
    created_at: '2026-05-10T08:00:00Z',
  },
  {
    id: 'bug2',
    title: 'Report export timeout',
    description: 'Reports take too long to export',
    severity: 'medium',
    status: 'investigating',
    version_tag: 'v1.0.0',
    reporter_name: 'Alice Admin',
    reporter_email: null,
    steps_to_reproduce: null,
    expected_behavior: null,
    actual_behavior: null,
    fix_notes: null,
    resolved_at: null,
    created_at: '2026-05-11T10:00:00Z',
  },
]

const MOCK_VERSIONS: VersionLogItem[] = [
  {
    id: 'ver1',
    version_tag: 'v1.0.12',
    release_date: '2026-05-14',
    release_notes: 'Admin portal frontend complete',
    breaking_changes: null,
    bugs_resolved: ['bug1'],
    deployed_by: 'u1',
    created_at: '2026-05-14T00:00:00Z',
  },
  {
    id: 'ver2',
    version_tag: 'v1.0.11',
    release_date: '2026-05-13',
    release_notes: 'Admin portal backend',
    breaking_changes: null,
    bugs_resolved: null,
    deployed_by: 'u1',
    created_at: '2026-05-13T00:00:00Z',
  },
]

const MOCK_AUDIT_ENTRIES: AuditLogEntry[] = [
  {
    id: 'audit1',
    user_id: 'u2',
    user_name: 'Bob Consultant',
    user_role: 'consultant',
    action: 'query',
    domain: 'conversation',
    query_text: 'What products are available?',
    governance_result: null,
    location_locked: 'EVANS',
    duration_ms: 320,
    created_at: '2026-05-14T09:00:00Z',
  },
  {
    id: 'audit2',
    user_id: 'u1',
    user_name: 'Alice Admin',
    user_role: 'org_admin',
    action: 'config_updated',
    domain: 'admin',
    query_text: 'maintenance_mode',
    governance_result: null,
    location_locked: null,
    duration_ms: null,
    created_at: '2026-05-14T08:30:00Z',
  },
]

// ─── Helper ──────────────────────────────────────────────────────────────────

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

// ─── Tests ───────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks()
})

// ── AdminDashboard Tests ─────────────────────────────────────────────────────

describe('AdminDashboard', () => {
  // Import here to ensure mocks are set up first
  let AdminDashboard: typeof import('@/pages/admin/AdminDashboard').AdminDashboard

  beforeEach(async () => {
    const mod = await import('@/pages/admin/AdminDashboard')
    AdminDashboard = mod.AdminDashboard
  })

  test('1. renders 8 metric cards on successful fetch', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(MOCK_SUMMARY)
    mockFetchTopProducts.mockResolvedValue(MOCK_TOP_PRODUCTS)
    mockFetchUsageByDay.mockResolvedValue(MOCK_USAGE)

    renderWithRouter(<AdminDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument()
    })

    // Check all 8 metric cards render their values
    expect(screen.getByText('150')).toBeInTheDocument() // total_queries
    expect(screen.getByText('8')).toBeInTheDocument() // active_users
    expect(screen.getByText('120')).toBeInTheDocument() // claude_api_calls
    expect(screen.getByText('245.3ms')).toBeInTheDocument() // avg_response_ms
    expect(screen.getByText('5')).toBeInTheDocument() // governance_blocks
    expect(screen.getByText('4')).toBeInTheDocument() // open_bugs
    expect(screen.getByText('30')).toBeInTheDocument() // thumbs_up
    expect(screen.getByText('3')).toBeInTheDocument() // thumbs_down
  })

  test('2. renders error state with retry button', async () => {
    mockFetchAnalyticsSummary.mockRejectedValue(new Error('Network error'))
    mockFetchTopProducts.mockRejectedValue(new Error('Network error'))
    mockFetchUsageByDay.mockRejectedValue(new Error('Network error'))

    renderWithRouter(<AdminDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load analytics')).toBeInTheDocument()
    })

    expect(screen.getByText('Retry')).toBeInTheDocument()
  })

  test('3. date range selector changes active button styling', async () => {
    mockFetchAnalyticsSummary.mockResolvedValue(MOCK_SUMMARY)
    mockFetchTopProducts.mockResolvedValue(MOCK_TOP_PRODUCTS)
    mockFetchUsageByDay.mockResolvedValue(MOCK_USAGE)

    renderWithRouter(<AdminDashboard />)

    await waitFor(() => {
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument()
    })

    // Default is 7d which should have the active class
    const btn7d = screen.getByText('7d')
    expect(btn7d.className).toContain('bg-accent')

    // Click 30d
    fireEvent.click(screen.getByText('30d'))

    await waitFor(() => {
      const btn30d = screen.getByText('30d')
      expect(btn30d.className).toContain('bg-accent')
    })
  })
})

// ── AdminUsers Tests ─────────────────────────────────────────────────────────

describe('AdminUsers', () => {
  let AdminUsers: typeof import('@/pages/admin/AdminUsers').AdminUsers

  beforeEach(async () => {
    const mod = await import('@/pages/admin/AdminUsers')
    AdminUsers = mod.AdminUsers
  })

  test('4. renders user table with role badges', async () => {
    mockFetchAdminUsers.mockResolvedValue(MOCK_USERS)

    renderWithRouter(<AdminUsers />)

    await waitFor(() => {
      expect(screen.getByText('User Management')).toBeInTheDocument()
    })

    // Check user names render
    expect(screen.getByText('Alice Admin')).toBeInTheDocument()
    expect(screen.getByText('Bob Consultant')).toBeInTheDocument()

    // Check role badges (use getAllByText since filter dropdown also has these values)
    const orgAdminBadges = screen.getAllByText('org admin')
    expect(orgAdminBadges.length).toBeGreaterThanOrEqual(1)
    // At least one should be the badge (span element)
    const badge = orgAdminBadges.find(el => el.tagName === 'SPAN')
    expect(badge).toBeTruthy()
    expect(screen.getAllByText('consultant').length).toBeGreaterThanOrEqual(1)
  })

  test('5. shows invite modal on button click', async () => {
    mockFetchAdminUsers.mockResolvedValue(MOCK_USERS)

    renderWithRouter(<AdminUsers />)

    await waitFor(() => {
      expect(screen.getByText('User Management')).toBeInTheDocument()
    })

    // Click Invite User button
    fireEvent.click(screen.getByText('Invite User'))

    await waitFor(() => {
      expect(screen.getByText('Send Invite')).toBeInTheDocument()
      expect(screen.getByLabelText('Email')).toBeInTheDocument()
      expect(screen.getByLabelText('Full Name')).toBeInTheDocument()
      expect(screen.getByLabelText('Role')).toBeInTheDocument()
    })
  })
})

// ── AdminConfig Tests ────────────────────────────────────────────────────────

describe('AdminConfig', () => {
  let AdminConfig: typeof import('@/pages/admin/AdminConfig').AdminConfig

  beforeEach(async () => {
    const mod = await import('@/pages/admin/AdminConfig')
    AdminConfig = mod.AdminConfig
  })

  test('6. renders config items with toggle for boolean values', async () => {
    mockFetchAdminConfig.mockResolvedValue(MOCK_CONFIG)

    renderWithRouter(<AdminConfig />)

    await waitFor(() => {
      expect(screen.getByText('Configuration')).toBeInTheDocument()
    })

    // Check config keys render (with underscores replaced by spaces)
    expect(screen.getByText('maintenance mode')).toBeInTheDocument()
    expect(screen.getByText('max conversation length')).toBeInTheDocument()

    // Boolean value shows Disabled (maintenance_mode is false)
    expect(screen.getByText('Disabled')).toBeInTheDocument()
  })

  test('7. shows org_admin badge on restricted config', async () => {
    mockFetchAdminConfig.mockResolvedValue(MOCK_CONFIG)

    renderWithRouter(<AdminConfig />)

    await waitFor(() => {
      expect(screen.getByText('Configuration')).toBeInTheDocument()
    })

    // maintenance_mode has editable_by='org_admin' so it should show the badge
    expect(screen.getByText('org_admin only')).toBeInTheDocument()
  })
})

// ── AdminBugs Tests ──────────────────────────────────────────────────────────

describe('AdminBugs', () => {
  let AdminBugs: typeof import('@/pages/admin/AdminBugs').AdminBugs

  beforeEach(async () => {
    const mod = await import('@/pages/admin/AdminBugs')
    AdminBugs = mod.AdminBugs
  })

  test('8. renders bug list with severity badges', async () => {
    mockFetchAdminBugs.mockResolvedValue(MOCK_BUGS)

    renderWithRouter(<AdminBugs />)

    await waitFor(() => {
      expect(screen.getByText('Bug Reports')).toBeInTheDocument()
    })

    // Check bug titles
    expect(screen.getByText('Login fails on Safari')).toBeInTheDocument()
    expect(screen.getByText('Report export timeout')).toBeInTheDocument()

    // Check severity badges (use getAllByText since filter dropdown also has these values)
    const criticalEls = screen.getAllByText('critical')
    expect(criticalEls.length).toBeGreaterThanOrEqual(1)
    const mediumEls = screen.getAllByText('medium')
    expect(mediumEls.length).toBeGreaterThanOrEqual(1)
  })

  test('9. opens detail panel on row click', async () => {
    mockFetchAdminBugs.mockResolvedValue(MOCK_BUGS)

    renderWithRouter(<AdminBugs />)

    await waitFor(() => {
      expect(screen.getByText('Login fails on Safari')).toBeInTheDocument()
    })

    // Click the first bug row
    fireEvent.click(screen.getByText('Login fails on Safari'))

    await waitFor(() => {
      expect(screen.getByText('Bug Detail')).toBeInTheDocument()
      expect(screen.getByText('Update Bug')).toBeInTheDocument()
      // Detail panel shows description (may appear in both table row and detail panel)
      const descriptionEls = screen.getAllByText('Users cannot log in using Safari browser')
      expect(descriptionEls.length).toBeGreaterThanOrEqual(2) // one in table, one in detail panel
    })
  })
})

// ── AdminVersions Tests ──────────────────────────────────────────────────────

describe('AdminVersions', () => {
  let AdminVersions: typeof import('@/pages/admin/AdminVersions').AdminVersions

  beforeEach(async () => {
    const mod = await import('@/pages/admin/AdminVersions')
    AdminVersions = mod.AdminVersions
  })

  test('10. renders version accordion items', async () => {
    mockFetchAdminVersions.mockResolvedValue(MOCK_VERSIONS)

    renderWithRouter(<AdminVersions />)

    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument()
    })

    // Check version tags render
    expect(screen.getByText('v1.0.12')).toBeInTheDocument()
    expect(screen.getByText('v1.0.11')).toBeInTheDocument()

    // Check version count
    expect(screen.getByText('2 versions recorded')).toBeInTheDocument()

    // org_admin should see New Release button
    expect(screen.getByText('New Release')).toBeInTheDocument()
  })
})

// ── AuditLogPage Tests ───────────────────────────────────────────────────────

describe('AuditLogPage', () => {
  let AuditLogPage: typeof import('@/pages/admin/AuditLogPage').AuditLogPage

  beforeEach(async () => {
    const mod = await import('@/pages/admin/AuditLogPage')
    AuditLogPage = mod.AuditLogPage
  })

  test('11. renders audit log table entries', async () => {
    mockFetchAuditLog.mockResolvedValue(MOCK_AUDIT_ENTRIES)

    renderWithRouter(<AuditLogPage />)

    await waitFor(() => {
      expect(screen.getByText('Audit Log')).toBeInTheDocument()
    })

    // Check entries render
    expect(screen.getByText('Bob Consultant')).toBeInTheDocument()
    expect(screen.getByText('Alice Admin')).toBeInTheDocument()

    // Check actions
    expect(screen.getByText('query')).toBeInTheDocument()
    expect(screen.getByText('config_updated')).toBeInTheDocument()

    // Check entry count
    expect(screen.getByText('2 entries')).toBeInTheDocument()
  })
})
