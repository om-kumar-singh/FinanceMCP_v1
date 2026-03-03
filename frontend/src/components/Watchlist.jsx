import { useEffect, useState } from 'react'
import { ref, onValue, set, remove } from 'firebase/database'
import { db } from '../lib/firebase'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'

function Watchlist({ onSelectStock, refreshTrigger }) {
  const { user } = useAuth()
  const uid = user?.uid
  const [watchlist, setWatchlist] = useState({})
  const [prices, setPrices] = useState({})
  const [loadingPrices, setLoadingPrices] = useState(false)

  useEffect(() => {
    if (!uid) return
    const wlRef = ref(db, `users/${uid}/watchlist`)
    const unsub = onValue(wlRef, (snapshot) => {
      setWatchlist(snapshot.val() || {})
    })
    return () => unsub()
  }, [uid])

  useEffect(() => {
    const items = Object.values(watchlist)
    const symbols = items.map((item) => item?.symbol).filter(Boolean)
    if (symbols.length === 0) return

    setLoadingPrices(true)
    const promises = symbols.map((sym) =>
      api.get(`/stock/${encodeURIComponent(sym)}`).then((r) => ({ sym, data: r.data })).catch(() => ({ sym, data: null }))
    )
    Promise.all(promises).then((results) => {
      const next = {}
      results.forEach(({ sym, data }) => {
        next[sym] = data ? { price: data.price, change: data.change, change_percent: data.change_percent } : null
      })
      setPrices(next)
      setLoadingPrices(false)
    })
  }, [watchlist, refreshTrigger])

  const entries = Object.entries(watchlist)
  const changeColor = (val) => {
    if (val == null || val === undefined) return 'text-slate-600'
    const n = typeof val === 'number' ? val : parseFloat(val)
    if (Number.isNaN(n)) return 'text-slate-600'
    if (n > 0) return 'text-bharat-green'
    if (n < 0) return 'text-red-600'
    return 'text-slate-600'
  }

  if (!uid) return null

  return (
    <div className="bg-white rounded-xl border-2 border-bharat-navy/30 p-4">
      <h3 className="text-sm font-semibold text-bharat-navy mb-3 flex items-center gap-2">
        <span>★</span> Watchlist
      </h3>

      {entries.length === 0 && (
        <p className="text-xs text-slate-500 italic">
          Start by searching for a stock like RELIANCE or HDFCBANK to add to your watchlist!
        </p>
      )}

      {entries.length > 0 && (
        <ul className="space-y-2">
          {entries.map(([key, meta]) => {
            const symbol = meta?.symbol || key
            const p = prices[symbol]
            return (
              <li
                key={key}
                className="flex items-center justify-between gap-2 py-2 border-b border-slate-100 last:border-0 cursor-pointer hover:bg-slate-50 rounded-lg px-2 -mx-2 transition-colors"
                onClick={() => onSelectStock?.({ symbol, company_name: meta?.name })}
              >
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium text-slate-900 truncate">{meta?.name || symbol.replace('.NS', '')}</div>
                  <div className="text-[10px] text-slate-500">{symbol}</div>
                </div>
                <div className="text-right shrink-0">
                  {loadingPrices ? (
                    <span className="text-xs text-slate-400">…</span>
                  ) : p ? (
                    <>
                      <div className="text-xs font-semibold text-slate-900">₹{p.price?.toLocaleString()}</div>
                      <div className={`text-[10px] font-medium ${changeColor(p.change_percent)}`}>
                        {p.change_percent >= 0 ? '+' : ''}{p.change_percent}%
                      </div>
                    </>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export function useWatchlist() {
  const { user } = useAuth()
  const uid = user?.uid

  const addToWatchlist = (symbol, name) => {
    if (!uid || !symbol) return
    const safeKey = symbol.replace(/\./g, '_')
    const wlRef = ref(db, `users/${uid}/watchlist/${safeKey}`)
    set(wlRef, { symbol, name: name || symbol, addedAt: Date.now() })
  }

  const removeFromWatchlist = (symbol) => {
    if (!uid || !symbol) return
    const safeKey = symbol.replace(/\./g, '_')
    const wlRef = ref(db, `users/${uid}/watchlist/${safeKey}`)
    remove(wlRef)
  }

  return { addToWatchlist, removeFromWatchlist }
}

export default Watchlist
