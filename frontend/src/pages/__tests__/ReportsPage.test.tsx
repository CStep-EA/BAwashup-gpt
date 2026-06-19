/**
 * ReportsPage Tests — Sprint 10
 * 9 required tests for report list, card, form, and share flow.
 *
 * Uses Vitest + React Testing Library with mocked API calls.
 */

import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import type { ReportSummary, ProductSummary, ReportGenerateResponse } from '@/lib/api'

// ─── Mocks ───────────────────────────────────────────────────────────────────

// Mock the API module
vi.mock('@/lib/api', () => ({
  fetchReports: vi.fn(),
  fetchReportDetail: vi.fn(),
  generateReport: vi.fn(),
  shareReport: vi.fn(),
  apiFetchRaw: vi.fn(),
  fetchProducts: vi.fn(),
  fetchPricingLookup: vi.fn(),
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

import {
  fetchReports,
  fetchProducts,
  generateReport,
  fetchPricingLookup,
  apiFetchRaw,
} from '@/lib/api'

// Typed mocks
const mockFetchReports = vi.mocked(fetchReports)
const mockFetchProducts = vi.mocked(fetchProducts)
const mockGenerateReport = vi.mocked(generateReport)
const mockFetchPricingLookup = vi.mocked(fetchPricingLookup)
const mockApiFetchRaw = vi.mocked(apiFetchRaw)

// ─── Test data ───────────────────────────────────────────────────────────────

const MOCK_REPORTS: ReportSummary[] = [
  {
    report_id: 'r1',
    customer_name: 'Valley Dairy',
    operation_name: 'Valley Main Barn',
    location_code: 'EVANS',
    status: 'complete',
    shared_with_customer: false,
    created_at: '2026-05-10T10:00:00Z',
  },
  {
    report_id: 'r2',
    customer_name: 'Mountain Farms',
    operation_name: 'Mountain Parlor',
    location_code: 'JEROME',
    status: 'generating',
    shared_with_customer: false,
    created_at: '2026-05-12T10:00:00Z',
  },
  {
    report_id: 'r3',
    customer_name: 'Sunrise Ranch',
    operation_name: 'Sunrise Facility',
    location_code: 'TURLOCK',
    status: 'failed',
    shared_with_customer: false,
    created_at: '2026-05-11T10:00:00Z',
  },
  {
    report_id: 'r4',
    customer_name: 'Shared Farm',
    operation_name: 'Shared Op',
    location_code: 'EVANS',
    status: 'complete',
    shared_with_customer: true,
    created_at: '2026-05-09T10:00:00Z',
  },
]

const MOCK_PRODUCTS: ProductSummary[] = [
  {
    id: 'p1',
    product_name: 'Shield 52',
    part_number: 'SH52',
    category: 'Teat Dip',
    product_type: 'teat_dip',
    chemistry_type: 'Iodine',
    germicide_type: null,
    usage_timing: 'post',
    is_concentrate: false,
    emollient_pct: 10,
    emollient_type: 'Glycerin',
    notes: null,
    sds_verified: true,
  },
  {
    id: 'p2',
    product_name: 'Curiass Gold',
    part_number: 'CG01',
    category: 'Teat Dip',
    product_type: 'teat_dip',
    chemistry_type: 'Chlorhexidine',
    germicide_type: null,
    usage_timing: 'post',
    is_concentrate: false,
    emollient_pct: 15,
    emollient_type: 'Lanolin',
    notes: null,
    sds_verified: true,
  },
]

// ─── Setup ───────────────────────────────────────────────────────────────────

// Reset reports store between tests
async function resetReportsStore() {
  const { useReportsStore } = await import('@/store/reports')
  useReportsStore.setState({
    reports: [],
    isLoading: false,
    error: null,
    pollingInterval: null,
    completedToast: null,
  })
}

// Reset auth store to have a profile
async function setMockProfile() {
  const { useAuthStore } = await import('@/store/auth')
  useAuthStore.setState({
    user: { id: 'u1', email: 'rep@bowerag.test' },
    profile: {
      id: 'u1',
      full_name: 'Test Rep',
      role: 'consultant',
      location_id: null,
      customer_operation: null,
      active: true,
    },
    role: 'consultant',
    locationCode: 'EVANS',
    isLoading: false,
    isAuthenticated: true,
    error: null,
  })
}

beforeEach(async () => {
  vi.clearAllMocks()
  await resetReportsStore()
  await setMockProfile()
})

// ─── Lazy imports (after mocks) ─────────────────────────────────────────────

async function renderReportsPage() {
  const { ReportsPage } = await import('@/pages/ReportsPage')
  return render(
    <MemoryRouter>
      <ReportsPage />
    </MemoryRouter>,
  )
}

async function renderReportCard(report: ReportSummary) {
  const { ReportCard } = await import('@/components/reports/ReportCard')
  const onDownload = vi.fn()
  const onShare = vi.fn()
  const onView = vi.fn()
  render(
    <MemoryRouter>
      <ReportCard report={report} onDownload={onDownload} onShare={onShare} onView={onView} />
    </MemoryRouter>,
  )
  return { onDownload, onShare, onView }
}

async function renderNewReportForm() {
  const { NewReportForm } = await import('@/components/reports/NewReportForm')
  const onClose = vi.fn()
  const onSuccess = vi.fn()
  render(
    <MemoryRouter>
      <NewReportForm onClose={onClose} onSuccess={onSuccess} />
    </MemoryRouter>,
  )
  return { onClose, onSuccess }
}

async function renderShareModal() {
  const { ShareReportModal } = await import('@/components/reports/ShareReportModal')
  const onClose = vi.fn()
  const onShared = vi.fn()
  render(
    <MemoryRouter>
      <ShareReportModal
        reportId="r1"
        reportTitle="Valley Dairy - Valley Main Barn"
        onClose={onClose}
        onShared={onShared}
      />
    </MemoryRouter>,
  )
  return { onClose, onShared }
}

// ─────────────────────────────────────────────────────────────────────────────
// TESTS
// ─────────────────────────────────────────────────────────────────────────────

describe('ReportsPage', () => {
  test('renders empty state when no reports', async () => {
    mockFetchReports.mockResolvedValue([])

    await renderReportsPage()

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument()
    })
    expect(screen.getByText('No reports yet.')).toBeInTheDocument()
    expect(screen.getByTestId('create-first-report-btn')).toBeInTheDocument()
  })
})

describe('ReportCard', () => {
  test('shows correct status badge for each status value', async () => {
    // Complete
    const { unmount: u1 } = render(
      await (async () => {
        const { ReportCard } = await import('@/components/reports/ReportCard')
        return (
          <MemoryRouter>
            <ReportCard
              report={{ ...MOCK_REPORTS[0], status: 'complete' }}
              onDownload={vi.fn()}
              onShare={vi.fn()}
              onView={vi.fn()}
            />
          </MemoryRouter>
        )
      })(),
    )
    expect(screen.getByTestId('status-badge-complete')).toHaveTextContent('Complete')
    u1()

    // Generating
    const { unmount: u2 } = render(
      await (async () => {
        const { ReportCard } = await import('@/components/reports/ReportCard')
        return (
          <MemoryRouter>
            <ReportCard
              report={{ ...MOCK_REPORTS[1], status: 'generating' }}
              onDownload={vi.fn()}
              onShare={vi.fn()}
              onView={vi.fn()}
            />
          </MemoryRouter>
        )
      })(),
    )
    expect(screen.getByTestId('status-badge-generating')).toHaveTextContent('Generating...')
    u2()

    // Failed
    render(
      await (async () => {
        const { ReportCard } = await import('@/components/reports/ReportCard')
        return (
          <MemoryRouter>
            <ReportCard
              report={{ ...MOCK_REPORTS[2], status: 'failed' }}
              onDownload={vi.fn()}
              onShare={vi.fn()}
              onView={vi.fn()}
            />
          </MemoryRouter>
        )
      })(),
    )
    expect(screen.getByTestId('status-badge-failed')).toHaveTextContent('Failed')
  })

  test("shows 'Shared with customer' badge when shared_with_customer=true", async () => {
    await renderReportCard(MOCK_REPORTS[3])

    expect(screen.getByTestId('shared-badge')).toBeInTheDocument()
    expect(screen.getByText('Shared with customer')).toBeInTheDocument()
  })
})

describe('NewReportForm', () => {
  test('step 1 validates required fields before enabling Next', async () => {
    mockFetchProducts.mockResolvedValue({ products: [], total_count: 0, has_more: false })

    await renderNewReportForm()

    // Next button should exist and be disabled (fields empty)
    const nextBtn = screen.getByRole('button', { name: /next/i })
    expect(nextBtn).toBeDisabled()

    // Fill required fields
    const user = userEvent.setup()
    const inputs = screen.getAllByRole('textbox')
    // Customer name is the first text input
    await user.type(inputs[0], 'Green Valley Dairy')
    // Operation name
    await user.type(inputs[1], 'Fresno CA')

    // Select location
    const locationSelect = screen.getByTestId('location-select')
    fireEvent.change(locationSelect, { target: { value: 'EVANS' } })

    // Rep name should be pre-filled from profile, but let's ensure it's filled
    // inputs[2] is rep name — it's pre-filled with 'Test Rep' from mock
    // inputs[3] is rep title

    // Next should now be enabled
    await waitFor(() => {
      expect(nextBtn).not.toBeDisabled()
    })
  })

  test('step 2 shows only products sellable at selected location', async () => {
    mockFetchProducts.mockResolvedValue({
      products: MOCK_PRODUCTS,
      total_count: 2,
      has_more: false,
    })

    await renderNewReportForm()

    // Fill step 1 to get to step 2
    const user = userEvent.setup()
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[0], 'Test Farm')
    await user.type(inputs[1], 'Test Op')
    fireEvent.change(screen.getByTestId('location-select'), { target: { value: 'EVANS' } })

    // Click Next
    const nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Step 2 should show products
    await waitFor(() => {
      expect(screen.getByText('Shield 52')).toBeInTheDocument()
      expect(screen.getByText('Curiass Gold')).toBeInTheDocument()
    })

    // Verify fetchProducts was called with location_code
    expect(mockFetchProducts).toHaveBeenCalledWith(
      expect.objectContaining({ location_code: 'EVANS' }),
    )
  })

  test('step 3 shows character count on textareas', async () => {
    mockFetchProducts.mockResolvedValue({
      products: MOCK_PRODUCTS,
      total_count: 2,
      has_more: false,
    })
    mockFetchPricingLookup.mockResolvedValue({
      pricing: [],
      count: 0,
      product_id: 'p1',
      location: 'Evans CO',
      location_code: 'EVANS',
      location_locked: false,
      effective_date: null,
      source: 'test',
    })

    await renderNewReportForm()

    const user = userEvent.setup()

    // Navigate through steps 1 & 2
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[0], 'Test Farm')
    await user.type(inputs[1], 'Test Op')
    fireEvent.change(screen.getByTestId('location-select'), { target: { value: 'EVANS' } })

    // Step 1 → 2
    let nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Select a product
    await waitFor(() => expect(screen.getByText('Shield 52')).toBeInTheDocument())
    await user.click(screen.getByText('Shield 52'))

    // Step 2 → 3
    nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Step 3: verify character counts
    await waitFor(() => {
      expect(screen.getByTestId('findings-count')).toHaveTextContent('0 characters')
      expect(screen.getByTestId('recs-count')).toHaveTextContent('0 characters')
    })

    // Type in findings textarea
    const findingsTextarea = screen.getByTestId('findings-textarea')
    await user.type(findingsTextarea, 'Cows look healthy!')

    expect(screen.getByTestId('findings-count')).toHaveTextContent('18 characters')
  })

  test('step 4 shows success state after successful generate', async () => {
    mockFetchProducts.mockResolvedValue({
      products: MOCK_PRODUCTS,
      total_count: 2,
      has_more: false,
    })
    mockFetchPricingLookup.mockResolvedValue({
      pricing: [],
      count: 0,
      product_id: 'p1',
      location: 'Evans CO',
      location_code: 'EVANS',
      location_locked: false,
      effective_date: null,
      source: 'test',
    })

    const mockResult: ReportGenerateResponse = {
      report_id: 'new-r1',
      download_url: 'https://mock.com/report.docx',
      status: 'complete',
      customer_name: 'Test Farm',
      operation_name: 'Test Op',
      products_included: 1,
      pricing_included: false,
      created_at: '2026-05-14',
    }
    mockGenerateReport.mockResolvedValue(mockResult)

    await renderNewReportForm()
    const user = userEvent.setup()

    // Step 1
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[0], 'Test Farm')
    await user.type(inputs[1], 'Test Op')
    fireEvent.change(screen.getByTestId('location-select'), { target: { value: 'EVANS' } })
    let nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Step 2: select a product
    await waitFor(() => expect(screen.getByText('Shield 52')).toBeInTheDocument())
    await user.click(screen.getByText('Shield 52'))
    nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Step 3: fill notes
    const findingsTA = screen.getByTestId('findings-textarea')
    const recsTA = screen.getByTestId('recs-textarea')
    await user.type(findingsTA, 'Good procedures overall.')
    await user.type(recsTA, 'Switch to better post-dip.')
    nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Step 4: generate
    const generateBtn = screen.getByTestId('generate-btn')
    await user.click(generateBtn)

    // Wait for success (goes through governance → writing → preparing → success)
    await waitFor(
      () => {
        expect(screen.getByText(/Your report for Test Op is ready!/)).toBeInTheDocument()
      },
      { timeout: 10000 },
    )

    // Download button should be present
    expect(screen.getByTestId('download-report-btn')).toBeInTheDocument()
  })

  test('shows governance error when API returns 400', async () => {
    mockFetchProducts.mockResolvedValue({
      products: MOCK_PRODUCTS,
      total_count: 2,
      has_more: false,
    })
    mockFetchPricingLookup.mockResolvedValue({
      pricing: [],
      count: 0,
      product_id: 'p1',
      location: 'Evans CO',
      location_code: 'EVANS',
      location_locked: false,
      effective_date: null,
      source: 'test',
    })

    // Mock API to throw a 400 governance error
    mockGenerateReport.mockRejectedValue(
      new Error("API 400: Product 'Shield 52' is not available at ULYSSES. Remove it and try again."),
    )

    await renderNewReportForm()
    const user = userEvent.setup()

    // Navigate through all steps
    const inputs = screen.getAllByRole('textbox')
    await user.type(inputs[0], 'Test Farm')
    await user.type(inputs[1], 'Test Op')
    fireEvent.change(screen.getByTestId('location-select'), { target: { value: 'EVANS' } })
    let nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    await waitFor(() => expect(screen.getByText('Shield 52')).toBeInTheDocument())
    await user.click(screen.getByText('Shield 52'))
    nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    await user.type(screen.getByTestId('findings-textarea'), 'Test findings')
    await user.type(screen.getByTestId('recs-textarea'), 'Test recs')
    nextBtn = screen.getByRole('button', { name: /next/i })
    await waitFor(() => expect(nextBtn).not.toBeDisabled())
    await user.click(nextBtn)

    // Generate
    await user.click(screen.getByTestId('generate-btn'))

    // Should show governance error
    await waitFor(
      () => {
        expect(screen.getByText('Product Not Available')).toBeInTheDocument()
      },
      { timeout: 10000 },
    )

    // Go back button should return to step 2
    expect(screen.getByText('Go Back to Product Selection')).toBeInTheDocument()
  })
})

