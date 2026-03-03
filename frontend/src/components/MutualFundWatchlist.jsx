import { useEffect, useState } from 'react'
import { onValue, ref, remove, set } from 'firebase/database'
import { db } from '../lib/firebase'
import { useAuth } from '../context/AuthContext'
import { getMutualFundNav } from '../services/api'

const MF_WATCHLIST_KEY = 'bharat_mf_watchlist'

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(MF_WATCHLIST_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return typeof parsed === 'object' && parsed !== null ? parsed : {}
  } catch {
    return {}
  }
}

function saveToStorage(obj) {
  try {
    localStorage.setItem(MF_WATCHLIST_KEY, JSON.stringify(obj))
  } catch (e) {
    console.error('[MF Watchlist] localStorage write failed:', e)
  }
}

export function useMutualFundWatchlist() {
  const { user } = useAuth()
  const uid = user?.uid

  const [localItems, setLocalItems] = useState(loadFromStorage)
  const [firebaseItems, setFirebaseItems] = useState({})

  useEffect(() => {
    if (!uid) return
    const wlRef = ref(db, `users/${uid}/mf_watchlist`)
    const unsub = onValue(
      wlRef,
      (snapshot) => {
        setFirebaseItems(snapshot.val() || {})
      },
      (error) => {
        console.error('[MF Watchlist] Firebase subscribe failed:', error)
      },
    )
    return () => unsub()
  }, [uid])

  // Merge local and Firebase so items always show up in UI
  const items = {
    ...localItems,
    ...(uid ? firebaseItems : {}),
  }

  const addToMfWatchlist = (scheme) => {
    if (!scheme?.scheme_code) {
      console.warn('[MF Watchlist] addToMfWatchlist: no scheme_code')
      return
    }
    const key = String(scheme.scheme_code)
    const entry = {
      scheme_code: key,
      scheme_name: scheme.scheme_name || '',
      fund_house: scheme.fund_house || '',
      scheme_type: scheme.scheme_type || '',
      addedAt: Date.now(),
    }

    if (uid) {
      const wlRef = ref(db, `users/${uid}/mf_watchlist/${key}`)
      set(wlRef, entry)
        .then(() => console.log('[MF Watchlist] Added to Firebase:', key, entry.scheme_name))
        .catch((e) => console.error('[MF Watchlist] Firebase add failed:', e))
    }

    const next = { ...localItems, [key]: entry }
    setLocalItems(next)
    saveToStorage(next)
    window.dispatchEvent(new CustomEvent('bharat-mf-watchlist-update'))
    console.log('[MF Watchlist] Added to localStorage:', key, entry.scheme_name)
  }

  const removeFromMfWatchlist = (schemeCode) => {
    if (!schemeCode) return
    const key = String(schemeCode)

    if (uid) {
      const wlRef = ref(db, `users/${uid}/mf_watchlist/${key}`)
      remove(wlRef)
        .then(() => console.log('[MF Watchlist] Removed from Firebase:', key))
        .catch((e) => console.error('[MF Watchlist] Firebase remove failed:', e))
    }

    const next = { ...localItems }
    delete next[key]
    setLocalItems(next)
    saveToStorage(next)
    window.dispatchEvent(new CustomEvent('bharat-mf-watchlist-update'))
    console.log('[MF Watchlist] Removed from localStorage:', key)
  }

  useEffect(() => {
    if (uid) return
    const handler = () => {
      setLocalItems(loadFromStorage())
    }
    window.addEventListener('bharat-mf-watchlist-update', handler)
    return () => window.removeEventListener('bharat-mf-watchlist-update', handler)
  }, [uid])

  return { addToMfWatchlist, removeFromMfWatchlist, items }
}

