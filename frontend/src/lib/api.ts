/**
 * Bower Ag CowCare Tool — API Client
 * Sprint 7: Typed fetch wrapper with Supabase auth token injection.
 *
 * All calls to the FastAPI backend go through this module.
 * Token is pulled from Supabase session automatically.
 */

import { supabase } from '@/lib/supabase'

const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '')

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ConversationRequest {
  message: string
  session_id?: string
  conversation_history: ConversationMessage[]
}

export interface ConversationResponse {
  reply: string
  domain: string
  location_locked: string | null
  governance_applied: boolean
  needs_location: boolean
  llm_called: boolean
  input_tokens: number | null
  output_tokens: number | null
}

export interface SetLocationRequest {
  location_code: string
  force?: boolean
}

export interface LocationResponse {
  location_code: string
  location_name: string
  previously_locked: string | null
  message: string
}

export interface FeedbackRequest {
  conversation_id?: string
  message_index?: number
  rating: -1 | 1
  comment?: string
  session_id?: string
}

export interface BugReportRequest {
  title: string
  what_happened: string
  expected_behavior?: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  conversation_id?: string
  session_id?: string
}

// ─── Helpers ────────────────────────────────────────────────────────────────

async function getAuthHeaders(sessionId?: string): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const { data: { session } } = await supabase.auth.getSession()
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  if (sessionId) {
    headers['X-Session-ID'] = sessionId
  }

  return headers
}

