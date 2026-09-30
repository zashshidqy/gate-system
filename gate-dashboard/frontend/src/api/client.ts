import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosError } from 'axios'
import toast from 'react-hot-toast'

const API_BASE = (import.meta as any).env?.VITE_API_BASE || '/api'
const API_DOWN_MESSAGE = 'Cannot reach API at http://127.0.0.1:8000. Start the backend.'

function isAuthEndpoint(url?: string): boolean {
  if (!url) return false
  return url.includes('/auth/login') || url.includes('/auth/register')
}

function formatDetail(detail: unknown): string | null {
  if (!detail) return null
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item?.msg) return item.msg
        return null
      })
      .filter(Boolean)
      .join('. ')
  }
  if (typeof detail === 'object' && detail !== null && 'msg' in detail) {
    return String((detail as { msg: unknown }).msg)
  }
  return null
}

class ApiClient {
  private client: AxiosInstance
  private retryCount: Map<string, number> = new Map()
  private maxRetries = 3
  private retryDelay = 1000 // ms
  private apiDownToastId = 'api-unreachable'

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 15000,
    })

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      const token = localStorage.getItem('access_token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    this.client.interceptors.response.use(
      (response) => {
        const key = `${response.config.method}-${response.config.url}`
        this.retryCount.delete(key)
        return response
      },
      async (error: AxiosError) => {
        const config = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

        if (!config) return Promise.reject(error)

        const key = `${config.method}-${config.url}`
        const currentRetry = this.retryCount.get(key) || 0
        const status = error.response?.status
        const authRequest = isAuthEndpoint(config.url)

        // 401 on login/register: let the form show Invalid username or password
        if (status === 401 && authRequest) {
          this.retryCount.delete(key)
          return Promise.reject(error)
        }

        // 401 on authenticated routes: clear session and send user to login
        if (status === 401) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('user')
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
          return Promise.reject(error)
        }

        if (status === 403) {
          toast.error('Anda tidak memiliki izin untuk tindakan ini')
          return Promise.reject(error)
        }

        if (status === 503) {
          const message = (error.response?.data as any)?.detail || 'Gate system is unavailable'
          toast.error(message)
          return Promise.reject(error)
        }

        const unreachable =
          !error.response ||
          status === 502 ||
          error.code === 'ECONNREFUSED' ||
          error.code === 'ERR_NETWORK' ||
          error.code === 'ECONNABORTED'

        // Never retry login/register — fail fast with a clear message
        if (authRequest && unreachable) {
          toast.error(API_DOWN_MESSAGE, { id: this.apiDownToastId })
          this.retryCount.delete(key)
          return Promise.reject(error)
        }

        const isRetryable =
          unreachable ||
          (status ?? 0) >= 500 ||
          error.code === 'ENOTFOUND'

        if (isRetryable && currentRetry < this.maxRetries && !config._retry && !authRequest) {
          config._retry = true
          this.retryCount.set(key, currentRetry + 1)

          const delay = this.retryDelay * Math.pow(2, currentRetry)
          await new Promise((resolve) => setTimeout(resolve, delay))

          return this.client(config)
        }

        if (unreachable) {
          toast.error(API_DOWN_MESSAGE, { id: this.apiDownToastId })
        } else if ((status ?? 0) >= 500) {
          toast.error('Galat server. Silakan coba lagi nanti.')
        } else if (status === 400) {
          const message = formatDetail((error.response?.data as any)?.detail) || 'Invalid request'
          toast.error(message)
        } else if (status === 404) {
          toast.error('Data tidak ditemukan')
        }

        this.retryCount.delete(key)
        return Promise.reject(error)
      }
    )
  }

  get instance() {
    return this.client
  }

  setToken(token: string | null) {
    if (token) {
      localStorage.setItem('access_token', token)
    } else {
      localStorage.removeItem('access_token')
    }
  }

  getToken() {
    return localStorage.getItem('access_token')
  }

  clearRetries() {
    this.retryCount.clear()
  }
}

const client = new ApiClient()
export const apiClient = client
export const api = client.instance