function MutualFundWatchlist({ onSelectScheme }) {
  const { addToMfWatchlist, removeFromMfWatchlist, items } = useMutualFundWatchlist()
  const [navs, setNavs] = useState({})
  const [loading, setLoading] = useState(false)

  const entries = Object.entries(items || {})

  const schemeCodes = Object.keys(items || {}).sort().join(',')
  useEffect(() => {
    if (!schemeCodes) {
      setNavs({})
      return
    }
    setLoading(true)
    const load = async () => {
      const codes = schemeCodes ? schemeCodes.split(',') : []
      try {
        const results = await Promise.all(
          codes.map(async (code) => {
            try {
              const nav = await getMutualFundNav(code)
              return { code, nav }
            } catch (e) {
              console.warn('[MF Watchlist] NAV fetch failed for', code, e?.message)
              return { code, nav: null }
            }
          }),
        )
        const next = {}
        results.forEach(({ code, nav }) => {
          next[code] = nav
        })
        setNavs(next)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [schemeCodes])

  const changeColor = (val) => {
    if (val == null || val === undefined) return 'text-slate-600'
    const n = typeof val === 'number' ? val : parseFloat(val)
    if (Number.isNaN(n)) return 'text-slate-600'
    if (n > 0) return 'text-bharat-green'
    if (n < 0) return 'text-red-600'
    return 'text-slate-600'
  }

  const handleRemove = (e, code) => {
    e.stopPropagation()
    removeFromMfWatchlist(code)
  }

  return (
    <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg overflow-hidden flex flex-col h-full">
      <div className="bg-bharat-navy px-4 py-3 border-b border-bharat-navy/60">
        <h3 className="text-sm font-semibold text-white flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <span className="text-bharat-saffron">★</span>
            <span>MF Watchlist</span>
          </span>
          <span className="text-[10px] text-bharat-green/80 uppercase tracking-wide">
            NAV Tracker
          </span>
        </h3>
      </div>

      <div className="flex-1 px-4 py-3 space-y-3 overflow-y-auto max-h-[450px] scrollbar-thin scrollbar-track-transparent scrollbar-thumb-slate-300">
        {entries.length === 0 && (
          <div className="text-center px-2 py-6">
            <p className="text-sm font-medium text-slate-700 mb-1">
              Your watchlist is empty. Add a fund to get started!
            </p>
          </div>
        )}

        {entries.length > 0 && (
          <ul className="space-y-2">
            {entries.map(([code, meta]) => {
              const nav = navs[code]
              return (
                <li
                  key={code}
                  className="group flex items-center justify-between gap-2 py-2 border-b border-slate-100 last:border-0 cursor-pointer hover:bg-slate-50 rounded-lg px-3 -mx-3 transition-colors bg-white"
                  onClick={() =>
                    onSelectScheme?.({
                      scheme_code: code,
                      scheme_name: meta.scheme_name,
                      fund_house: meta.fund_house,
                      scheme_type: meta.scheme_type,
                    })
                  }
                >
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-semibold text-slate-900 truncate">
                      {meta.scheme_name}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate">
                      {meta.fund_house || code}
                    </div>
                  </div>
                  <div className="text-right shrink-0 mr-1">
                    {loading && !nav ? (
                      <span className="text-xs text-slate-400">…</span>
                    ) : nav ? (
                      <>
                        <div className="text-xs font-semibold text-slate-900">
                          <span className="text-bharat-green">NAV</span>{' '}
                          <span className="text-bharat-green">₹{nav.nav}</span>
                        </div>
                        {nav.change_percent != null && (
                          <div
                            className={`text-[10px] font-medium ${changeColor(
                              nav.change_percent,
                            )}`}
                          >
                            {nav.change_percent >= 0 ? '+' : ''}
                            {nav.change_percent}%
                          </div>
                        )}
                      </>
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={(e) => handleRemove(e, code)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-full text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors shrink-0"
                    title="Remove from MF watchlist"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.8}
                        d="M6 7h12M10 11v6m4-6v6M9 7l1-2h4l1 2m-8 0v11a2 2 0 002 2h6a2 2 0 002-2V7"
                      />
                    </svg>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="px-4 py-3 border-t border-slate-200 bg-slate-50">
        <p className="text-[11px] text-slate-600 leading-snug">
          <span className="font-semibold text-bharat-navy">ⓘ MF Watchlist:</span>{' '}
          Track NAV movements of your favourite mutual funds. Synced securely via BharatFinanceAI cloud.
        </p>
      </div>
    </div>
  )
}

export default MutualFundWatchlist
