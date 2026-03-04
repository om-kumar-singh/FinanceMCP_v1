import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  Label,
} from 'recharts'

/**
 * Build survival probability curve from API result.
 * Maps months to estimated probability of surviving to that month.
 */
function buildSurvivalData(result) {
  if (!result) return []
  const runway = Number(result.runway_months) || 1
  const prob6 = Number(result.survival_probability_6_months) ?? 60
  const months = [1, 2, 3, 6, 12]
  return months.map((month) => {
    let probability
    if (month <= 1) probability = 95
    else if (month === 2) probability = 90
    else if (month === 3) probability = 82
    else if (month === 6) probability = prob6
    else probability = Math.max(5, Math.round(prob6 - (month - 6) * 5))
    return { month, probability: Math.max(0, Math.min(100, probability)) }
  })
}

/**
 * Build shock scenario comparison from API result.
 */
function buildShockData(result) {
  if (!result) return []
  const runway = Number(result.runway_months) || 1
  const adjusted = result.adjusted_runway_after_market_shock != null
    ? Number(result.adjusted_runway_after_market_shock)
    : runway * 0.75
  const worst = Number(result.worst_case_survival_months) ?? runway * 0.5
  const emergency = runway * 0.4
  return [
    { scenario: 'Normal', months: Math.round(runway * 10) / 10 },
    { scenario: 'Market Crash', months: Math.round(adjusted * 10) / 10 },
    { scenario: 'Job Loss', months: Math.round(worst * 10) / 10 },
    { scenario: 'Emergency', months: Math.round(Math.max(0.5, emergency) * 10) / 10 },
  ]
}

/**
 * Build runway depletion (savings vs months) from savings and monthly expenses.
 */
function buildRunwayData(savings, monthlyExpenses) {
  if (!savings || !monthlyExpenses || monthlyExpenses <= 0) return []
  const s = Number(savings)
  const e = Number(monthlyExpenses)
  const data = []
  let remaining = s
  for (let month = 0; month <= Math.ceil(s / e) + 2 && month <= 24; month++) {
    data.push({ month, savings: Math.max(0, Math.round(remaining)) })
    remaining -= e
  }
  return data
}

function getRunwayNarrative(runwayData) {
  if (!runwayData || runwayData.length < 2) return null
  const first = runwayData[0]
  const last = runwayData[runwayData.length - 1]
  const slope = last.savings - first.savings

  if (slope < 0) {
    return "Your savings are decreasing over time. The point where the line hits ₹0 shows when you'd run out of money if income stops."
  }
  if (slope > 0) {
    return "You're saving money each month! Your financial runway is extending."
  }
  return "Your expenses match your income - savings remain stable."
}

function getRunwayLengthText(runwayData) {
  if (!runwayData || runwayData.length === 0) return null
  const zeroPoint = runwayData.find((d) => d.savings <= 0)
  if (zeroPoint) {
    return `Runway Length: The month when funds reach ₹0 = ${zeroPoint.month} months of financial independence.`
  }
  const last = runwayData[runwayData.length - 1]
  return `Runway Length: Funds stay above ₹0 for at least ${last.month} months in this projection.`
}

