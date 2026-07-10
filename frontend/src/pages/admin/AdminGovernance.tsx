/**
 * AdminGovernance — Comprehensive governance management module
 *
 * Tabs:
 * 1. Audit — Run governance audits, detect bypasses
 * 2. Performance — Response time monitoring by domain
 * 3. Test Suite — GUI test runner for regression tests
 * 4. Documents — Upload, process, manage governance reference materials
 */

import { useState, useEffect, useCallback } from 'react'
import {
  governanceApi,
  type GovernanceAuditResult,
  type PerformanceResult,
  type PerformanceTrend,
  type TestRunResult,
  type GovernanceDocument,
  type DocumentStats,
  type DocumentChunk,
  type ProcessingStatus,
} from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Shield, Activity, FlaskConical, FileText, Loader2,
  AlertTriangle, CheckCircle2, XCircle, Clock, Upload,
  Trash2, RefreshCw, Eye, ChevronDown, ChevronRight,
  Play, Search, FileUp, BarChart3,
} from 'lucide-react'

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

type Tab = 'audit' | 'performance' | 'tests' | 'documents'

export function AdminGovernance() {
  const [activeTab, setActiveTab] = useState<Tab>('audit')

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'audit', label: 'Audit', icon: <Shield className="h-4 w-4" /> },
    { id: 'performance', label: 'Performance', icon: <Activity className="h-4 w-4" /> },
    { id: 'tests', label: 'Test Suite', icon: <FlaskConical className="h-4 w-4" /> },
    { id: 'documents', label: 'Documents', icon: <FileText className="h-4 w-4" /> },
  ]

  return (
    <div className="space-y-4 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-bold text-charcoal">Governance Center</h1>
        <p className="text-sm text-muted-foreground">
          Audit compliance, monitor performance, run tests, and manage reference materials.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 overflow-x-auto rounded-lg bg-muted p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-charcoal shadow-sm'
                : 'text-muted-foreground hover:text-charcoal'
            }`}
          >
            {tab.icon}
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'audit' && <AuditTab />}
      {activeTab === 'performance' && <PerformanceTab />}
      {activeTab === 'tests' && <TestSuiteTab />}
      {activeTab === 'documents' && <DocumentsTab />}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// AUDIT TAB
// ═══════════════════════════════════════════════════════════════════════════════

function AuditTab() {
  const [result, setResult] = useState<GovernanceAuditResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [days, setDays] = useState(7)
  const [domain, setDomain] = useState('')
  const [error, setError] = useState<string | null>(null)

  const runAudit = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await governanceApi.runAudit(days, domain || undefined)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audit failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 text-lg font-semibold text-charcoal">Governance Audit</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Scan for queries where governance data was missing on pricing/product domains — indicates the engine failed to inject context before Claude responded.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Time Window</label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="mt-1 block rounded-md border px-3 py-2 text-sm"
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Domain Filter</label>
            <select
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="mt-1 block rounded-md border px-3 py-2 text-sm"
            >
              <option value="">All governance domains</option>
              <option value="PRICING">Pricing</option>
              <option value="PRODUCTS">Products</option>
              <option value="TEAT_DIP">Teat Dip</option>
              <option value="CHEMICAL_CIP">Chemical CIP</option>
            </select>
          </div>
          <Button
            onClick={runAudit}
            disabled={loading}
            className="h-10 bg-barn-red text-white hover:bg-barn-red-light"
          >
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Search className="mr-2 h-4 w-4" />}
            Run Audit
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertTriangle className="mr-2 inline h-4 w-4" /> {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Total Queries" value={result.total_queries} />
            <StatCard
              label="Bypasses Found"
              value={result.bypasses_found}
              variant={result.bypasses_found > 0 ? 'danger' : 'success'}
            />
            <StatCard
              label="Bypass Rate"
              value={`${result.bypass_rate}%`}
              variant={result.bypass_rate > 5 ? 'danger' : result.bypass_rate > 0 ? 'warning' : 'success'}
            />
            <StatCard label="Window" value={`${result.time_window_days}d`} />
          </div>

          {/* Bypass List */}
          {result.bypasses.length > 0 && (
            <div className="rounded-lg border bg-white">
              <div className="border-b px-4 py-3">
                <h3 className="font-semibold text-charcoal">
                  Bypass Details ({result.bypasses.length})
                </h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                {result.bypasses.map((bypass) => (
                  <div key={bypass.id} className="border-b px-4 py-3 last:border-0">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-charcoal">{bypass.query_text}</p>
                        <div className="mt-1 flex flex-wrap gap-2">
                          <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                            {bypass.domain}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(bypass.created_at).toLocaleString()}
                          </span>
                        </div>
                        {bypass.response_summary && (
                          <p className="mt-1 text-xs text-muted-foreground">
                            Response: {bypass.response_summary}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {result.bypasses_found === 0 && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-center">
              <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-green-600" />
              <p className="font-medium text-green-800">No Governance Bypasses Detected</p>
              <p className="text-sm text-green-600">
                All {result.total_queries} queries in the last {result.time_window_days} days had proper governance data.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// PERFORMANCE TAB
// ═══════════════════════════════════════════════════════════════════════════════

function PerformanceTab() {
  const [result, setResult] = useState<PerformanceResult | null>(null)
  const [trends, setTrends] = useState<PerformanceTrend[]>([])
  const [loading, setLoading] = useState(false)
  const [days, setDays] = useState(7)
  const [error, setError] = useState<string | null>(null)

  const loadPerformance = async () => {
    setLoading(true)
    setError(null)
    try {
      const [perf, trendData] = await Promise.all([
        governanceApi.getPerformance(days),
        governanceApi.getPerformanceTrends(days),
      ])
      setResult(perf)
      setTrends(trendData.trends)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadPerformance() }, [])

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-end gap-3 rounded-lg border bg-white p-4">
        <div>
          <label className="text-xs font-medium text-muted-foreground">Time Window</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="mt-1 block rounded-md border px-3 py-2 text-sm"
          >
            <option value={1}>Last 24 hours</option>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </div>
        <Button onClick={loadPerformance} disabled={loading} variant="outline" className="h-10">
          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <AlertTriangle className="mr-2 inline h-4 w-4" /> {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {/* Overall Summary */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Avg Response" value={`${Math.round(result.overall_avg_ms)}ms`} />
            <StatCard label="P95 Response" value={`${Math.round(result.overall_p95_ms)}ms`} />
            <StatCard label="Total Queries" value={result.total_queries} />
            <StatCard
              label="Alerts"
              value={result.alert_domains.length}
              variant={result.alert_domains.length > 0 ? 'danger' : 'success'}
            />
          </div>

          {/* Alert Banner */}
          {result.alert_domains.length > 0 && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <p className="text-sm font-medium text-red-800">
                <AlertTriangle className="mr-1 inline h-4 w-4" />
                Performance Alert: {result.alert_domains.join(', ')} averaging &gt;5s
              </p>
            </div>
          )}

          {/* Domain Table */}
          <div className="rounded-lg border bg-white">
            <div className="border-b px-4 py-3">
              <h3 className="font-semibold text-charcoal">Response Time by Domain</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-2 text-left font-medium">Domain</th>
                    <th className="px-4 py-2 text-right font-medium">Avg</th>
                    <th className="px-4 py-2 text-right font-medium">P95</th>
                    <th className="px-4 py-2 text-right font-medium">Max</th>
                    <th className="px-4 py-2 text-right font-medium">Count</th>
                    <th className="px-4 py-2 text-right font-medium">&gt;5s</th>
                  </tr>
                </thead>
                <tbody>
                  {result.domains.map((d) => (
                    <tr key={d.domain} className="border-b last:border-0">
                      <td className="px-4 py-2 font-medium">{d.domain}</td>
                      <td className={`px-4 py-2 text-right ${d.avg_ms > 5000 ? 'font-bold text-red-600' : ''}`}>
                        {Math.round(d.avg_ms)}ms
                      </td>
                      <td className="px-4 py-2 text-right">{Math.round(d.p95_ms)}ms</td>
                      <td className="px-4 py-2 text-right">{Math.round(d.max_ms)}ms</td>
                      <td className="px-4 py-2 text-right">{d.count}</td>
                      <td className={`px-4 py-2 text-right ${d.over_5s_count > 0 ? 'text-red-600' : ''}`}>
                        {d.over_5s_count} ({d.over_5s_rate}%)
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Trends */}
          {trends.length > 0 && (
            <div className="rounded-lg border bg-white p-4">
              <h3 className="mb-3 font-semibold text-charcoal">Daily Trends</h3>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b">
                      <th className="px-2 py-1 text-left">Date</th>
                      <th className="px-2 py-1 text-left">Domain</th>
                      <th className="px-2 py-1 text-right">Avg (ms)</th>
                      <th className="px-2 py-1 text-right">Queries</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trends.slice(0, 50).map((t, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="px-2 py-1">{t.date}</td>
                        <td className="px-2 py-1">{t.domain}</td>
                        <td className={`px-2 py-1 text-right ${t.avg_ms > 5000 ? 'text-red-600 font-medium' : ''}`}>
                          {Math.round(t.avg_ms)}
                        </td>
                        <td className="px-2 py-1 text-right">{t.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// TEST SUITE TAB
// ═══════════════════════════════════════════════════════════════════════════════

function TestSuiteTab() {
  const [currentRun, setCurrentRun] = useState<TestRunResult | null>(null)
  const [history, setHistory] = useState<TestRunResult[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState('')
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadHistory = async () => {
    try {
      const data = await governanceApi.getTestHistory()
      setHistory(data.runs)
    } catch { /* ignore */ }
  }

  useEffect(() => { loadHistory() }, [])

  const startTests = async () => {
    setLoading(true)
    setError(null)
    try {
      const run = await governanceApi.runTests(filter || undefined)
      setCurrentRun(run)
      setPolling(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start tests')
    } finally {
      setLoading(false)
    }
  }

  // Poll for results
  useEffect(() => {
    if (!polling || !currentRun) return
    const interval = setInterval(async () => {
      try {
        const updated = await governanceApi.getTestRun(currentRun.run_id)
        setCurrentRun(updated)
        if (updated.status !== 'running') {
          setPolling(false)
          loadHistory()
        }
      } catch {
        setPolling(false)
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [polling, currentRun])

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="rounded-lg border bg-white p-4">
        <h2 className="mb-2 text-lg font-semibold text-charcoal">Governance Regression Tests</h2>
        <p className="mb-4 text-sm text-muted-foreground">
          Run the 10-test governance regression suite against the live Claude API.
          Each test verifies pricing, sellability, and domain classification behavior.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex-1">
            <label className="text-xs font-medium text-muted-foreground">Filter (optional)</label>
            <Input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="e.g., gr01, pricing, sellability"
              className="mt-1"
            />
          </div>
          <Button
            onClick={startTests}
            disabled={loading || polling}
            className="h-10 bg-barn-red text-white hover:bg-barn-red-light"
          >
            {loading || polling ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            {polling ? 'Running...' : 'Run Tests'}
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          <AlertTriangle className="mr-1 inline h-3 w-3" />
          Tests call the Claude API — each run consumes tokens. Average runtime: 2-4 minutes.
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Current Run Results */}
      {currentRun && (
        <div className="rounded-lg border bg-white">
          <div className="flex items-center justify-between border-b px-4 py-3">
            <div>
              <h3 className="font-semibold text-charcoal">
                Run: {currentRun.run_id}
                {currentRun.status === 'running' && (
                  <Loader2 className="ml-2 inline h-4 w-4 animate-spin text-accent" />
                )}
              </h3>
              <p className="text-xs text-muted-foreground">
                Started: {new Date(currentRun.started_at).toLocaleString()}
                {currentRun.duration_ms && ` — Duration: ${(currentRun.duration_ms / 1000).toFixed(1)}s`}
              </p>
            </div>
            <div className="flex gap-2">
              <span className="rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                {currentRun.passed} passed
              </span>
              {currentRun.failed > 0 && (
                <span className="rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                  {currentRun.failed} failed
                </span>
              )}
              {currentRun.skipped > 0 && (
                <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-700">
                  {currentRun.skipped} skipped
                </span>
              )}
            </div>
          </div>

          {/* Test Case List */}
          <div className="max-h-96 overflow-y-auto">
            {currentRun.test_cases.map((tc) => (
              <div key={tc.test_id} className="flex items-start gap-3 border-b px-4 py-2 last:border-0">
                <StatusIcon status={tc.status} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{tc.test_name}</p>
                  {tc.message && (
                    <p className="mt-0.5 text-xs text-muted-foreground">{tc.message}</p>
                  )}
                </div>
              </div>
            ))}
            {currentRun.test_cases.length === 0 && currentRun.status === 'running' && (
              <div className="p-4 text-center text-sm text-muted-foreground">
                Tests are running — results will appear here...
              </div>
            )}
          </div>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="rounded-lg border bg-white">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-charcoal">Recent Test Runs</h3>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {history.map((run) => (
              <div
                key={run.run_id}
                className="flex items-center justify-between border-b px-4 py-2 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium">{run.run_id}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(run.started_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-green-600">{run.passed}P</span>
                  {run.failed > 0 && <span className="text-xs text-red-600">{run.failed}F</span>}
                  {run.skipped > 0 && <span className="text-xs text-yellow-600">{run.skipped}S</span>}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setCurrentRun(run)}
                    className="h-7 text-xs"
                  >
                    View
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// DOCUMENTS TAB
// ═══════════════════════════════════════════════════════════════════════════════

function DocumentsTab() {
  const [documents, setDocuments] = useState<GovernanceDocument[]>([])
  const [stats, setStats] = useState<DocumentStats | null>(null)
  const [domains, setDomains] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterDomain, setFilterDomain] = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null)
  const [chunks, setChunks] = useState<DocumentChunk[]>([])
  const [processingJob, setProcessingJob] = useState<ProcessingStatus | null>(null)

  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const [docData, statsData] = await Promise.all([
        governanceApi.listDocuments(filterDomain || undefined),
        governanceApi.getDocumentStats(),
      ])
      setDocuments(docData.documents)
      setDomains(docData.domains)
      setStats(statsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [filterDomain])

  useEffect(() => { loadDocuments() }, [loadDocuments])

  const handleViewChunks = async (sourceDoc: string) => {
    if (expandedDoc === sourceDoc) {
      setExpandedDoc(null)
      setChunks([])
      return
    }
    try {
      const data = await governanceApi.getDocumentChunks(sourceDoc)
      setChunks(data.chunks)
      setExpandedDoc(sourceDoc)
    } catch { /* ignore */ }
  }

  const handleDelete = async (sourceDoc: string) => {
    if (!confirm(`Delete all chunks for "${sourceDoc}"? This removes it from the AI search index.`)) return
    try {
      await governanceApi.deleteDocument(sourceDoc)
      loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const handleReembed = async (sourceDoc: string) => {
    try {
      const result = await governanceApi.reembedDocument(sourceDoc)
      setProcessingJob({
        job_id: result.job_id,
        status: 'processing',
        filename: sourceDoc,
        chunks_created: 0,
        message: `Re-embedding ${result.chunk_count} chunks...`,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Re-embed failed')
    }
  }

  return (
    <div className="space-y-4">
      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Documents" value={stats.total_documents} />
          <StatCard label="Total Chunks" value={stats.total_chunks} />
          <StatCard label="Total Characters" value={`${Math.round(stats.total_chars / 1000)}K`} />
          <StatCard label="Domains" value={Object.keys(stats.by_domain).length} />
        </div>
      )}

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          className="rounded-md border px-3 py-2 text-sm"
        >
          <option value="">All domains</option>
          {domains.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <Button onClick={() => setShowUpload(!showUpload)} className="h-10 bg-barn-red text-white hover:bg-barn-red-light">
          <Upload className="mr-2 h-4 w-4" />
          Upload Document
        </Button>
        <Button onClick={loadDocuments} variant="outline" className="h-10">
          <RefreshCw className="mr-2 h-4 w-4" /> Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}

      {/* Upload Section */}
      {showUpload && (
        <UploadSection
          domains={domains}
          onComplete={() => { setShowUpload(false); loadDocuments() }}
          processingJob={processingJob}
          setProcessingJob={setProcessingJob}
        />
      )}

      {/* Processing Status */}
      {processingJob && processingJob.status === 'processing' && (
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
          <div className="flex items-center gap-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" />
            <span className="text-sm font-medium text-blue-800">{processingJob.message}</span>
          </div>
        </div>
      )}

      {/* Document List */}
      {loading ? (
        <div className="py-8 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="rounded-lg border bg-white">
          <div className="border-b px-4 py-3">
            <h3 className="font-semibold text-charcoal">
              Reference Documents ({documents.length})
            </h3>
          </div>
          {documents.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              <FileText className="mx-auto mb-2 h-8 w-8" />
              <p>No documents found. Upload governance materials to get started.</p>
            </div>
          ) : (
            <div className="divide-y">
              {documents.map((doc) => (
                <div key={doc.source_doc}>
                  <div className="flex items-center justify-between px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleViewChunks(doc.source_doc)}
                          className="flex items-center gap-1 text-sm font-medium text-charcoal hover:text-accent"
                        >
                          {expandedDoc === doc.source_doc ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                          {doc.source_doc}
                        </button>
                      </div>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
                          {doc.domain}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {doc.chunk_count} chunks · {Math.round(doc.total_chars / 1000)}K chars
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleViewChunks(doc.source_doc)}
                        title="View chunks"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleReembed(doc.source_doc)}
                        title="Re-embed"
                      >
                        <RefreshCw className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(doc.source_doc)}
                        title="Delete"
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Expanded Chunks */}
                  {expandedDoc === doc.source_doc && chunks.length > 0 && (
                    <div className="border-t bg-muted/30 px-4 py-2">
                      <p className="mb-2 text-xs font-medium text-muted-foreground">
                        Chunks ({chunks.length}):
                      </p>
                      <div className="max-h-64 space-y-2 overflow-y-auto">
                        {chunks.map((chunk) => (
                          <div key={chunk.id} className="rounded border bg-white p-2">
                            <p className="text-xs font-medium text-charcoal">{chunk.section_title}</p>
                            <p className="mt-1 text-xs text-muted-foreground line-clamp-3">
                              {chunk.content}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// UPLOAD SECTION
// ═══════════════════════════════════════════════════════════════════════════════

function UploadSection({
  domains,
  onComplete,
  processingJob,
  setProcessingJob,
}: {
  domains: string[]
  onComplete: () => void
  processingJob: ProcessingStatus | null
  setProcessingJob: (job: ProcessingStatus | null) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [domain, setDomain] = useState('general')
  const [uploading, setUploading] = useState(false)
  const [uploadedJobId, setUploadedJobId] = useState<string | null>(null)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const result = await governanceApi.uploadDocument(file, domain)
      setUploadedJobId(result.job_id)
      setStatusMessage(`Uploaded "${result.filename}" (${result.size_kb} KB). Ready to process.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleProcess = async () => {
    if (!uploadedJobId) return
    setProcessing(true)
    setError(null)
    try {
      await governanceApi.processDocument(uploadedJobId, domain)
      setStatusMessage('Processing started — extracting text, chunking, and embedding...')

      // Poll for status
      const pollInterval = setInterval(async () => {
        try {
          const status = await governanceApi.getProcessingStatus(uploadedJobId)
          setProcessingJob(status)
          setStatusMessage(status.message || 'Processing...')
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(pollInterval)
            setProcessing(false)
            if (status.status === 'completed') {
              setTimeout(() => onComplete(), 1500)
            }
          }
        } catch {
          clearInterval(pollInterval)
          setProcessing(false)
        }
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed')
      setProcessing(false)
    }
  }

  return (
    <div className="rounded-lg border bg-white p-4">
      <h3 className="mb-3 font-semibold text-charcoal">
        <FileUp className="mr-2 inline h-5 w-5" />
        Upload Governance Document
      </h3>
      <p className="mb-4 text-sm text-muted-foreground">
        Upload a PDF, DOCX, or text file. The system will extract text, split into searchable chunks,
        generate embeddings, and add to the governance knowledge base.
      </p>

      <div className="space-y-3">
        {/* File Input */}
        <div>
          <label className="text-xs font-medium text-muted-foreground">File</label>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt,.md,.csv"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="mt-1 block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-barn-red file:px-3 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-barn-red-light"
          />
        </div>

        {/* Domain */}
        <div>
          <label className="text-xs font-medium text-muted-foreground">Domain Classification</label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="mt-1 block w-full rounded-md border px-3 py-2 text-sm"
          >
            {domains.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <p className="mt-1 text-xs text-muted-foreground">
            Determines how the AI retrieves this content (e.g., pricing queries search "calculation" domain docs)
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {!uploadedJobId ? (
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="bg-barn-red text-white hover:bg-barn-red-light"
            >
              {uploading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
              Upload
            </Button>
          ) : (
            <Button
              onClick={handleProcess}
              disabled={processing}
              className="bg-green-600 text-white hover:bg-green-700"
            >
              {processing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4" />}
              Process & Embed
            </Button>
          )}
        </div>

        {/* Status */}
        {statusMessage && (
          <div className={`rounded-md p-2 text-sm ${
            processingJob?.status === 'completed'
              ? 'bg-green-50 text-green-700'
              : processingJob?.status === 'failed'
              ? 'bg-red-50 text-red-700'
              : 'bg-blue-50 text-blue-700'
          }`}>
            {statusMessage}
          </div>
        )}

        {error && (
          <div className="rounded-md bg-red-50 p-2 text-sm text-red-700">{error}</div>
        )}
      </div>
    </div>
  )
}


// ═══════════════════════════════════════════════════════════════════════════════
// SHARED COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

function StatCard({
  label,
  value,
  variant = 'default',
}: {
  label: string
  value: string | number
  variant?: 'default' | 'success' | 'warning' | 'danger'
}) {
  const colors = {
    default: 'bg-white',
    success: 'bg-green-50 border-green-200',
    warning: 'bg-yellow-50 border-yellow-200',
    danger: 'bg-red-50 border-red-200',
  }
  const textColors = {
    default: 'text-charcoal',
    success: 'text-green-700',
    warning: 'text-yellow-700',
    danger: 'text-red-700',
  }

  return (
    <div className={`rounded-lg border p-3 ${colors[variant]}`}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-bold ${textColors[variant]}`}>{value}</p>
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'passed':
      return <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
    case 'failed':
      return <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
    case 'skipped':
      return <Clock className="mt-0.5 h-4 w-4 shrink-0 text-yellow-600" />
    case 'error':
      return <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-600" />
    default:
      return <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-muted-foreground" />
  }
}
