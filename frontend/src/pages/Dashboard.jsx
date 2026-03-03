import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../services/api'
import StockSearch from '../components/StockSearch'
import Chat from '../components/Chat'
import Watchlist, { useWatchlist } from '../components/Watchlist'
import RSIGauge from '../components/RSIGauge'
import MACDGauge from '../components/MACDGauge'

const TABS = [
  { id: 'market', label: 'Market View' },
  { id: 'technical', label: 'Technical Analysis' },
  { id: 'ai', label: 'AI Advisor' },
]

function Dashboard() {
  const location = useLocation()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('market')
  const [toast, setToast] = useState(location.state?.toast || null)
  const { addToWatchlist } = useWatchlist()

  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE.NS')
  const [selectedName, setSelectedName] = useState('Reliance Industries Limited')
  const [stockData, setStockData] = useState(null)
  const [rsiData, setRsiData] = useState(null)
  const [macdData, setMacdData] = useState(null)

  const [loading, setLoading] = useState(false)
  const [stockError, setStockError] = useState(null)
  const [rsiError, setRsiError] = useState(null)
  const [macdError, setMacdError] = useState(null)
  const [watchlistRefresh, setWatchlistRefresh] = useState(0)

  useEffect(() => {
    const nextToast = location.state?.toast
    if (nextToast) {
      setToast(nextToast)
      navigate(location.pathname, { replace: true, state: {} })
    }
  }, [location.state, location.pathname, navigate])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 2500)
    return () => clearTimeout(t)
  }, [toast])

  const changeColor = (value) => {
    if (value === null || value === undefined) return 'text-slate-700'
    const num = typeof value === 'number' ? value : parseFloat(value)
    if (Number.isNaN(num)) return 'text-slate-700'
    if (num > 0) return 'text-bharat-green'
    if (num < 0) return 'text-red-600'
    return 'text-slate-700'
  }

  const rsiSignalColor = (signal) => {
    if (!signal) return 'text-slate-700'
    const n = signal.toLowerCase()
    if (n === 'overbought') return 'text-red-600'
    if (n === 'oversold') return 'text-bharat-green'
    if (n === 'neutral') return 'text-amber-600'
    return 'text-slate-700'
  }

  const macdTrendColor = (trend) => {
    if (!trend) return 'text-slate-700'
    const n = trend.toLowerCase()
    if (n === 'bullish') return 'text-bharat-green'
    if (n === 'bearish') return 'text-red-600'
    return 'text-slate-700'
  }

  const fetchStockData = async (symbolToFetch = selectedSymbol) => {
    const symbol = symbolToFetch || selectedSymbol
    if (!symbol) return

    setStockError(null)
    setRsiError(null)
    setMacdError(null)
    setStockData(null)
    setRsiData(null)
    setMacdData(null)
    setLoading(true)

    try {
      const [stockRes, rsiRes, macdRes] = await Promise.allSettled([
        api.get(`/stock/${encodeURIComponent(symbol)}`),
        api.get(`/rsi/${encodeURIComponent(symbol)}`),
        api.get(`/macd/${encodeURIComponent(symbol)}`),
      ])

      if (stockRes.status === 'fulfilled') setStockData(stockRes.value.data)
      else {
        console.error('Stock fetch error:', stockRes.reason)
        setStockError(stockRes.reason?.response?.data?.detail || stockRes.reason?.message || 'Failed to fetch stock data')
      }

      if (rsiRes.status === 'fulfilled') setRsiData(rsiRes.value.data)
      else {
        console.error('RSI fetch error:', rsiRes.reason)
        setRsiError(rsiRes.reason?.response?.data?.detail || rsiRes.reason?.message || 'Failed to fetch RSI data')
      }

      if (macdRes.status === 'fulfilled') setMacdData(macdRes.value.data)
      else {
        console.error('MACD fetch error:', macdRes.reason)
        setMacdError(macdRes.reason?.response?.data?.detail || macdRes.reason?.message || 'Failed to fetch MACD data')
      }
    } catch (err) {
      console.error('Unexpected error:', err)
      setStockError('Unexpected error while fetching data')
      setRsiError('Unexpected error while fetching data')
      setMacdError('Unexpected error while fetching data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStockData(selectedSymbol)
  }, [selectedSymbol])

  const handleStockSelect = (stock) => {
    if (!stock) return
    setSelectedSymbol(stock.symbol)
    setSelectedName(stock.company_name || stock.display_symbol || stock.symbol)
    fetchStockData(stock.symbol)
  }

  const handleAddToWatchlist = () => {
    if (!selectedSymbol) return
    addToWatchlist(selectedSymbol, selectedName)
    setWatchlistRefresh((v) => v + 1)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {toast && (
        <div className="rounded-lg border border-bharat-green/60 bg-bharat-green/10 px-4 py-2 text-sm font-semibold text-bharat-green shadow-sm mb-4">
          {toast}
        </div>
      )}

      {/* Tab bar */}
      <div className="flex border-b-2 border-slate-200 mb-6">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative flex items-center gap-2 px-5 py-3 text-sm font-semibold transition-colors ${
              activeTab === tab.id
                ? 'text-bharat-navy'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <span>{tab.label}</span>
            {activeTab === tab.id && (
              <span
                className="w-1.5 h-1.5 rounded-full bg-bharat-saffron shrink-0"
                aria-hidden
              />
            )}
            {activeTab === tab.id && (
              <span
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-bharat-navy"
                aria-hidden
              />
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'market' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6">
              <h2 className="text-xl font-semibold text-bharat-navy mb-4">Market Overview</h2>
              <p className="text-sm text-slate-600 mb-4">
                Real-time price, volume, and daily range for NSE-listed securities.
              </p>
              <StockSearch onStockSelect={handleStockSelect} />
              <p className="text-xs text-slate-500 mt-2">
                Start typing a company name or NSE symbol (e.g. Reliance, TCS, HDFC Bank).
              </p>
            </div>

            <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-bharat-navy">Stock Data</h3>
                <button
                  type="button"
                  onClick={handleAddToWatchlist}
                  className="p-2 rounded-full text-bharat-saffron hover:bg-bharat-saffron/10 transition-colors"
                  title="Add to watchlist"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                  </svg>
                </button>
              </div>

              {stockError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {stockError}
                </div>
              )}

              {loading && !stockData && !stockError && (
                <p className="text-sm text-slate-500">Fetching Bharat Markets Data...</p>
              )}

              {stockData && (
                <div className="grid grid-cols-1 gap-3 text-sm">
                  <div className="pb-2 border-b border-slate-300">
                    <div className="flex items-center gap-2">
                      <span className="text-base font-semibold text-slate-900">
                        {selectedName || stockData.symbol}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500">NSE: {stockData.symbol?.replace('.NS', '')}</div>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-600">Price</span>
                    <span className="font-semibold">₹{stockData.price?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-600">Change</span>
                    <span className={`font-semibold ${changeColor(stockData.change)}`}>
                      {stockData.change >= 0 ? '+' : ''}{stockData.change}
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-600">Change %</span>
                    <span className={`font-semibold ${changeColor(stockData.change_percent)}`}>
                      {stockData.change_percent >= 0 ? '+' : ''}{stockData.change_percent}%
                    </span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200">
                    <span className="text-slate-600">Volume</span>
                    <span className="font-semibold">{stockData.volume?.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between py-1">
                    <span className="text-slate-600">Day High / Low</span>
                    <span className="font-semibold">
                      ₹{stockData.day_high?.toLocaleString()} / ₹{stockData.day_low?.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}

              {!loading && !stockData && !stockError && (
                <p className="text-sm text-slate-500">Pick a stock to see live price data.</p>
              )}
            </div>
          </div>

          <div>
            <Watchlist onSelectStock={handleStockSelect} refreshTrigger={watchlistRefresh} />
          </div>
        </div>
      )}

      {activeTab === 'technical' && (
        <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6">
          <h2 className="text-xl font-semibold text-bharat-navy mb-2">Technical Analysis</h2>
          <p className="text-sm text-slate-600 mb-6">
            Signals and momentum tools built for quick decisions.
          </p>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border-2 border-bharat-navy/30 p-5">
              <h3 className="text-lg font-semibold text-bharat-navy mb-2">RSI</h3>
              <p className="text-xs text-slate-600 mb-4">
                <span className="font-semibold text-bharat-navy">ⓘ</span> The Relative Strength Index (RSI) measures the speed and change of price movements to identify overbought or oversold conditions.
              </p>
              {rsiError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {rsiError}
                </div>
              )}
              {loading && !rsiData && !rsiError && (
                <p className="text-sm text-slate-500">Fetching Bharat Markets Data...</p>
              )}
              {rsiData && <RSIGauge value={rsiData.rsi} signal={rsiData.signal} />}
              {!loading && !rsiData && !rsiError && (
                <p className="text-sm text-slate-500">Select a stock in Market View to compute RSI.</p>
              )}
            </div>

            <div className="bg-white rounded-xl border-2 border-bharat-navy/30 p-5">
              <h3 className="text-lg font-semibold text-bharat-navy mb-2">MACD</h3>
              <p className="text-xs text-slate-600 mb-4">
                <span className="font-semibold text-bharat-navy">ⓘ</span> Moving Average Convergence Divergence (MACD) shows the relationship between two moving averages of a stock's price to find momentum.
              </p>
              {macdError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {macdError}
                </div>
              )}
              {loading && !macdData && !macdError && (
                <p className="text-sm text-slate-500">Fetching Bharat Markets Data...</p>
              )}
              {macdData && (
                <div className="space-y-4">
                  <MACDGauge histogram={macdData.histogram} trend={macdData.trend} />
                  <div className="grid grid-cols-2 gap-2 text-sm pt-2 border-t border-slate-200">
                    <div className="flex justify-between">
                      <span className="text-slate-600">MACD</span>
                      <span className="font-semibold">{macdData.macd}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">Signal</span>
                      <span className="font-semibold">{macdData.signal}</span>
                    </div>
                  </div>
                </div>
              )}
              {!loading && !macdData && !macdError && (
                <p className="text-sm text-slate-500">Select a stock in Market View to compute MACD.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'ai' && (
        <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6">
          <h2 className="text-xl font-semibold text-bharat-navy mb-2">AI Advisor</h2>
          <p className="text-sm text-slate-600 mb-4">
            <span className="font-semibold text-bharat-navy">ⓘ</span> Ask BharatFinanceAI for real-time analysis, SIP calculations, or market terminology.
          </p>
          <div className="rounded-xl border-2 border-bharat-navy/30 overflow-hidden">
            <Chat embedded heightClassName="h-[560px] md:h-[680px]" />
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
