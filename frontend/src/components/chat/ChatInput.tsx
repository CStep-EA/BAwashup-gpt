/**
 * ChatInput — Auto-expanding textarea with send button + file attachment
 * Sprint 7: Enter on desktop = send. Enter on mobile = newline.
 * Sprint 14: Paperclip button for image/video attachment, file preview.
 * Send button: blue circle, arrow icon, 48px tap target.
 * 16px font-size minimum for iOS.
 */

import { useRef, useEffect, useCallback } from 'react'
import { ArrowUp, Loader2, Paperclip, X, Image as ImageIcon, Video } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatInputProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled?: boolean
  loading?: boolean
  placeholder?: string
  /** Sprint 14: file attachment callback */
  onFileSelect?: (file: File) => void
  /** Sprint 14: currently selected file */
  selectedFile?: File | null
  /** Sprint 14: clear selected file */
  onFileClear?: () => void
  /** Sprint 14: whether media attachments are enabled */
  mediaEnabled?: boolean
}

function isMobile(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
}

const ACCEPTED_TYPES = 'image/jpeg,image/png,image/heic,image/webp,video/mp4,video/quicktime,video/x-msvideo'
const IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/heic', 'image/webp'])
const VIDEO_TYPES = new Set(['video/mp4', 'video/quicktime', 'video/x-msvideo'])
const MAX_IMAGE_MB = 10
const MAX_VIDEO_MB = 500

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled = false,
  loading = false,
  placeholder = 'Ask about products, pricing, or troubleshooting…',
  onFileSelect,
  selectedFile,
  onFileClear,
  mediaEnabled = false,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Auto-resize textarea (max 4 lines then scroll)
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    const lineHeight = 24 // ~16px * 1.5
    const maxHeight = lineHeight * 4 + 24 // 4 lines + padding
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`
    el.style.overflowY = el.scrollHeight > maxHeight ? 'auto' : 'hidden'
  }, [])

  useEffect(() => {
    adjustHeight()
  }, [value, adjustHeight])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Desktop: Enter to send, Shift+Enter for newline
    // Mobile: Enter always newline (send only via button)
    if (e.key === 'Enter' && !e.shiftKey && !isMobile()) {
      e.preventDefault()
      if (canSend) {
        onSend()
      }
    }
  }

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !onFileSelect) return

    // Validate type
    if (!IMAGE_TYPES.has(file.type) && !VIDEO_TYPES.has(file.type)) {
      alert('Please select a JPEG, PNG, HEIC, WebP image or MP4, MOV, AVI video.')
      e.target.value = ''
      return
    }

    // Validate size
    const isImage = IMAGE_TYPES.has(file.type)
    const maxBytes = (isImage ? MAX_IMAGE_MB : MAX_VIDEO_MB) * 1024 * 1024
    if (file.size > maxBytes) {
      alert(`File must be under ${isImage ? MAX_IMAGE_MB : MAX_VIDEO_MB}MB.`)
      e.target.value = ''
      return
    }

    onFileSelect(file)
    e.target.value = '' // Reset so same file can be selected again
  }, [onFileSelect])

  const handlePaperclipClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const canSend = (value.trim().length > 0 || !!selectedFile) && !loading && !disabled

  const isImage = selectedFile ? IMAGE_TYPES.has(selectedFile.type) : false

  return (
    <div className="border-t bg-white p-3">
      <div className="mx-auto max-w-3xl">
        {/* File preview */}
        {selectedFile && (
          <div className="mb-2 flex items-center gap-2 rounded-lg border bg-gray-50 px-3 py-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent/10">
              {isImage ? (
                <ImageIcon className="h-4 w-4 text-accent" />
              ) : (
                <Video className="h-4 w-4 text-accent" />
              )}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-navy">
                {selectedFile.name}
              </p>
              <p className="text-[10px] text-muted-foreground">
                {formatFileSize(selectedFile.size)}
                {!isImage && ' — Video will be processed in the background'}
              </p>
            </div>
            <button
              onClick={onFileClear}
              className="tap-target flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-gray-400 transition-colors hover:bg-gray-200 hover:text-gray-600"
              aria-label="Remove file"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Input row */}
        <div className="flex items-end gap-2">
          {/* Paperclip button — only when media is enabled */}
          {mediaEnabled && onFileSelect && (
            <button
              onClick={handlePaperclipClick}
              disabled={disabled || loading}
              className={cn(
                'tap-target flex h-12 w-12 shrink-0 items-center justify-center rounded-full transition-all',
                disabled || loading
                  ? 'text-gray-200'
                  : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600 active:scale-95',
              )}
              aria-label="Attach image or video"
            >
              <Paperclip className="h-5 w-5" />
            </button>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_TYPES}
            onChange={handleFileChange}
            className="hidden"
            aria-hidden="true"
          />

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            placeholder={selectedFile ? 'Add a note (optional)…' : placeholder}
            rows={1}
            className={cn(
              'flex-1 resize-none rounded-xl border bg-gray-50 px-4 py-3 text-sm leading-relaxed outline-none transition-colors',
              'placeholder:text-gray-400',
              'focus:border-accent focus:bg-white focus:ring-2 focus:ring-accent/20',
              'disabled:cursor-not-allowed disabled:opacity-50',
            )}
            style={{ fontSize: '16px', minHeight: '48px' }}
          />

          <button
            onClick={onSend}
            disabled={!canSend}
            className={cn(
              'tap-target flex h-12 w-12 shrink-0 items-center justify-center rounded-full transition-all',
              canSend
                ? 'bg-accent text-white shadow-sm hover:bg-accent-hover active:scale-95'
                : 'bg-gray-100 text-gray-300'
            )}
            aria-label="Send message"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <ArrowUp className="h-5 w-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
