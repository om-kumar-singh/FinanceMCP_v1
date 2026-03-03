function MACDGauge({ histogram, trend }) {
  const h = typeof histogram === 'number' ? histogram : 0
  const isBullish = (trend || '').toLowerCase() === 'bullish'

  const maxAbs = Math.max(0.1, Math.abs(h) * 1.5)
  const normalized = Math.max(-1, Math.min(1, h / maxAbs))
  const pct = ((normalized + 1) / 2) * 100

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-[10px] text-slate-500">
        <span>−</span>
        <span>Histogram</span>
        <span>+</span>
      </div>
      <div className="h-3 bg-slate-200 rounded-full overflow-hidden relative">
        <div className="absolute inset-0 flex">
          <div className="h-full flex-1 bg-red-100" />
          <div className="h-full flex-1 bg-bharat-green/20" />
        </div>
        <div
          className={`absolute top-0 bottom-0 w-1 rounded-full ${
            isBullish ? 'bg-bharat-green' : 'bg-red-500'
          }`}
          style={{ left: `${pct}%`, marginLeft: '-2px' }}
        />
      </div>
      <div className="flex justify-between items-center text-sm">
        <span className="text-slate-600">Trend</span>
        <span className={`font-semibold ${
          isBullish ? 'text-bharat-green' : (trend || '').toLowerCase() === 'bearish' ? 'text-red-600' : 'text-slate-600'
        }`}>
          {trend || '—'}
        </span>
      </div>
    </div>
  )
}

export default MACDGauge
