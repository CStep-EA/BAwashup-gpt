/**
 * Customer Portal Frontend Tests — Sprint 13
 * 7 tests for CustomerLayout, CustomerReportsPage, CustomerReportCard,
 * and CustomerReportViewPage.
 *
 * Uses Vitest + React Testing Library with mocked API calls.
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import type { CustomerReportSummary, CustomerReportDetail } from '@/lib/api'

// ─── Mocks ───────────────────────────────────────────────────────────────────

// Mock the API module
vi.mock('@/lib/api', () => ({
  fetchCustomerReports: vi.fn(),
  fetchCustomerReportDetail: vi.fn(),
}))

// Mock supabase (needed by auth store)
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      signInWithPassword: vi.fn(),
      signOut: vi.fn(),
      onAuthStateChange: vi.fn().mockReturnValue({ data: { subscription: { unsubscribe: vi.fn() } } }),
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

// Mock navigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

import { fetchCustomerReports, fetchCustomerReportDetail } from '@/lib/api'

// Typed mocks
const mockFetchCustomerReports = vi.mocked(fetchCustomerReports)
const mockFetchCustomerReportDetail = vi.mocked(fetchCustomerReportDetail)

// ─── Test data ──────────────────────────────────────────────────────────────

const MOCK_CUSTOMER_REPORTS: CustomerReportSummary[] = [
  {
    report_id: 'cr1',
    operation_name: 'Valley Main Barn',
    rep_name: 'Sarah Johnson',
    created_at: '2026-05-10T10:00:00Z',
    has_download: true,
  },
  {
    report_id: 'cr2',
    operation_name: 'Mountain Parlor Facility',
    rep_name: 'Mike Reynolds',
    created_at: '2026-05-12T10:00:00Z',
    has_download: false,
  },
]

const MOCK_REPORT_DETAIL: CustomerReportDetail = {
  report_id: 'cr1',
  operation_name: 'Valley Main Barn',
  rep_name: 'Sarah Johnson',
  rep_title: 'Bower Ag Consultant',
  report_content:
    '## Overview\n\nWe visited your operation and observed excellent milking protocols.\n\n## Recommendations\n\nContinue current post-dip program with Shield 52.',
  download_url: 'https://mock-r2.com/report.docx',
  created_at: '2026-05-10T10:00:00Z',
}

// ─── Setup ──────────────────────────────────────────────────────────────────

// Set mock customer profile before each test
async function setMockCustomerProfile() {
  const { useAuthStore } = await import('@/store/auth')
  useAuthStore.setState({
    user: { id: 'cust1', email: 'farmer@example.com' },
    profile: {
      id: 'cust1',
      full_name: 'John Farmer',
      role: 'customer',
      location_id: null,
      customer_operation: 'Happy Valley Farm',
      active: true,
    },
    role: 'customer',
    locationCode: null,
    isLoading: false,
    isAuthenticated: true,
    error: null,
  })
}

beforeEach(async () => {
  vi.clearAllMocks()
  await setMockCustomerProfile()
})

// ─── Lazy render helpers ────────────────────────────────────────────────────

async function renderCustomerLayout() {
  const { CustomerLayout } = await import('@/layouts/CustomerLayout')
  return render(
    <MemoryRouter>
      <CustomerLayout />
    </MemoryRouter>,
  )
}

async function renderCustomerReportsPage() {
  const { CustomerReportsPage } = await import('@/pages/customer/CustomerReportsPage')
  return render(
    <MemoryRouter>
      <CustomerReportsPage />
    </MemoryRouter>,
  )
}

async function renderCustomerReportCard(report: CustomerReportSummary) {
  const { CustomerReportCard } = await import('@/components/customer/CustomerReportCard')
  const onView = vi.fn()
  render(
    <MemoryRouter>
      <CustomerReportCard report={report} onView={onView} />
    </MemoryRouter>,
  )
  return { onView }
}

async function renderCustomerReportViewPage(reportId: string) {
  const { CustomerReportViewPage } = await import('@/pages/customer/CustomerReportViewPage')
  return render(
    <MemoryRouter initialEntries={[`/my-reports/${reportId}`]}>
      <Routes>
        <Route path="/my-reports/:reportId" element={<CustomerReportViewPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// TESTS
// ─────────────────────────────────────────────────────────────────────────────

describe('CustomerLayout', () => {
  test('renders branded header with customer name and sign-out button', async () => {
    await renderCustomerLayout()

    // Bower Ag branding
    expect(screen.getByText('Bower Ag')).toBeInTheDocument()
    expect(screen.getByText('CowCare Reports')).toBeInTheDocument()

    // Customer name
    expect(screen.getByTestId('customer-name')).toHaveTextContent('John Farmer')

    // Customer operation
    expect(screen.getByTestId('customer-operation')).toHaveTextContent('Happy Valley Farm')

    // Sign out button
    expect(screen.getByTestId('customer-sign-out')).toBeInTheDocument()

    // Footer
    expect(screen.getByText(/Contact your Bower Ag representative/)).toBeInTheDocument()
  })
})

describe('CustomerReportsPage', () => {
  test('shows warm welcome with customer first name and operation', async () => {
    mockFetchCustomerReports.mockResolvedValue(MOCK_CUSTOMER_REPORTS)

    await renderCustomerReportsPage()

    await waitFor(() => {
      expect(screen.getByTestId('customer-welcome')).toHaveTextContent('Welcome back, John!')
    })
    expect(screen.getByTestId('customer-operation-subtitle')).toHaveTextContent('Happy Valley Farm')
  })

  test('renders report list with correct count', async () => {
    mockFetchCustomerReports.mockResolvedValue(MOCK_CUSTOMER_REPORTS)

    await renderCustomerReportsPage()

    await waitFor(() => {
      expect(screen.getByTestId('customer-reports-list')).toBeInTheDocument()
    })
    expect(screen.getByText('2 reports available')).toBeInTheDocument()
    expect(screen.getByTestId('customer-report-card-cr1')).toBeInTheDocument()
    expect(screen.getByTestId('customer-report-card-cr2')).toBeInTheDocument()
  })

  test('shows empty state when no reports shared', async () => {
    mockFetchCustomerReports.mockResolvedValue([])

    await renderCustomerReportsPage()

    await waitFor(() => {
      expect(screen.getByTestId('customer-reports-empty')).toBeInTheDocument()
    })
    expect(screen.getByText('No reports yet')).toBeInTheDocument()
    expect(screen.getByText(/hasn't shared any reports/)).toBeInTheDocument()
  })
})

describe('CustomerReportCard', () => {
  test('displays operation name, rep name, and view button', async () => {
    const { onView } = await renderCustomerReportCard(MOCK_CUSTOMER_REPORTS[0])

    expect(screen.getByTestId('report-operation-name')).toHaveTextContent('Valley Main Barn')
    expect(screen.getByTestId('report-rep-name')).toHaveTextContent('Prepared by Sarah Johnson')
    expect(screen.getByTestId('report-date')).toBeInTheDocument()

    // Click view
    const user = userEvent.setup()
    await user.click(screen.getByTestId('view-report-cr1'))
    expect(onView).toHaveBeenCalledWith('cr1')
  })
})

describe('CustomerReportViewPage', () => {
  test('renders report content with sections and download bar', async () => {
    mockFetchCustomerReportDetail.mockResolvedValue(MOCK_REPORT_DETAIL)

    await renderCustomerReportViewPage('cr1')

    await waitFor(() => {
      expect(screen.getByTestId('report-view-page')).toBeInTheDocument()
    })

    // Header
    expect(screen.getByTestId('report-view-title')).toHaveTextContent('Valley Main Barn')
    expect(screen.getByTestId('report-view-rep')).toHaveTextContent('Prepared by Sarah Johnson, Bower Ag Consultant')

    // Content sections
    expect(screen.getByTestId('report-view-content')).toBeInTheDocument()
    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Recommendations')).toBeInTheDocument()
    expect(screen.getByText(/excellent milking protocols/)).toBeInTheDocument()

    // Download bar
    expect(screen.getByTestId('report-download-bar')).toBeInTheDocument()
    expect(screen.getByTestId('report-download-btn')).toHaveTextContent('Download Full Report (DOCX)')
  })

  test('shows error state and retry when API fails', async () => {
    mockFetchCustomerReportDetail.mockRejectedValue(new Error('API 500: Server error'))

    await renderCustomerReportViewPage('cr1')

    await waitFor(() => {
      expect(screen.getByTestId('report-view-error')).toBeInTheDocument()
    })
    expect(screen.getByText('Unable to load report')).toBeInTheDocument()
    expect(screen.getByTestId('report-view-retry')).toBeInTheDocument()
  })

  test('shows back button that navigates to /my-reports', async () => {
    mockFetchCustomerReportDetail.mockResolvedValue(MOCK_REPORT_DETAIL)

    await renderCustomerReportViewPage('cr1')

    await waitFor(() => {
      expect(screen.getByTestId('report-view-back')).toBeInTheDocument()
    })

    const user = userEvent.setup()
    await user.click(screen.getByTestId('report-view-back'))
    expect(mockNavigate).toHaveBeenCalledWith('/my-reports')
  })
})
