/**
 * Bower Ag CowCare Tool — App Router
 * Sprint 14: Added media job status route.
 *
 * Route structure:
 *   /login              — Public (LoginPage)
 *   /offline            — Public (OfflinePage)
 *
 *   [AuthGuard]         — All routes below require authentication
 *
 *     [CustomerLayout]  — Customer-only routes (no Sidebar/BottomNav)
 *       /my-reports               — CustomerReportsPage
 *       /my-reports/:reportId     — CustomerReportViewPage
 *
 *     [AppLayout]       — Staff routes (Sidebar + BottomNav)
 *
 *       [CustomerGuard] — Redirects customers to /my-reports
 *         /             — DashboardPage
 *         /chat         — ChatPage
 *         /products     — ProductsPage
 *         /reports      — ReportsPage
 *         /reports/:reportId/preview — ReportPreviewPage
 *         /media/jobs/:jobId — MediaJobStatusPage
 *         /settings     — SettingsPage
 *
 *       [RoleGuard: org_admin, admin]
 *         /admin        — AdminDashboard
 *         /admin/users  — AdminUsers
 *         /admin/config — AdminConfig
 *         /admin/bugs   — AdminBugs
 *         /admin/versions — AdminVersions
 *         /admin/audit  — AuditLogPage (org_admin only in nav)
 *
 *   *                   — NotFoundPage (catch-all)
 */

import { Routes, Route } from 'react-router-dom'

// Guards
import { AuthGuard } from '@/components/guards/AuthGuard'
import { RoleGuard } from '@/components/guards/RoleGuard'
import { CustomerGuard } from '@/components/guards/CustomerGuard'

// Layouts
import { AppLayout } from '@/components/layout/AppLayout'
import { CustomerLayout } from '@/layouts/CustomerLayout'

// Public pages
import { LoginPage } from '@/pages/LoginPage'
import { OfflinePage } from '@/pages/OfflinePage'
import { NotFoundPage } from '@/pages/NotFoundPage'

// App pages (staff)
import { DashboardPage } from '@/pages/DashboardPage'
import { ChatPage } from '@/pages/ChatPage'
import { ProductLookupPage } from '@/pages/ProductLookupPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { ReportPreviewPage } from '@/pages/ReportPreviewPage'
import { SettingsPage } from '@/pages/SettingsPage'

// Customer pages
import { CustomerReportsPage } from '@/pages/customer/CustomerReportsPage'
import { CustomerReportViewPage } from '@/pages/customer/CustomerReportViewPage'

// Media pages (Sprint 14)
import { MediaJobStatusPage } from '@/pages/media/MediaJobStatusPage'

// Admin pages
import { AdminDashboard } from '@/pages/admin/AdminDashboard'
import { AdminUsers } from '@/pages/admin/AdminUsers'
import { AdminConfig } from '@/pages/admin/AdminConfig'
import { AdminBugs } from '@/pages/admin/AdminBugs'
import { AdminVersions } from '@/pages/admin/AdminVersions'
import { AuditLogPage } from '@/pages/admin/AuditLogPage'

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/offline" element={<OfflinePage />} />

      {/* Authenticated routes */}
      <Route element={<AuthGuard />}>

        {/* ── Customer portal — simplified layout, no nav ────────── */}
        <Route element={<CustomerLayout />}>
          <Route path="my-reports" element={<CustomerReportsPage />} />
          <Route path="my-reports/:reportId" element={<CustomerReportViewPage />} />
        </Route>

        {/* ── Staff routes — full layout with Sidebar + BottomNav ── */}
        <Route element={<AppLayout />}>
          {/* Non-customer routes — customers get redirected to /my-reports */}
          <Route element={<CustomerGuard />}>
            <Route index element={<DashboardPage />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="products" element={<ProductLookupPage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="reports/:reportId/preview" element={<ReportPreviewPage />} />
            <Route path="media/jobs/:jobId" element={<MediaJobStatusPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>

          {/* Admin routes — org_admin and admin only, shows 403 for others */}
          <Route
            element={
              <RoleGuard allowedRoles={['org_admin', 'admin']} />
            }
          >
            <Route path="admin" element={<AdminDashboard />} />
            <Route path="admin/users" element={<AdminUsers />} />
            <Route path="admin/config" element={<AdminConfig />} />
            <Route path="admin/bugs" element={<AdminBugs />} />
            <Route path="admin/versions" element={<AdminVersions />} />
            <Route path="admin/audit" element={<AuditLogPage />} />
          </Route>
        </Route>
      </Route>

      {/* 404 catch-all */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
