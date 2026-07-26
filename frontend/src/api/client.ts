import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('API error:', err.message)
    return Promise.reject(err)
  },
)

export default api
