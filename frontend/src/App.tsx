/**
 * Bower Ag CowCare Tool — App Root
 * Mobile-first expert system for dairy cow care consulting.
 * Cow comfort is #1.
 */

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-[var(--color-navy)] text-white px-4 py-3 flex items-center gap-3">
        <div className="text-2xl">🐄</div>
        <div>
          <h1 className="text-lg font-bold leading-tight">CowCare Tool</h1>
          <p className="text-xs text-blue-200">Bower Ag Expert System</p>
        </div>
      </header>

      {/* Main Content — Sprint 0 placeholder */}
      <main className="p-4 max-w-lg mx-auto">
        <div className="bg-white rounded-xl shadow-sm border p-6 mt-4">
          <div className="text-center">
            <div className="text-5xl mb-4">🐄</div>
            <h2 className="text-xl font-bold text-[var(--color-navy)] mb-2">
              Bower Ag CowCare Tool
            </h2>
            <p className="text-gray-600 mb-4">
              Expert system for dairy cow care consulting.
              <br />
              <span className="font-medium text-[var(--color-accent)]">
                Cow comfort is always #1.
              </span>
            </p>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800">
              ✅ Frontend running — Sprint 0 complete.
              <br />
              Chat, products, and reports coming in future sprints.
            </div>
          </div>
        </div>

        {/* System Status */}
        <div className="mt-4 bg-white rounded-xl shadow-sm border p-4">
          <h3 className="font-semibold text-sm text-gray-700 mb-2">System Status</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Frontend</span>
              <span className="text-green-600 font-medium">● Running</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Backend API</span>
              <span className="text-yellow-600 font-medium">○ Connect .env</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Database</span>
              <span className="text-yellow-600 font-medium">○ Connect .env</span>
            </div>
          </div>
        </div>

        {/* Version footer */}
        <p className="text-center text-xs text-gray-400 mt-6">
          v0.0.1 · Sprint 0 · Project Foundation
        </p>
      </main>
    </div>
  )
}

export default App
