import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
})

export const searchStocks = async (query, limit = 8, signal) => {
  const response = await api.get('/stock/search', {
    params: { q: query, limit },
    signal,
  })
  return response.data
}

export const getPopularStocks = async () => {
  const response = await api.get('/stock/popular')
  return response.data
}

export const resolveSymbol = async (query) => {
  const response = await api.get('/stock/resolve', {
    params: { q: query },
  })
  return response.data
}

export const getMarketNews = async (symbol) => {
  const safeSymbol = symbol || 'NSE'
  const response = await api.get(`/news/${encodeURIComponent(safeSymbol)}`)
  return response.data
}

export const searchMutualFunds = async (query) => {
  const response = await api.get('/mutual-fund/search', {
    params: { query },
  })
  return response.data
}

export const getMutualFundNav = async (schemeCode) => {
  if (!schemeCode) throw new Error('schemeCode is required')
  const response = await api.get(`/mutual-fund/${encodeURIComponent(schemeCode)}`)
  return response.data
}

export const calculateSip = async (monthlyInvestment, years, annualReturn) => {
  const response = await api.get('/sip', {
    params: {
      monthly_investment: monthlyInvestment,
      years,
      annual_return: annualReturn,
    },
  })
  return response.data
}

export default api
