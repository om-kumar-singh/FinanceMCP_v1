import { useState } from 'react'
import { predictResilience } from '../services/api'
import ResilienceCharts from '../components/ResilienceCharts'

function getRiskLevelColor(riskLevel) {
  if (!riskLevel) return 'text-slate-700'
  const level = String(riskLevel).toLowerCase()
  if (level.includes('strong')) return 'text-green-600 bg-green-50 border-green-200'
  if (level.includes('moderate')) return 'text-amber-700 bg-amber-50 border-amber-200'
  if (level.includes('vulnerable')) return 'text-orange-600 bg-orange-50 border-orange-200'
  if (level.includes('high')) return 'text-red-600 bg-red-50 border-red-200'
  return 'text-slate-700 bg-slate-50 border-slate-200'
}

function ResiliencePredictor() {
  const [income, setIncome] = useState('')
  const [monthlyExpenses, setMonthlyExpenses] = useState('')
  const [savings, setSavings] = useState('')
  const [emi, setEmi] = useState('')
  const [stockPortfolioValue, setStockPortfolioValue] = useState('')
  const [mutualFundValue, setMutualFundValue] = useState('')

  const [ageBand, setAgeBand] = useState('')
  const [dependents, setDependents] = useState('')
  const [riskTolerance, setRiskTolerance] = useState('')
  const [primaryGoal, setPrimaryGoal] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [lastInputs, setLastInputs] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setResult(null)

    const inc = parseFloat(income)
    const exp = parseFloat(monthlyExpenses)
    const sav = parseFloat(savings)
    const emiVal = parseFloat(emi)
    if (!income || !monthlyExpenses || !savings || emi === '' || isNaN(inc) || isNaN(exp) || isNaN(sav) || isNaN(emiVal)) {
      setError('Please fill in Income, Monthly Expenses, Savings, and EMI.')
      return
    }
    if (inc <= 0 || exp <= 0 || sav < 0 || emiVal < 0) {
      setError('Income and expenses must be positive. Savings and EMI must be non-negative.')
      return
    }

    setLoading(true)
    try {
      const profile = {
        age_band: ageBand || null,
        dependents: dependents !== '' ? Number(dependents) : null,
        risk_tolerance: riskTolerance || null,
        primary_goal: primaryGoal || null,
      }
      const hasProfile = Object.values(profile).some(
        (v) => v !== null && v !== '' && !Number.isNaN(v)
      )

      const payload = {
        income: inc,
        monthly_expenses: exp,
        savings: sav,
        emi: emiVal,
        stock_portfolio_value: stockPortfolioValue ? parseFloat(stockPortfolioValue) || 0 : 0,
        mutual_fund_value: mutualFundValue ? parseFloat(mutualFundValue) || 0 : 0,
        ...(hasProfile ? { profile } : {}),
      }
      const data = await predictResilience(payload)
      setResult(data)
      setLastInputs({ savings: sav, monthlyExpenses: exp })
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Failed to predict resilience.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl sm:text-3xl font-bold text-bharat-navy mb-6">
        AI Financial Shock Resilience Predictor
      </h1>

      {/* Section 1: Financial Inputs Form */}
      <section className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6 mb-8">
        <h2 className="text-lg font-semibold text-bharat-navy mb-4">Financial Inputs</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="income" className="block text-sm font-medium text-slate-700 mb-1">
              Monthly Income (₹)
            </label>
            <input
              id="income"
              type="number"
              min="0"
              step="1000"
              value={income}
              onChange={(e) => setIncome(e.target.value)}
              placeholder="e.g. 80000"
              className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
            />
          </div>
          <div>
            <label htmlFor="monthlyExpenses" className="block text-sm font-medium text-slate-700 mb-1">
              Monthly Expenses (₹)
            </label>
            <input
              id="monthlyExpenses"
              type="number"
              min="0"
              step="1000"
              value={monthlyExpenses}
              onChange={(e) => setMonthlyExpenses(e.target.value)}
              placeholder="e.g. 40000"
              className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
            />
          </div>
          <div>
            <label htmlFor="savings" className="block text-sm font-medium text-slate-700 mb-1">
              Savings (₹)
            </label>
            <input
              id="savings"
              type="number"
              min="0"
              step="1000"
              value={savings}
              onChange={(e) => setSavings(e.target.value)}
              placeholder="e.g. 240000"
              className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
            />
          </div>
          <div>
            <label htmlFor="emi" className="block text-sm font-medium text-slate-700 mb-1">
              EMI (₹)
            </label>
            <input
              id="emi"
              type="number"
              min="0"
              step="500"
              value={emi}
              onChange={(e) => setEmi(e.target.value)}
              placeholder="e.g. 10000"
              className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
            />
          </div>
          <div>
            <label htmlFor="stockPortfolioValue" className="block text-sm font-medium text-slate-700 mb-1">
              Stock Portfolio Value (₹) <span className="text-slate-500">optional</span>
            </label>
            <input
              id="stockPortfolioValue"
              type="number"
              min="0"
              step="1000"
              value={stockPortfolioValue}
              onChange={(e) => setStockPortfolioValue(e.target.value)}
              placeholder="e.g. 500000"
              className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
            />
          </div>
          <div>
            <label htmlFor="mutualFundValue" className="block text-sm font-medium text-slate-700 mb-1">
              Mutual Fund Value (₹) <span className="text-slate-500">optional</span>
            </label>
            <input
              id="mutualFundValue"
              type="number"
              min="0"
              step="1000"
              value={mutualFundValue}
              onChange={(e) => setMutualFundValue(e.target.value)}
              placeholder="e.g. 300000"
              className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
            />
          </div>

          {/* Optional profile inputs for personalised Gemini recommendations */}
          <div className="pt-2 border-t border-slate-200 mt-2">
            <p className="text-xs text-slate-500 mb-3">
              Optional: Share a few details so AI (Gemini) can tailor recommendations to your situation.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label htmlFor="ageBand" className="block text-sm font-medium text-slate-700 mb-1">
                  Age Band <span className="text-slate-500">optional</span>
                </label>
                <select
                  id="ageBand"
                  value={ageBand}
                  onChange={(e) => setAgeBand(e.target.value)}
                  className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 bg-white focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none text-sm"
                >
                  <option value="">Select age band</option>
                  <option value="18-25">18–25</option>
                  <option value="26-35">26–35</option>
                  <option value="36-50">36–50</option>
                  <option value="50+">50+</option>
                </select>
              </div>
              <div>
                <label htmlFor="dependents" className="block text-sm font-medium text-slate-700 mb-1">
                  Number of Dependents <span className="text-slate-500">optional</span>
                </label>
                <input
                  id="dependents"
                  type="number"
                  min="0"
                  step="1"
                  value={dependents}
                  onChange={(e) => setDependents(e.target.value)}
                  placeholder="e.g. 2"
                  className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none"
                />
              </div>
              <div>
                <label htmlFor="riskTolerance" className="block text-sm font-medium text-slate-700 mb-1">
                  Risk Tolerance <span className="text-slate-500">optional</span>
                </label>
                <select
                  id="riskTolerance"
                  value={riskTolerance}
                  onChange={(e) => setRiskTolerance(e.target.value)}
                  className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 bg-white focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none text-sm"
                >
                  <option value="">Select risk level</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div>
                <label htmlFor="primaryGoal" className="block text-sm font-medium text-slate-700 mb-1">
                  Primary Goal <span className="text-slate-500">optional</span>
                </label>
                <select
                  id="primaryGoal"
                  value={primaryGoal}
                  onChange={(e) => setPrimaryGoal(e.target.value)}
                  className="w-full rounded-lg border-2 border-slate-300 px-3 py-2 text-slate-900 bg-white focus:border-bharat-navy focus:ring-1 focus:ring-bharat-navy outline-none text-sm"
                >
                  <option value="">Select goal</option>
                  <option value="emergency_fund">Build emergency fund</option>
                  <option value="house">Buy a house</option>
                  <option value="education">Children&apos;s education</option>
                  <option value="retirement">Retirement planning</option>
                  <option value="wealth_growth">Wealth growth</option>
                </select>
              </div>
            </div>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full sm:w-auto inline-flex items-center justify-center rounded-full bg-bharat-saffron px-6 py-2.5 text-sm font-semibold text-bharat-navy shadow-md hover:bg-orange-500 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Predicting…' : 'Predict Resilience'}
          </button>
        </form>
      </section>

      {/* Section 2: Prediction Results + AI Recommendations */}
      {result && (
        <section className="mb-8 grid grid-cols-1 md:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] gap-4 md:gap-6">
          <div className="bg-white rounded-2xl border-2 border-bharat-navy/40 shadow-lg p-6">
            <h2 className="text-lg font-semibold text-bharat-navy mb-4">Prediction Results</h2>
            {result.insight && (
              <p className="text-sm text-slate-600 mb-4 pb-4 border-b border-slate-200">
                {result.insight}
              </p>
            )}
            {Array.isArray(result.insights) && result.insights.length > 0 && (
              <div className="mb-4 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-3">
                <h3 className="text-sm font-semibold text-indigo-800 mb-2">Financial Insights</h3>
                <ul className="list-disc list-inside text-sm text-indigo-900 space-y-1">
                  {result.insights.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <ResultRow label="Resilience Score" value={result.resilience_score} />
              <ResultRow
                label="Risk Level"
                value={result.risk_level}
                highlight
                colorClass={getRiskLevelColor(result.risk_level)}
              />
              <ResultRow label="Runway Months" value={result.runway_months} />
              {result.adjusted_runway_after_market_shock != null && (
                <ResultRow label="Adjusted Runway After Market Shock" value={result.adjusted_runway_after_market_shock} />
              )}
              {result.portfolio_volatility != null && (
                <ResultRow label="Portfolio Volatility" value={result.portfolio_volatility} />
              )}
              {result.macro_sentiment_risk != null && (
                <ResultRow label="Macro Sentiment Risk" value={result.macro_sentiment_risk} />
              )}
              {result.survival_probability_6_months != null && (
                <ResultRow label="Survival Probability (6 months) %" value={result.survival_probability_6_months} />
              )}
              {result.ml_resilience_score != null && (
                <ResultRow label="ML Resilience Score" value={result.ml_resilience_score} />
              )}
              {result.combined_resilience_score != null && (
                <ResultRow label="Combined Resilience Score" value={result.combined_resilience_score} />
              )}
            </div>
            {result.news_based_adjustment && (
              <p className="mt-4 text-xs text-slate-500">{result.news_based_adjustment}</p>
            )}
          </div>

          {result.recommendations && typeof result.recommendations === 'object' && (
            <aside className="bg-white rounded-2xl border-2 border-emerald-200 shadow-lg p-6">
              <h3 className="text-lg font-semibold text-emerald-900 mb-1">Recommendations</h3>
              <p className="text-xs text-emerald-700 mb-3">
                Personalised tips based on your profile and current resilience metrics.
              </p>
              {result.recommendation_source === 'gemini_unavailable' && (
                <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                  <p className="text-xs text-amber-800">
                    Gemini recommendations are unavailable. Common causes: missing/invalid `GEMINI_API_KEY`, model not enabled, or quota/rate-limit exceeded.
                    Check backend logs, then restart the backend after updating `backend/.env`.
                  </p>
                </div>
              )}
              <div className="grid grid-cols-1 gap-3">
                {[
                  { key: 'normal', title: 'Normal' },
                  { key: 'market_crash', title: 'Market Crash' },
                  { key: 'job_loss', title: 'Job Loss' },
                  { key: 'emergency', title: 'Emergency' },
                ].map(({ key, title }) => {
                  const items = Array.isArray(result.recommendations?.[key])
                    ? result.recommendations[key].slice(0, 5)
                    : []
                  if (items.length === 0) return null
                  return (
                    <div key={key} className="rounded-lg border border-emerald-200 bg-emerald-50/60 px-3 py-2">
                      <p className="text-xs font-semibold text-emerald-900 mb-1">{title}</p>
                      <ul className="list-disc list-inside text-sm text-emerald-950 space-y-1">
                        {items.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )
                })}
              </div>
            </aside>
          )}
        </section>
      )}
      {result && (
        <ResilienceCharts result={result} inputData={lastInputs || {}} />
      )}
    </div>
  )
}

function ResultRow({ label, value, highlight, colorClass }) {
  if (value == null && value !== 0) return null
  const val =
    typeof value === 'number'
      ? Number.isInteger(value)
        ? value
        : Number(value.toFixed(2))
      : value
  return (
    <div
      className={`flex justify-between items-center py-2 border-b border-slate-100 ${highlight ? 'rounded-lg px-3 -mx-3 border' : ''} ${colorClass || ''}`}
    >
      <span className="text-sm text-slate-600">{label}</span>
      <span className="text-sm font-semibold">{val}</span>
    </div>
  )
}

export default ResiliencePredictor
