/**
 * SubmitFeedbackPage — Public feedback/bug submission form
 * Any authenticated user can submit a bug, feature request, or suggestion.
 * Accessible via /feedback route and footer shortcut link.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Bug, Lightbulb, MessageSquarePlus, Check, ArrowLeft } from 'lucide-react'
import { submitFeedbackBug } from '@/lib/api'

const CATEGORIES = [
  { value: 'bug', label: 'Bug Report', icon: Bug, description: "Something isn't working right" },
  { value: 'feature', label: 'Feature Request', icon: Lightbulb, description: "I'd like a new feature" },
  { value: 'suggestion', label: 'Suggestion', icon: MessageSquarePlus, description: 'General feedback or idea' },
]

const SEVERITY_OPTIONS = [
  { value: 'low', label: 'Low', description: 'Minor issue, workaround exists' },
  { value: 'medium', label: 'Medium', description: 'Impacts workflow but not blocking' },
  { value: 'high', label: 'High', description: 'Significantly impacts my work' },
  { value: 'critical', label: 'Critical', description: "Can't do my job without this fix" },
]

export function SubmitFeedbackPage() {
  const navigate = useNavigate()

  const [category, setCategory] = useState('bug')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState('medium')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) return
    setSubmitting(true)
    setError(null)

    try {
      await submitFeedbackBug({
        title: `[${category}] ${title.trim()}`,
        what_happened: description.trim(),
        severity,
      })
      setSuccess(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="mx-auto max-w-lg p-4 pt-8">
        <Card>
          <CardContent className="flex flex-col items-center py-10 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
              <Check className="h-7 w-7 text-green-600" />
            </div>
            <h2 className="mt-4 text-lg font-bold text-navy">Thanks for your feedback!</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              We've received your {category === 'bug' ? 'bug report' : category === 'feature' ? 'feature request' : 'suggestion'}.
              Our team will review it shortly.
            </p>
            <div className="mt-6 flex gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setSuccess(false)
                  setTitle('')
                  setDescription('')
                  setSeverity('medium')
                }}
              >
                Submit Another
              </Button>
              <Button
                className="bg-accent text-white hover:bg-accent/90"
                onClick={() => navigate(-1)}
              >
                Go Back
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-lg p-4 pt-4">
      {/* Header */}
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="rounded-lg p-2 hover:bg-gray-100"
          aria-label="Go back"
        >
          <ArrowLeft className="h-5 w-5 text-navy" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-navy">Submit Feedback</h1>
          <p className="text-xs text-muted-foreground">
            Report a bug, request a feature, or share a suggestion
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="space-y-4 p-4">
          {/* Category selection */}
          <div>
            <label className="mb-2 block text-xs font-semibold text-muted-foreground">
              What type of feedback?
            </label>
            <div className="grid grid-cols-3 gap-2">
              {CATEGORIES.map((cat) => {
                const Icon = cat.icon
                const isSelected = category === cat.value
                return (
                  <button
                    key={cat.value}
                    onClick={() => setCategory(cat.value)}
                    className={`flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 text-center transition-all ${
                      isSelected
                        ? 'border-accent bg-accent/5 text-accent'
                        : 'border-gray-200 text-muted-foreground hover:border-gray-300'
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                    <span className="text-xs font-medium">{cat.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted-foreground">
              Title
            </label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={
                category === 'bug'
                  ? 'Brief summary of the issue…'
                  : category === 'feature'
                  ? 'What feature would you like?'
                  : "What's your suggestion?"
              }
              className="text-base"
            />
          </div>

          {/* Description */}
          <div>
            <label className="mb-1 block text-xs font-semibold text-muted-foreground">
              {category === 'bug' ? 'What happened?' : 'Details'}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={
                category === 'bug'
                  ? 'Describe what went wrong. Include steps to reproduce if possible…'
                  : 'Provide as much detail as you can…'
              }
              className="w-full rounded-lg border bg-white px-3 py-2.5 text-base min-h-[120px] resize-y focus:border-accent focus:ring-2 focus:ring-accent/20 outline-none"
            />
          </div>

          {/* Severity (visible for bugs) */}
          {category === 'bug' && (
            <div>
              <label className="mb-1 block text-xs font-semibold text-muted-foreground">
                Severity
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full rounded-lg border bg-white px-3 py-2.5 text-sm"
              >
                {SEVERITY_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label} — {s.description}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Submit */}
          <Button
            className="w-full gap-2 bg-accent text-white hover:bg-accent/90"
            onClick={handleSubmit}
            disabled={submitting || !title.trim() || !description.trim()}
          >
            {submitting ? 'Submitting…' : 'Submit Feedback'}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
