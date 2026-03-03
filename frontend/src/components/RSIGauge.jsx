function RSIGauge({ value, signal }) {
  const rsi = typeof value === 'number' ? Math.min(100, Math.max(0, value)) : 50
  const oversold = 30
  const overbought = 70

  let zoneColor = 'bg-slate-300'
  if (rsi <= oversold) zoneColor = 'bg-bharat-green'
  else if (rsi >= overbought) zoneColor = 'bg-red-500'
  else zoneColor = 'bg-amber-400'

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-[10px] text-slate-500">
        <span>0</span>
        <span className="text-bharat-green">Oversold 30</span>
        <span>50</span>
        <span className="text-red-500">Overbought 70</span>
        <span>100</span>
      </div>
      <div className="h-3 bg-slate-200 rounded-full overflow-hidden flex">
        <div
          className={`h-full ${zoneColor} transition-all duration-500 rounded-l-full`}
          style={{ width: `${rsi}%` }}
        />
      </div>
      <div className="flex justify-between items-center text-sm">
        <span className="text-slate-600">RSI</span>
        <span className="font-bold text-bharat-navy">{value ?? '—'}</span>
        <span className={`font-medium ${
          signal?.toLowerCase() === 'overbought' ? 'text-red-600' :
          signal?.toLowerCase() === 'oversold' ? 'text-bharat-green' :
          signal?.toLowerCase() === 'neutral' ? 'text-amber-600' : 'text-slate-600'
        }`}>
          {signal || '—'}
        </span>
      </div>
    </div>
  )
}

export default RSIGauge
