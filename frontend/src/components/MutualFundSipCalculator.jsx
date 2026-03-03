import { useEffect, useMemo, useState } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

function getDefaultReturnForSchemeType(schemeType) {
  if (!schemeType) return 12
  const t = String(schemeType).toLowerCase()
  if (t.includes('equity') || t.includes('growth')) return 12
  if (t.includes('index')) return 10
  if (t.includes('debt') || t.includes('liquid') || t.includes('income')) return 7
  if (t.includes('hybrid') || t.includes('balanced')) return 9
  return 12
}

function computeSipSeries(monthly, years, annualReturn) {
  const r = annualReturn / 12 / 100
  const series = []
  for (let y = 1; y <= years; y += 1) {
    const n = y * 12
    let fv
    if (r <= 0) {
      fv = monthly * n
    } else {
      fv = monthly * ((1 + r) ** n - 1) / r * (1 + r)
    }
    series.push({ year: y, value: Math.round(fv) })
  }
  return series
}

function MutualFundSipCalculator({ selectedFund }) {
  const [monthly, setMonthly] = useState(5000)
  const [years, setYears] = useState(10)
  const [expectedReturn, setExpectedReturn] = useState(12)

  useEffect(() => {
    if (selectedFund?.scheme_type) {
      const defaultRet = getDefaultReturnForSchemeType(selectedFund.scheme_type)
      setExpectedReturn(defaultRet)
      console.log('[MutualFundSipCalculator] Fund changed, default return:', defaultRet, 'scheme_type:', selectedFund.scheme_type)
    }
  }, [selectedFund?.scheme_code, selectedFund?.scheme_type])

  const series = useMemo(
    () => computeSipSeries(monthly, years, expectedReturn),
    [monthly, years, expectedReturn],
  )

  const totalInvested = monthly * years * 12
  const finalValue = series.length ? series[series.length - 1].value : 0

  const data = {
    labels: series.map((p) => `Y${p.year}`),
    datasets: [
      {
        label: 'Projected Wealth (₹)',
        data: series.map((p) => p.value),
        borderColor: '#000080',
        backgroundColor: 'rgba(0, 0, 128, 0.1)',
        tension: 0.25,
        pointRadius: 2,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        callbacks: {
          label: (ctx) => `₹${ctx.parsed.y.toLocaleString()}`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
      },
      y: {
        ticks: {
          callback: (value) => `₹${Number(value).toLocaleString()}`,
        },
      },
    },
  }

  return (
    <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-5 flex flex-col h-full">
      <h3 className="text-lg font-semibold text-bharat-navy mb-2">SIP Calculator</h3>
      {selectedFund?.scheme_name && (
        <p className="text-xs text-slate-600 mb-1">
          For: <span className="font-semibold text-bharat-navy">{selectedFund.scheme_name}</span>
        </p>
      )}
      <p className="text-xs text-slate-600 mb-4">
        <span className="font-semibold text-bharat-navy">ⓘ</span> Projected wealth is based on
        monthly SIP and expected annual return. Actual returns may differ.
      </p>

      <div className="space-y-4 mb-4">
        <div>
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Monthly Amount</span>
            <span className="font-semibold text-slate-900">₹{monthly.toLocaleString()}</span>
          </div>
          <input
            type="range"
            min={1000}
            max={100000}
            step={500}
            value={monthly}
            onChange={(e) => setMonthly(Number(e.target.value))}
            className="w-full accent-bharat-saffron"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Duration (Years)</span>
            <span className="font-semibold text-slate-900">{years} yrs</span>
          </div>
          <input
            type="range"
            min={1}
            max={30}
            step={1}
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            className="w-full accent-bharat-saffron"
          />
        </div>

        <div>
          <div className="flex justify-between text-xs text-slate-600 mb-1">
            <span>Expected Return (p.a.)</span>
            <span className="font-semibold text-slate-900">{expectedReturn}%</span>
          </div>
          <input
            type="range"
            min={4}
            max={20}
            step={0.5}
            value={expectedReturn}
            onChange={(e) => setExpectedReturn(Number(e.target.value))}
            className="w-full accent-bharat-saffron"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs mb-4">
        <div className="bg-slate-50 rounded-lg border border-slate-200 px-3 py-2">
          <div className="text-slate-500 mb-1">Total Invested</div>
          <div className="text-sm font-semibold text-slate-900">
            ₹{totalInvested.toLocaleString()}
          </div>
        </div>
        <div className="bg-bharat-green/5 rounded-lg border border-bharat-green/40 px-3 py-2">
          <div className="text-slate-500 mb-1">Projected Wealth</div>
          <div className="text-sm font-semibold text-bharat-green">
            ₹{finalValue.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-[160px]">
        <Line data={data} options={options} />
      </div>
    </div>
  )
}

export default MutualFundSipCalculator

