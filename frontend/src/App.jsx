import Stock from './components/Stock'
import Chat from './components/Chat'

function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {/* Navbar */}
      <nav className="border-b-2 border-slate-200 bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-xl bg-orange-100 border border-orange-300 flex items-center justify-center">
                <span className="text-orange-500 font-bold text-lg">₹</span>
              </div>
              <div>
                <h1 className="text-xl font-semibold tracking-tight text-slate-900">
                  BharatFinanceAI
                </h1>
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                  Indian Markets Intelligence
                </p>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Dashboard */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <Stock />
        <Chat />
      </main>
    </div>
  )
}

export default App
