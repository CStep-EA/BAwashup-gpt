/**
 * Bower Ag CowCare Tool — Products Store (Zustand)
 * Sprint 8: Product catalog state with search, filters, pagination, caching.
 *
 * Cache: product detail results cached for 5 minutes to avoid re-fetching on re-expand.
 */

import { create } from 'zustand'
import type {
  ProductSummary,
  ProductDetailResponse,
  CategoryMetadata,
  ProductListParams,
} from '@/lib/api'
import {
  fetchProducts,
  fetchProductDetail,
  fetchProductCategories,
} from '@/lib/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ProductFilters {
  search: string
  category: string | null
  chemistry: string | null
  locationOnly: boolean
}

interface DetailCache {
  data: ProductDetailResponse
  cachedAt: number
}

interface ProductsState {
  // Data
  products: ProductSummary[]
  totalCount: number
  hasMore: boolean
  categories: CategoryMetadata | null

  // Filters
  filters: ProductFilters

  // UI state
  isLoading: boolean
  isLoadingMore: boolean
  error: string | null

  // Detail cache (5 min TTL)
  detailCache: Record<string, DetailCache>

  // Actions
  search: (params?: { resetOffset?: boolean }) => Promise<void>
  setFilter: (key: keyof ProductFilters, value: string | boolean | null) => void
  clearFilters: () => void
  loadMore: () => Promise<void>
  loadProduct: (productId: string) => Promise<ProductDetailResponse | null>
  loadCategories: () => Promise<void>
}

// ─── Constants ───────────────────────────────────────────────────────────────

const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes
const PAGE_SIZE = 25

const DEFAULT_FILTERS: ProductFilters = {
  search: '',
  category: null,
  chemistry: null,
  locationOnly: false,
}

// ─── Store ───────────────────────────────────────────────────────────────────

export const useProductsStore = create<ProductsState>((set, get) => ({
  products: [],
  totalCount: 0,
  hasMore: false,
  categories: null,
  filters: { ...DEFAULT_FILTERS },
  isLoading: false,
  isLoadingMore: false,
  error: null,
  detailCache: {},

  search: async (params = {}) => {
    const { resetOffset = true } = params
    const state = get()
    const { filters } = state

    set({ isLoading: true, error: null })

    const apiParams: ProductListParams = {
      limit: PAGE_SIZE,
      offset: resetOffset ? 0 : state.products.length,
    }

    if (filters.search.trim()) {
      apiParams.search = filters.search.trim()
    }
    if (filters.category) {
      apiParams.category = filters.category
    }
    if (filters.chemistry) {
      apiParams.chemistry = filters.chemistry
    }
    if (filters.locationOnly) {
      // Use user's location from auth store (profile has location_id)
      const { useAuthStore } = await import('@/store/auth')
      const authState = useAuthStore.getState()
      const locationCode = authState.locationCode || null
      if (locationCode) {
        apiParams.location_code = locationCode
      }
    }

    try {
      const result = await fetchProducts(apiParams)
      set({
        products: resetOffset ? result.products : [...state.products, ...result.products],
        totalCount: result.total_count,
        hasMore: result.has_more,
        isLoading: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load products',
        isLoading: false,
      })
    }
  },

  setFilter: (key, value) => {
    set((state) => ({
      filters: { ...state.filters, [key]: value },
    }))
    // Auto-search on filter change
    get().search({ resetOffset: true })
  },

  clearFilters: () => {
    set({ filters: { ...DEFAULT_FILTERS } })
    get().search({ resetOffset: true })
  },

  loadMore: async () => {
    const state = get()
    if (state.isLoadingMore || !state.hasMore) return

    set({ isLoadingMore: true })

    const apiParams: ProductListParams = {
      limit: PAGE_SIZE,
      offset: state.products.length,
    }

    const { filters } = state
    if (filters.search.trim()) apiParams.search = filters.search.trim()
    if (filters.category) apiParams.category = filters.category
    if (filters.chemistry) apiParams.chemistry = filters.chemistry

    try {
      const result = await fetchProducts(apiParams)
      set({
        products: [...state.products, ...result.products],
        totalCount: result.total_count,
        hasMore: result.has_more,
        isLoadingMore: false,
      })
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load more products',
        isLoadingMore: false,
      })
    }
  },

  loadProduct: async (productId: string) => {
    const state = get()
    const cached = state.detailCache[productId]

    // Return cached if still valid
    if (cached && Date.now() - cached.cachedAt < CACHE_TTL_MS) {
      return cached.data
    }

    try {
      const detail = await fetchProductDetail(productId)
      set((s) => ({
        detailCache: {
          ...s.detailCache,
          [productId]: { data: detail, cachedAt: Date.now() },
        },
      }))
      return detail
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : 'Failed to load product detail',
      })
      return null
    }
  },

  loadCategories: async () => {
    try {
      const categories = await fetchProductCategories()
      set({ categories })
    } catch {
      // Non-critical — filters just won't have dynamic values
    }
  },
}))
