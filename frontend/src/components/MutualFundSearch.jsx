import { useEffect, useState } from 'react'
import { getMutualFundNav } from '../services/api'
import { useMutualFundWatchlist } from './MutualFundWatchlist'

function MutualFundSearch({ onSelectFund }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedCode, setSelectedCode] = useState(null)
  const [nav, setNav] = useState(null)
  const [navLoading, setNavLoading] = useState(false)
  const [navError, setNavError] = useState(null)

  const { addToMfWatchlist } = useMutualFundWatchlist()

  // const fallbackFunds = [
  //   {
  //     scheme_code: '118834',
  //     scheme_name: 'SBI Bluechip Fund - Regular Plan - Growth',
  //     fund_house: 'SBI Mutual Fund',
  //     scheme_type: 'Equity Large Cap',
  //   },
  //   {
  //     scheme_code: '120503',
  //     scheme_name: 'ICICI Prudential Bluechip Fund - Growth',
  //     fund_house: 'ICICI Prudential Mutual Fund',
  //     scheme_type: 'Equity Large Cap',
  //   },
  //   {
  //     scheme_code: '119551',
  //     scheme_name: 'HDFC Top 100 Fund - Growth',
  //     fund_house: 'HDFC Mutual Fund',
  //     scheme_type: 'Equity Large Cap',
  //   },
  //   {
  //     scheme_code: '100027',
  //     scheme_name: 'UTI Nifty 50 Index Fund - Growth',
  //     fund_house: 'UTI Mutual Fund',
  //     scheme_type: 'Index Fund',
  //   },
  //   {
  //     scheme_code: '120716',
  //     scheme_name: 'Mirae Asset Large Cap Fund - Regular Plan - Growth',
  //     fund_house: 'Mirae Asset Mutual Fund',
  //     scheme_type: 'Equity Large Cap',
  //   },
  // ]

  // Debounced search for Google-style autocomplete
  useEffect(() => {
    const trimmed = query.trim()
    if (!trimmed || trimmed.length < 2) {
      setResults([])
      return
    }

    setLoading(true)

    const handle = setTimeout(async () => {
      try {
        const mfApiBase = import.meta.env.VITE_MFAPI_BASE_URL || 'https://api.mfapi.in'
        const res = await fetch(`${mfApiBase}/mf/search?q=${encodeURIComponent(trimmed)}`)
        if (!res.ok) {
          console.error('mfapi.in search failed with status', res.status)
          setResults([])
          return
        }
        const data = await res.json()
        if (Array.isArray(data) && data.length > 0) {
          const normalized = data.map((item) => ({
            scheme_code: String(item.schemeCode || item.scheme_code),
            scheme_name: item.schemeName || item.scheme_name,
            fund_house: item.fundHouse || item.fund_house || '',
            scheme_type: item.schemeType || item.scheme_type || '',
          }))
          setResults(normalized)
        } else {
          // Empty result: no mock fallback; keep results empty
          setResults([])
        }
      } catch (err) {
        console.error('MF search error:', err)
        // Hard fallback disabled; only API-fetched data is shown
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => clearTimeout(handle)
  }, [query])

  useEffect(() => {
    if (!selectedCode) return
    const loadNav = async () => {
      setNavLoading(true)
      setNavError(null)
      try {
        const data = await getMutualFundNav(selectedCode)
        if (data) {
          setNav(data)
        } else {
          console.warn('[MutualFundSearch] NAV API returned empty for scheme:', selectedCode)
          setNavError('No NAV data available for this scheme.')
        }
      } catch (err) {
        const msg = err?.response?.data?.detail || err?.message || 'Unknown error'
        const status = err?.response?.status
        console.error('[MutualFundSearch] NAV fetch failed:', {
          schemeCode: selectedCode,
          status,
          message: msg,
          fullError: err,
        })
        setNavError(status === 404 ? msg : 'Unable to fetch NAV right now.')
      } finally {
        setNavLoading(false)
      }
    }
    loadNav()
  }, [selectedCode])

  const handleSelect = (fund) => {
    setSelectedCode(fund.scheme_code)
    setQuery(fund.scheme_name || fund.scheme_code)
    setNav(null)
    setNavError(null)
    onSelectFund?.(fund)
  }

  const handleAddToWatchlist = () => {
    if (!nav && !selectedCode) return
    const fromResults = results.find((r) => r.scheme_code === selectedCode)
    const mf = fromResults || nav
      ? {
          scheme_code: selectedCode,
          scheme_name: fromResults?.scheme_name || nav?.scheme_name || '',
          fund_house: fromResults?.fund_house || '',
          scheme_type: fromResults?.scheme_type || '',
        }
      : { scheme_code: selectedCode, scheme_name: '', fund_house: '', scheme_type: '' }
    addToMfWatchlist(mf)
    console.log('[MutualFundSearch] Add to MF Watchlist:', mf.scheme_code, mf.scheme_name)
  }

  const changeColor = (val) => {
    if (val == null || val === undefined) return 'text-slate-700'
    const n = typeof val === 'number' ? val : parseFloat(val)
    if (Number.isNaN(n)) return 'text-slate-700'
    if (n > 0) return 'text-bharat-green'
    if (n < 0) return 'text-red-600'
    return 'text-slate-700'
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center">
        <div className="relative w-full">
          <span className="absolute inset-y-0 left-2 flex items-center pointer-events-none text-slate-400">
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-4.35-4.35M10.5 17a6.5 6.5 0 100-13 6.5 6.5 0 000 13z"
              />
            </svg>
          </span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search mutual funds (e.g. HDFC Tax Saver)"
            className="w-full rounded-lg border-2 border-slate-300 pl-8 pr-16 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-bharat-saffron focus:border-bharat-saffron"
          />
          {query && (
            <button
              type="button"
              onClick={() => {
                setQuery('')
                setResults([])
                setSelectedCode(null)
                setNav(null)
                setNavError(null)
              }}
              className="absolute inset-y-0 right-7 flex items-center text-slate-400 hover:text-slate-600"
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
          {loading && (
            <div className="absolute inset-y-0 right-2 flex items-center">
              <span className="w-3 h-3 border-2 border-bharat-saffron border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      </div>

      {results.length > 0 && (
        <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white max-h-64 overflow-y-auto">
          {results.map((fund) => (
            <button
              key={fund.scheme_code}
              type="button"
              onClick={() => handleSelect(fund)}
              className="w-full text-left px-3 py-2.5 text-xs hover:bg-slate-50 flex flex-col gap-0.5"
            >
              <span className="font-semibold text-slate-900 truncate">
                {fund.scheme_name}
              </span>
              <span className="text-[10px] text-slate-500 truncate">
                {fund.fund_house} • {fund.scheme_type} • {fund.scheme_code}
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-4 space-y-3">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h3 className="text-sm font-semibold text-bharat-navy">NAV Details</h3>
            <p className="text-[11px] text-slate-500">
              Select a mutual fund to view its latest NAV and daily change.
            </p>
          </div>
          <button
            type="button"
            onClick={handleAddToWatchlist}
            disabled={!selectedCode}
            className="px-2 py-1 rounded-full border border-bharat-saffron text-[11px] text-bharat-saffron hover:bg-bharat-saffron hover:text-bharat-navy disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Add to MF Watchlist
          </button>
        </div>

        {navLoading && (
          <p className="text-xs text-slate-500">Fetching latest NAV…</p>
        )}

        {navError && (
          <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md px-2 py-1">
            {navError}
          </p>
        )}

        {nav && !navError && (
          <div className="space-y-2 text-xs">
            <div className="pb-1 border-b border-slate-200">
              <div className="text-sm font-semibold text-slate-900">
                {nav.scheme_name}
              </div>
              <div className="text-[10px] text-slate-500">
                Scheme Code: {nav.scheme_code} • As of {nav.date}
              </div>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-200">
              <span className="text-slate-600">NAV</span>
              <span className="font-semibold text-slate-900">₹{nav.nav}</span>
            </div>
            {nav.change != null && nav.change_percent != null && (
              <div className="flex justify-between py-1 border-b border-slate-200">
                <span className="text-slate-600">Daily Change</span>
                <span className={`font-semibold ${changeColor(nav.change_percent)}`}>
                  {nav.change >= 0 ? '+' : ''}
                  {nav.change} ({nav.change_percent}%)
                </span>
              </div>
            )}
            <p className="text-[11px] text-slate-600 mt-1">
              <span className="font-semibold text-bharat-navy">ⓘ NAV:</span>{' '}
              NAV (Net Asset Value) represents the per-unit market value of the fund&apos;s
              assets minus its liabilities.
            </p>
          </div>
        )}

        {!nav && !navLoading && !navError && null}
      </div>
    </div>
  )
}

export default MutualFundSearch

