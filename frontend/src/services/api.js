import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
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

export default api
