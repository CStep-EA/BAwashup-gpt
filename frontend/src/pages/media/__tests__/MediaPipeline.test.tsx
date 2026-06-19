/**
 * Media Pipeline Frontend Tests — Sprint 14
 * 8 tests for ChatInput (paperclip), ChatPage (media handlers),
 * and MediaJobStatusPage.
 *
 * Uses Vitest + React Testing Library with mocked API calls.
 */

import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import type { MediaJobResponse } from '@/lib/api'

// ─── Mocks ───────────────────────────────────────────────────────────────────

// Mock the API module
vi.mock('@/lib/api', () => ({
  sendMessage: vi.fn(),
  submitFeedback: vi.fn(),
  clearLocation: vi.fn(),
  analyzeImage: vi.fn(),
  uploadVideo: vi.fn(),
  fetchMediaJob: vi.fn(),
  checkFeatureEnabled: vi.fn(),
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
  fetchMediaJob,
  checkFeatureEnabled,
} from '@/lib/api'

// Typed mocks
const mockFetchMediaJob = vi.mocked(fetchMediaJob)
const mockCheckFeatureEnabled = vi.mocked(checkFeatureEnabled)

// ─── Setup ───────────────────────────────────────────────────────────────────

async function setMockConsultantProfile() {
  const { useAuthStore } = await import('@/store/auth')
  useAuthStore.setState({
    user: { id: 'consultant1', email: 'rep@bowerag.test' },
    profile: {
      id: 'consultant1',
      full_name: 'Jane Smith',
      role: 'consultant',
      location_id: 'loc-001',
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
  vi.useFakeTimers({ shouldAdvanceTime: true })
  await setMockConsultantProfile()
})

afterEach(() => {
  vi.useRealTimers()
})

// ─── Helpers ─────────────────────────────────────────────────────────────────

function createMockFile(name: string, type: string, sizeKB: number = 1): File {
  const data = new Uint8Array(sizeKB * 1024)
  return new File([data], name, { type })
}

// ─────────────────────────────────────────────────────────────────────────────
// ChatInput Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('ChatInput — Media Attachment', () => {
  test('shows paperclip button when mediaEnabled is true', async () => {
    const { ChatInput } = await import('@/components/chat/ChatInput')

    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        mediaEnabled={true}
        onFileSelect={vi.fn()}
        selectedFile={null}
        onFileClear={vi.fn()}
      />,
    )

    expect(screen.getByLabelText('Attach image or video')).toBeInTheDocument()
  })

  test('hides paperclip button when mediaEnabled is false', async () => {
    const { ChatInput } = await import('@/components/chat/ChatInput')

    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        mediaEnabled={false}
        onFileSelect={vi.fn()}
        selectedFile={null}
        onFileClear={vi.fn()}
      />,
    )

    expect(screen.queryByLabelText('Attach image or video')).not.toBeInTheDocument()
  })

  test('shows file preview when selectedFile is set', async () => {
    const { ChatInput } = await import('@/components/chat/ChatInput')
    const mockFile = createMockFile('cow_teats.jpg', 'image/jpeg', 500)

    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        mediaEnabled={true}
        onFileSelect={vi.fn()}
        selectedFile={mockFile}
        onFileClear={vi.fn()}
      />,
    )

    // File name visible
    expect(screen.getByText('cow_teats.jpg')).toBeInTheDocument()
    // File size visible
    expect(screen.getByText(/500\.0 KB/)).toBeInTheDocument()
    // Remove button
    expect(screen.getByLabelText('Remove file')).toBeInTheDocument()
  })

  test('canSend is true when only a file is selected (no text)', async () => {
    const { ChatInput } = await import('@/components/chat/ChatInput')
    const onSend = vi.fn()
    const mockFile = createMockFile('image.jpg', 'image/jpeg')

    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSend={onSend}
        mediaEnabled={true}
        onFileSelect={vi.fn()}
        selectedFile={mockFile}
        onFileClear={vi.fn()}
      />,
    )

    // Send button should be enabled (blue) even with empty text
    const sendButton = screen.getByLabelText('Send message')
    expect(sendButton).not.toBeDisabled()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// ChatPage — Media Feature Flag
// ─────────────────────────────────────────────────────────────────────────────

describe('ChatPage — Media Feature Flag', () => {
  test('checks feature flag on mount for eligible role', async () => {
    mockCheckFeatureEnabled.mockResolvedValue(true)

    // Reset chat store
    const { useChatStore } = await import('@/store/chat')
    useChatStore.setState({ messages: [], sessionId: 'test-session' })

    const { ChatPage } = await import('@/pages/ChatPage')

    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    )

    // Wait for initial skeleton + feature check
    await waitFor(() => {
      expect(mockCheckFeatureEnabled).toHaveBeenCalledWith('feature.video_upload')
    })
  })

  test('does not check feature flag for customer role', async () => {
    await setMockCustomerProfile()
    mockCheckFeatureEnabled.mockResolvedValue(false)

    const { useChatStore } = await import('@/store/chat')
    useChatStore.setState({ messages: [], sessionId: 'test-session' })

    const { ChatPage } = await import('@/pages/ChatPage')

    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>,
    )

    // Wait past the skeleton timer
    await act(async () => {
      vi.advanceTimersByTime(500)
    })

    // Customer role should not trigger feature check
    expect(mockCheckFeatureEnabled).not.toHaveBeenCalled()
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// MediaJobStatusPage Tests
// ─────────────────────────────────────────────────────────────────────────────

describe('MediaJobStatusPage', () => {
  const MOCK_PROCESSING_JOB: MediaJobResponse = {
    job_id: 'job-001',
    status: 'processing',
    frames_extracted: 15,
    frames_analyzed: 8,
    result_report_id: null,
    error_message: null,
    created_at: '2026-05-15T10:00:00+00:00',
    completed_at: null,
  }

  const MOCK_COMPLETE_JOB: MediaJobResponse = {
    job_id: 'job-002',
    status: 'complete',
    frames_extracted: 30,
    frames_analyzed: 30,
    result_report_id: 'report-xyz',
    error_message: null,
    created_at: '2026-05-15T10:00:00+00:00',
    completed_at: '2026-05-15T10:05:00+00:00',
  }

  async function renderJobStatusPage(jobId: string) {
    const { MediaJobStatusPage } = await import('@/pages/media/MediaJobStatusPage')
    return render(
      <MemoryRouter initialEntries={[`/media/jobs/${jobId}`]}>
        <Routes>
          <Route path="/media/jobs/:jobId" element={<MediaJobStatusPage />} />
        </Routes>
      </MemoryRouter>,
    )
  }

  test('shows processing status with frame counts', async () => {
    mockFetchMediaJob.mockResolvedValue(MOCK_PROCESSING_JOB)

    await renderJobStatusPage('job-001')

    await waitFor(() => {
      expect(screen.getByText('Analyzing')).toBeInTheDocument()
    })

    // Frame progress
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('Frames Extracted')).toBeInTheDocument()
    expect(screen.getByText('Frames Analyzed')).toBeInTheDocument()

    // Polling indicator
    expect(screen.getByText(/Auto-refreshing/)).toBeInTheDocument()
  })

  test('shows complete status with View Report link', async () => {
    mockFetchMediaJob.mockResolvedValue(MOCK_COMPLETE_JOB)

    await renderJobStatusPage('job-002')

    await waitFor(() => {
      expect(screen.getByText('Complete')).toBeInTheDocument()
    })

    // View Report link
    const reportLink = screen.getByText('View Report')
    expect(reportLink).toBeInTheDocument()
    expect(reportLink.closest('a')).toHaveAttribute('href', '/reports/report-xyz/preview')

    // No polling indicator for completed jobs
    expect(screen.queryByText(/Auto-refreshing/)).not.toBeInTheDocument()
  })
})