export default function ResilienceCharts({ result, inputData = {} }) {
  const survivalData = buildSurvivalData(result)
  const shockData = buildShockData(result)
  const runwayData = buildRunwayData(inputData.savings, inputData.monthlyExpenses)
  const runwayNarrative = getRunwayNarrative(runwayData)
  const runwayLengthText = getRunwayLengthText(runwayData)

  const hasAnyData = survivalData.length > 0 || shockData.length > 0 || runwayData.length > 0
  if (!result || !hasAnyData) return null

  return (
    <section className="mt-8 bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6">
      <h2 className="text-lg font-semibold text-bharat-navy mb-6">
        Financial Shock Simulation Analysis
      </h2>
      <div>
        {/* Survival Probability Curve */}
        {survivalData.length > 0 && (
          <div className="chart-container">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Financial Survival Probability
            </h3>
            <div className="h-64 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={survivalData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="month" stroke="#4f46e5" tick={{ fontSize: 12 }}>
                    <Label
                      value="Months of Survival"
                      offset={-5}
                      position="insideBottom"
                      style={{ fill: '#4f46e5', fontSize: 12 }}
                    />
                  </XAxis>
                  <YAxis stroke="#4f46e5" tick={{ fontSize: 12 }} domain={[0, 100]}>
                    <Label
                      value="Survival Probability (%)"
                      angle={-90}
                      position="insideLeft"
                      style={{ textAnchor: 'middle', fill: '#4f46e5', fontSize: 12 }}
                    />
                  </YAxis>
                  <Tooltip
                    contentStyle={{
                      borderRadius: '8px',
                      border: 'none',
                      boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="probability"
                    name="Survival %"
                    stroke="#4f46e5"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex flex-col sm:flex-row sm:justify-between gap-2">
              <p className="text-[11px] text-slate-500">
                Shows how long your finances can sustain you over different time periods (1-12 months).
              </p>
              <p className="text-[11px] text-slate-500 sm:text-right">
                Likelihood of maintaining financial stability during normal conditions.
              </p>
            </div>
            <p className="mt-3 text-xs text-slate-600">
              This graph shows your probability of financial survival decreasing over time as expenses accumulate.
              A steeper drop indicates higher vulnerability to prolonged financial stress.
            </p>
          </div>
        )}

        {/* Shock Scenario Comparison */}
        {shockData.length > 0 && (
          <div className="chart-container">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Impact of Financial Shocks
            </h3>
            <div className="h-56 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={shockData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="scenario" stroke="#4f46e5" tick={{ fontSize: 11 }}>
                    <Label
                      value="Shock Scenarios"
                      offset={-5}
                      position="insideBottom"
                      style={{ fill: '#4f46e5', fontSize: 12 }}
                    />
                  </XAxis>
                  <YAxis stroke="#4f46e5" tick={{ fontSize: 12 }}>
                    <Label
                      value="Financial Impact (%)"
                      angle={-90}
                      position="insideLeft"
                      style={{ textAnchor: 'middle', fill: '#4f46e5', fontSize: 12 }}
                    />
                  </YAxis>
                  <Tooltip
                    contentStyle={{
                      borderRadius: '8px',
                      border: 'none',
                      boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
                    }}
                  />
                  <Bar
                    dataKey="months"
                    name="Runway (months)"
                    fill="#f97316"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex flex-col gap-1">
              <p className="text-[11px] text-slate-500">
                "Normal" → Baseline conditions with no financial shock
              </p>
              <p className="text-[11px] text-slate-500">
                "Market Crash" → 30-40% drop in investment values
              </p>
              <p className="text-[11px] text-slate-500">
                "Job Loss" → 3-6 months without steady income
              </p>
              <p className="text-[11px] text-slate-500">
                "Emergency" → Major unexpected expense (medical/repairs)
              </p>
            </div>
            <p className="mt-2 text-[11px] text-slate-500">
              Percentage reduction in your total net worth.
            </p>
            <p className="mt-3 text-xs text-slate-600">
              This bar chart compares how different shock scenarios affect your finances. Lower bars indicate better
              resilience. The &quot;Emergency&quot; bar typically shows the smallest impact if you have adequate savings.
            </p>
          </div>
        )}

        {/* Projected Financial Runway */}
        {runwayData.length > 0 && (
          <div className="chart-container">
            <h3 className="text-sm font-semibold text-slate-700 mb-3">
              Projected Financial Runway
            </h3>
            <div className="h-64 w-full min-w-0">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={runwayData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="month" stroke="#4f46e5" tick={{ fontSize: 12 }}>
                    <Label
                      value="Months"
                      offset={-5}
                      position="insideBottom"
                      style={{ fill: '#4f46e5', fontSize: 12 }}
                    />
                  </XAxis>
                  <YAxis stroke="#4f46e5" tick={{ fontSize: 12 }}>
                    <Label
                      value="Remaining Funds (₹)"
                      angle={-90}
                      position="insideLeft"
                      style={{ textAnchor: 'middle', fill: '#4f46e5', fontSize: 12 }}
                    />
                  </YAxis>
                  <Tooltip
                    contentStyle={{
                      borderRadius: '8px',
                      border: 'none',
                      boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
                    }}
                    formatter={(v) => [`₹${Number(v).toLocaleString()}`, 'Savings']}
                  />
                  <Area
                    type="monotone"
                    dataKey="savings"
                    stroke="#2563eb"
                    fillOpacity={0.3}
                    fill="#3b82f6"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 flex flex-col sm:flex-row sm:justify-between gap-2">
              <p className="text-[11px] text-slate-500">
                Time horizon showing 0-19 months into the future.
              </p>
              <p className="text-[11px] text-slate-500 sm:text-right">
                Projected balance of savings + liquid investments over time.
              </p>
            </div>
            {runwayNarrative && (
              <p className="mt-3 text-xs text-slate-600">
                {runwayNarrative}
              </p>
            )}
            {runwayLengthText && (
              <p className="mt-1 text-xs font-medium text-slate-700">
                {runwayLengthText}
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