async function apiFetch<T>(
  path: string,
  options: {
    method?: string
    body?: unknown
    sessionId?: string
  } = {},
): Promise<T> {
  const { method = 'GET', body, sessionId } = options
  const headers = await getAuthHeaders(sessionId)

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${detail}`)
  }

  return res.json()
}

// ─── API Functions ──────────────────────────────────────────────────────────

export async function sendMessage(
  req: ConversationRequest,
  sessionId?: string,
): Promise<ConversationResponse> {
  return apiFetch<ConversationResponse>('/conversation', {
    method: 'POST',
    body: req,
    sessionId,
  })
}

export async function setLocation(
  req: SetLocationRequest,
  sessionId?: string,
): Promise<LocationResponse> {
  return apiFetch<LocationResponse>('/session/location', {
    method: 'POST',
    body: req,
    sessionId,
  })
}

export async function clearLocation(sessionId?: string): Promise<{ cleared: boolean }> {
  return apiFetch<{ cleared: boolean }>('/session/location', {
    method: 'DELETE',
    sessionId,
  })
}

export async function submitFeedback(req: FeedbackRequest): Promise<{ id: string; message: string }> {
  return apiFetch<{ id: string; message: string }>('/feedback', {
    method: 'POST',
    body: req,
  })
}

export async function submitBugReport(
  req: BugReportRequest,
  sessionId?: string,
): Promise<{ id: string; message: string }> {
  return apiFetch<{ id: string; message: string }>('/bugs', {
    method: 'POST',
    body: req,
    sessionId,
  })
}

// ─── Products API (Sprint 8) ────────────────────────────────────────────────

export interface ProductSummary {
  id: string
  product_name: string
  part_number: string | null
  category: string
  product_type: string
  chemistry_type: string | null
  germicide_type: string | null
  usage_timing: string | null
  is_concentrate: boolean
  emollient_pct: number | null
  emollient_type: string | null
  notes: string | null
  sds_verified: boolean
}

export interface ProductListResponse {
  products: ProductSummary[]
  total_count: number
  has_more: boolean
}

export interface SellabilityEntry {
  location_name: string
  branch_code: string
  sellable: boolean
}

export interface PricingEntry {
  container_size: string
  uom: string
  price_per_unit: number
  extended_price: number | null
}

export interface ProductDetailResponse extends ProductSummary {
  sellability: SellabilityEntry[]
  my_location_pricing: PricingEntry[]
}

export interface CategoryMetadata {
  categories: string[]
  chemistry_types: string[]
  product_types: string[]
}

export interface ProductListParams {
  search?: string
  category?: string
  chemistry?: string
  location_code?: string
  limit?: number
  offset?: number
}

export interface PricingLookupResponse {
  pricing: Array<{
    id: string
    product_id: string
    location_id: string
    container_size: string
    uom: string
    price_per_unit: number
    extended_price: number | null
    version: number
    effective_date: string
    superseded_date: string | null
  }>
  count: number
  product_id: string
  location: string
  location_code: string
  location_locked: boolean
  effective_date: string | null
  source: string
}

export async function fetchProducts(params: ProductListParams = {}): Promise<ProductListResponse> {
  const searchParams = new URLSearchParams()
  if (params.search) searchParams.set('search', params.search)
  if (params.category) searchParams.set('category', params.category)
  if (params.chemistry) searchParams.set('chemistry', params.chemistry)
  if (params.location_code) searchParams.set('location_code', params.location_code)
  if (params.limit) searchParams.set('limit', String(params.limit))
  if (params.offset) searchParams.set('offset', String(params.offset))

  const qs = searchParams.toString()
  return apiFetch<ProductListResponse>(`/products${qs ? `?${qs}` : ''}`)
}

export async function fetchProductDetail(productId: string): Promise<ProductDetailResponse> {
  return apiFetch<ProductDetailResponse>(`/products/${productId}`)
}

export async function fetchProductCategories(): Promise<CategoryMetadata> {
  return apiFetch<CategoryMetadata>('/products/categories')
}

export async function fetchPricingLookup(
  productId: string,
  locationCode: string,
): Promise<PricingLookupResponse> {
  const params = new URLSearchParams({
    product_id: productId,
    location_code: locationCode,
  })
  return apiFetch<PricingLookupResponse>(`/pricing/lookup?${params.toString()}`)
}

// ─── Reports API (Sprint 10) ──────────────────────────────────────────────

export interface ReportSummary {
  report_id: string
  customer_name: string
  operation_name: string
  location_code: string
  status: 'generating' | 'complete' | 'failed' | 'deleted'
  shared_with_customer: boolean
  created_at: string
}

export interface ReportDetailResponse {
  report_id: string
  customer_name: string
  operation_name: string
  location_code: string
  rep_name: string | null
  rep_title: string | null
  include_pricing: boolean
  status: string
  shared_with_customer: boolean
  shared_with_user_ids: string[] | null
  download_url: string | null
  created_at: string
  updated_at: string
}

export interface ReportGenerateRequest {
  customer_name: string
  operation_name: string
  location_code: string
  product_ids: string[]
  findings: string
  recommendations: string
  rep_name: string
  rep_title?: string
  include_pricing?: boolean
}

export interface ReportGenerateResponse {
  report_id: string
  download_url: string
  status: string
  customer_name: string
  operation_name: string
  products_included: number
  pricing_included: boolean
  created_at: string
}

export interface ShareReportRequest {
  customer_user_ids: string[]
}

export interface ShareReportResponse {
  report_id: string
  shared_with_user_ids: string[]
  message: string
}

export async function fetchReports(): Promise<ReportSummary[]> {
  return apiFetch<ReportSummary[]>('/reports')
}

export async function fetchReportDetail(reportId: string): Promise<ReportDetailResponse> {
  return apiFetch<ReportDetailResponse>(`/reports/${reportId}`)
}

export async function generateReport(req: ReportGenerateRequest): Promise<ReportGenerateResponse> {
  return apiFetch<ReportGenerateResponse>('/reports/generate', {
    method: 'POST',
    body: req,
  })
}

export async function shareReport(
  reportId: string,
  req: ShareReportRequest,
): Promise<ShareReportResponse> {
  return apiFetch<ShareReportResponse>(`/reports/${reportId}/share`, {
    method: 'POST',
    body: req,
  })
}

export async function deleteReport(reportId: string): Promise<{ report_id: string; status: string }> {
  return apiFetch<{ report_id: string; status: string }>(`/reports/${reportId}`, {
    method: 'DELETE',
  })
}

/** Fetch API error with status code preserved */
export async function apiFetchRaw<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<{ data?: T; error?: string; status: number }> {
  const { method = 'GET', body } = options
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    return { error: detail, status: res.status }
  }
  const data = await res.json()
  return { data, status: res.status }
}

// ─── Admin API Types (Sprint 12) ─────────────────────────────────────────────

// Analytics
export interface DomainCount {
  domain: string
  count: number
}

export interface LocationCount {
  location_locked: string
  count: number
}

export interface AnalyticsSummary {
  total_queries: number
  queries_today: number
  active_users: number
  queries_by_domain: DomainCount[]
  queries_by_location: LocationCount[]
  avg_response_ms: number
  governance_blocks: number
  claude_api_calls: number
  thumbs_up: number
  thumbs_down: number
  open_bugs: number
  open_critical_bugs: number
}

export interface TopProduct {
  product_name: string
  mention_count: number
}

export interface DailyUsage {
  date: string
  query_count: number
  active_users: number
}

// User Management
export interface AdminUserItem {
  id: string
  full_name: string | null
  email: string | null
  role: string
  location_name: string | null
  active: boolean
  created_at: string
}

export interface InviteUserRequest {
  email: string
  role: string
  location_id?: string
  full_name: string
}

export interface InviteUserResponse {
  user_id: string
  email: string
  role: string
  message: string
}

export interface UpdateUserRequest {
  role?: string
  location_id?: string
  full_name?: string
  active?: boolean
}

// System Config
export interface ConfigItem {
  key: string
  value: unknown
  description: string | null
  editable_by: string
  updated_by: string | null
  updated_at: string | null
}

// Bug Reports (Admin)
export interface AdminBugReport {
  id: string
  title: string
  description: string | null
  severity: string
  status: string
  version_tag: string | null
  reporter_name: string | null
  reporter_email: string | null
  steps_to_reproduce: string | null
  expected_behavior: string | null
  actual_behavior: string | null
  fix_notes: string | null
  resolved_at: string | null
  created_at: string
}

export interface BugUpdateRequest {
  status?: string
  fix_notes?: string
  severity?: string
}

// Version Log
export interface VersionLogItem {
  id: string
  version_tag: string
  release_date: string | null
  release_notes: string | null
  breaking_changes: string | null
  bugs_resolved: string[] | null
  deployed_by: string | null
  created_at: string
}

export interface CreateVersionRequest {
  version_tag: string
  release_notes?: string
  breaking_changes?: string
  bugs_resolved?: string[]
}

// Audit Log
export interface AuditLogEntry {
  id: string
  user_id: string | null
  user_name: string | null
  user_role: string | null
  action: string | null
  domain: string | null
  query_text: string | null
  governance_result: unknown
  location_locked: string | null
  duration_ms: number | null
  created_at: string
}

// ─── Admin API Functions (Sprint 12) ─────────────────────────────────────────

// Analytics
export async function fetchAnalyticsSummary(days = 7): Promise<AnalyticsSummary> {
  return apiFetch<AnalyticsSummary>(`/admin/analytics/summary?days=${days}`)
}

export async function fetchTopProducts(days = 7, limit = 10): Promise<TopProduct[]> {
  return apiFetch<TopProduct[]>(`/admin/analytics/top_products?days=${days}&limit=${limit}`)
}

export async function fetchUsageByDay(days = 30): Promise<DailyUsage[]> {
  return apiFetch<DailyUsage[]>(`/admin/analytics/usage_by_day?days=${days}`)
}

// User Management
export async function fetchAdminUsers(): Promise<AdminUserItem[]> {
  return apiFetch<AdminUserItem[]>('/admin/users')
}

export async function inviteUser(req: InviteUserRequest): Promise<InviteUserResponse> {
  return apiFetch<InviteUserResponse>('/admin/users', {
    method: 'POST',
    body: req,
  })
}

export async function updateUser(userId: string, req: UpdateUserRequest): Promise<AdminUserItem> {
  return apiFetch<AdminUserItem>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: req,
  })
}

export async function deactivateUser(userId: string): Promise<{ message: string }> {
  return apiFetch<{ message: string }>(`/admin/users/${userId}`, {
    method: 'DELETE',
  })
}

// System Config
export async function fetchAdminConfig(): Promise<ConfigItem[]> {
  return apiFetch<ConfigItem[]>('/admin/config')
}

export async function updateConfig(key: string, value: unknown): Promise<ConfigItem> {
  return apiFetch<ConfigItem>(`/admin/config/${key}`, {
    method: 'PATCH',
    body: { value },
  })
}

// Bug Reports (Admin)
export async function fetchAdminBugs(params: {
  severity?: string
  status?: string
  version_tag?: string
  days?: number
  search?: string
} = {}): Promise<AdminBugReport[]> {
  const sp = new URLSearchParams()
  if (params.severity) sp.set('severity', params.severity)
  if (params.status) sp.set('status', params.status)
  if (params.version_tag) sp.set('version_tag', params.version_tag)
  if (params.days) sp.set('days', String(params.days))
  if (params.search) sp.set('search', params.search)
  const qs = sp.toString()
  return apiFetch<AdminBugReport[]>(`/admin/bugs${qs ? `?${qs}` : ''}`)
}

export async function fetchAdminBugDetail(bugId: string): Promise<AdminBugReport> {
  return apiFetch<AdminBugReport>(`/admin/bugs/${bugId}`)
}

export async function updateAdminBug(bugId: string, req: BugUpdateRequest): Promise<AdminBugReport> {
  return apiFetch<AdminBugReport>(`/admin/bugs/${bugId}`, {
    method: 'PATCH',
    body: req,
  })
}

export function getAdminBugsExportUrl(params: {
  severity?: string
  status?: string
  version_tag?: string
  days?: number
  search?: string
} = {}): string {
  const sp = new URLSearchParams()
  if (params.severity) sp.set('severity', params.severity)
  if (params.status) sp.set('status', params.status)
  if (params.version_tag) sp.set('version_tag', params.version_tag)
  if (params.days) sp.set('days', String(params.days))
  if (params.search) sp.set('search', params.search)
  const qs = sp.toString()
  return `${API_URL}/admin/bugs/export${qs ? `?${qs}` : ''}`
}

// Version Log
export async function fetchAdminVersions(): Promise<VersionLogItem[]> {
  return apiFetch<VersionLogItem[]>('/admin/versions')
}

export async function createVersion(req: CreateVersionRequest): Promise<VersionLogItem> {
  return apiFetch<VersionLogItem>('/admin/versions', {
    method: 'POST',
    body: req,
  })
}

export function getVersionsExportUrl(): string {
  return `${API_URL}/admin/versions/export`
}

// Audit Log
export async function fetchAuditLog(params: {
  user_id?: string
  domain?: string
  action?: string
  start_date?: string
  end_date?: string
  limit?: number
} = {}): Promise<AuditLogEntry[]> {
  const sp = new URLSearchParams()
  if (params.user_id) sp.set('user_id', params.user_id)
  if (params.domain) sp.set('domain', params.domain)
  if (params.action) sp.set('action', params.action)
  if (params.start_date) sp.set('start_date', params.start_date)
  if (params.end_date) sp.set('end_date', params.end_date)
  if (params.limit) sp.set('limit', String(params.limit))
  const qs = sp.toString()
  return apiFetch<AuditLogEntry[]>(`/admin/audit${qs ? `?${qs}` : ''}`)
}

export function getAuditExportUrl(params: {
  user_id?: string
  domain?: string
  action?: string
  start_date?: string
  end_date?: string
} = {}): string {
  const sp = new URLSearchParams()
  if (params.user_id) sp.set('user_id', params.user_id)
  if (params.domain) sp.set('domain', params.domain)
  if (params.action) sp.set('action', params.action)
  if (params.start_date) sp.set('start_date', params.start_date)
  if (params.end_date) sp.set('end_date', params.end_date)
  const qs = sp.toString()
  return `${API_URL}/admin/audit/export${qs ? `?${qs}` : ''}`
}

// ─── Customer Portal API Types (Sprint 13) ──────────────────────────────────

export interface CustomerReportSummary {
  report_id: string
  operation_name: string
  rep_name: string | null
  created_at: string
  has_download: boolean
}

export interface CustomerReportDetail {
  report_id: string
  operation_name: string
  rep_name: string | null
  rep_title: string | null
  report_content: string | null
  download_url: string | null
  created_at: string
}

// ─── Customer Portal API Functions (Sprint 13) ──────────────────────────────

export async function fetchCustomerReports(): Promise<CustomerReportSummary[]> {
  return apiFetch<CustomerReportSummary[]>('/customer/reports')
}

export async function fetchCustomerReportDetail(reportId: string): Promise<CustomerReportDetail> {
  return apiFetch<CustomerReportDetail>(`/customer/reports/${reportId}`)
}

// ─── Media Pipeline API Types (Sprint 14) ────────────────────────────────────

export interface ImageAnalysisResponse {
  analysis: string
  domain: string
  image_url: string
  governance_applied: boolean
  teat_scores: number[] | null
}

export interface VideoUploadResponse {
  job_id: string
  status: string
  message: string
}

export interface MediaJobResponse {
  job_id: string
  status: string
  frames_extracted: number | null
  frames_analyzed: number | null
  result_report_id: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

// ─── Media Pipeline API Functions (Sprint 14) ────────────────────────────────

export async function analyzeImage(
  file: File,
  domain: string = 'general',
): Promise<ImageAnalysisResponse> {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  const formData = new FormData()
  formData.append('file', file)
  formData.append('domain', domain)

  const res = await fetch(`${API_URL}/media/analyze-image`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${detail}`)
  }

  return res.json()
}

export async function uploadVideo(file: File): Promise<VideoUploadResponse> {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: Record<string, string> = {}
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }

  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_URL}/media/analyze-video`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${detail}`)
  }

  return res.json()
}

export async function fetchMediaJob(jobId: string): Promise<MediaJobResponse> {
  return apiFetch<MediaJobResponse>(`/media/jobs/${jobId}`)
}

export async function checkFeatureEnabled(key: string): Promise<boolean> {
  try {
    const configs = await apiFetch<Array<{ key: string; value: unknown }>>('/admin/config')
    const config = configs.find((c) => c.key === key)
    if (!config) return false
    const val = config.value
    if (typeof val === 'boolean') return val
    if (typeof val === 'string') return val.toLowerCase() === 'true'
    return Boolean(val)
  } catch {
    return false
  }
}