describe('ShareReportModal', () => {
  test('shows confirmation before sharing', async () => {
    // Mock search returning a customer
    mockApiFetchRaw.mockResolvedValue({
      data: [
        {
          id: 'cust-1',
          email: 'customer@farm.com',
          full_name: 'John Farmer',
          customer_operation: 'Happy Valley Farm',
        },
      ],
      status: 200,
    })

    await renderShareModal()

    const user = userEvent.setup()

    // Search for customer
    const searchInput = screen.getByTestId('share-search-input')
    await user.type(searchInput, 'customer@farm')

    // Wait for result
    await waitFor(() => {
      expect(screen.getByText('John Farmer')).toBeInTheDocument()
    })

    // Click the customer
    await user.click(screen.getByTestId('customer-result'))

    // Should show confirmation
    await waitFor(() => {
      expect(screen.getByTestId('share-confirm')).toBeInTheDocument()
    })
    // Text is split across elements (<strong>NOT</strong>), use function matcher
    expect(
      screen.getByText((_content, element) => {
        return (
          element?.tagName === 'P' &&
          (element.textContent || '').includes('NOT') &&
          (element.textContent || '').includes('Bower Ag internal information')
        ) || false
      }),
    ).toBeInTheDocument()

    // Share button should be present
    expect(screen.getByTestId('share-confirm-btn')).toBeInTheDocument()
  })
})
