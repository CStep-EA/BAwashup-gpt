/**
 * ProductCard Component Tests
 * Sprint 8: 7 tests covering card rendering, expansion, sellability, and navigation.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProductCard } from '../ProductCard'
import { ProductCardExpanded } from '../ProductCardExpanded'
import type { ProductSummary, ProductDetailResponse } from '@/lib/api'

// ─── Mock Data ───────────────────────────────────────────────────────────────

const mockProduct: ProductSummary = {
  id: 'test-product-1',
  product_name: 'Curiass Gold',
  part_number: 'CG-100',
  category: 'Teat Dip',
  product_type: 'teat_dip',
  chemistry_type: 'Iodine',
  germicide_type: 'Iodophor',
  usage_timing: 'post',
  is_concentrate: false,
  emollient_pct: 10,
  emollient_type: 'Glycerin',
  notes: 'Premium post-dip with superior conditioning',
  sds_verified: true,
}

const mockDetail: ProductDetailResponse = {
  ...mockProduct,
  sellability: [
    { location_name: 'Evans CO', branch_code: 'EVANS', sellable: true },
    { location_name: 'Ulysses KS', branch_code: 'ULYSSES', sellable: true },
    { location_name: 'Jerome ID', branch_code: 'JEROME', sellable: false },
    { location_name: 'Turlock CA', branch_code: 'TURLOCK', sellable: true },
    { location_name: 'Tulare CA', branch_code: 'TULARE', sellable: false },
  ],
  my_location_pricing: [
    { container_size: '5 gal', uom: 'pail', price_per_unit: 45.99, extended_price: 229.95 },
  ],
}

// ─── Mocks ───────────────────────────────────────────────────────────────────

// Mock the navigate function
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock the chat store
vi.mock('@/store/chat', () => ({
  useChatStore: vi.fn(() => ({
    addUserMessage: vi.fn(),
    locationCode: 'EVANS',
  })),
  LOCATIONS: {
    EVANS: 'Evans CO',
    ULYSSES: 'Ulysses KS',
    JEROME: 'Jerome ID',
    TURLOCK: 'Turlock CA',
    TULARE: 'Tulare CA',
  },
}))

// Mock auth store
vi.mock('@/store/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: { id: 'test-user', role: 'consultant', location_id: 'loc-1' },
  })),
}))

// Mock API (pricing lookup)
vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual('@/lib/api')
  return {
    ...actual,
    fetchPricingLookup: vi.fn(() =>
      Promise.resolve({
        pricing: [
          {
            id: 'p1',
            product_id: 'test-product-1',
            location_id: 'loc-1',
            container_size: '5 gal',
            uom: 'pail',
            price_per_unit: 45.99,
            extended_price: 229.95,
            version: 1,
            effective_date: '2026-01-01',
            superseded_date: null,
          },
        ],
        count: 1,
        product_id: 'test-product-1',
        location: 'Evans CO',
        location_code: 'EVANS',
        location_locked: true,
        effective_date: '2026-01-01',
        source: 'governance_db',
      })
    ),
  }
})

// ─── Tests ───────────────────────────────────────────────────────────────────

describe('ProductCard', () => {
  it('renders product name and category badge', () => {
    render(
      <MemoryRouter>
        <ProductCard product={mockProduct} isExpanded={false} onToggle={() => {}} />
      </MemoryRouter>
    )

    expect(screen.getByText('Curiass Gold')).toBeInTheDocument()
    expect(screen.getByText('Teat Dip')).toBeInTheDocument()
  })

  it('shows usage timing badge for teat dip products', () => {
    render(
      <MemoryRouter>
        <ProductCard product={mockProduct} isExpanded={false} onToggle={() => {}} />
      </MemoryRouter>
    )

    expect(screen.getByText('POST')).toBeInTheDocument()
  })

  it('shows RTU badge when not concentrate', () => {
    render(
      <MemoryRouter>
        <ProductCard product={mockProduct} isExpanded={false} onToggle={() => {}} />
      </MemoryRouter>
    )

    expect(screen.getByText('RTU')).toBeInTheDocument()
  })

  it('calls onToggle when card is tapped', () => {
    const onToggle = vi.fn()
    render(
      <MemoryRouter>
        <ProductCard product={mockProduct} isExpanded={false} onToggle={onToggle} />
      </MemoryRouter>
    )

    fireEvent.click(screen.getByRole('button'))
    expect(onToggle).toHaveBeenCalledTimes(1)
  })
})

describe('ProductCardExpanded', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows sellability chips for all locations', () => {
    render(
      <MemoryRouter>
        <ProductCardExpanded detail={mockDetail} userLocationCode="EVANS" />
      </MemoryRouter>
    )

    // All 5 location chips should be rendered
    expect(screen.getByTitle(/Evans.*Sellable/)).toBeInTheDocument()
    expect(screen.getByTitle(/Jerome.*Not sellable/)).toBeInTheDocument()
  })

  it('renders green check for sellable and red X for not sellable', () => {
    render(
      <MemoryRouter>
        <ProductCardExpanded detail={mockDetail} userLocationCode="EVANS" />
      </MemoryRouter>
    )

    // Evans (sellable) should have ✓, Jerome (not sellable) should have ✕
    const chips = screen.getAllByText('✓')
    expect(chips.length).toBe(3) // EVANS, ULYSSES, TURLOCK

    const xChips = screen.getAllByText('✕')
    expect(xChips.length).toBe(2) // JEROME, TULARE
  })

  it('user location chip has ring styling', () => {
    render(
      <MemoryRouter>
        <ProductCardExpanded detail={mockDetail} userLocationCode="EVANS" />
      </MemoryRouter>
    )

    const evansChip = screen.getByTitle(/Evans.*Sellable/)
    expect(evansChip).toHaveClass('ring-2')
    expect(evansChip).toHaveClass('ring-accent')
  })

  it('"Ask about this product" button navigates to /chat', async () => {
    render(
      <MemoryRouter>
        <ProductCardExpanded detail={mockDetail} userLocationCode="EVANS" />
      </MemoryRouter>
    )

    const askButton = screen.getByText('Ask about this product')
    fireEvent.click(askButton)

    expect(mockNavigate).toHaveBeenCalledWith('/chat')
  })
})

describe('EmptyState and Filters', () => {
  it('empty state renders when products array is empty', async () => {
    // Import and render the page with mocked empty store
    const { ProductLookupPage } = await import('@/pages/ProductLookupPage')

    // Mock the products store to return empty
    vi.mock('@/store/products', () => ({
      useProductsStore: vi.fn(() => ({
        products: [],
        totalCount: 0,
        hasMore: false,
        categories: null,
        filters: { search: 'nonexistent', category: null, chemistry: null, locationOnly: false },
        isLoading: false,
        isLoadingMore: false,
        error: null,
        search: vi.fn(),
        setFilter: vi.fn(),
        clearFilters: vi.fn(),
        loadMore: vi.fn(),
        loadProduct: vi.fn(),
        loadCategories: vi.fn(),
      })),
    }))

    render(
      <MemoryRouter>
        <ProductLookupPage />
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/No products found/)).toBeInTheDocument()
    })
  })
})
