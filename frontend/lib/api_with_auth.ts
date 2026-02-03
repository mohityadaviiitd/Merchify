import api from './api'
import { getToken } from './auth'

api.interceptors.request.use(config => {
  const token = getToken()
  if (token && config.headers) {
    config.headers['Authorization'] = `Token ${token}`
  }
  return config
})

export default api
