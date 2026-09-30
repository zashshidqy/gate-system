import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { apiClient } from '../api/client'
import { User, TokenResponse } from '../types'

interface AuthContextType {
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
  register: (data: { username: string; email?: string; password: string; full_name?: string; role?: string }) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const initAuth = async () => {
      const token = apiClient.getToken()
      if (token) {
        try {
          const response = await apiClient.instance.get<User>('/auth/me')
          setUser(response.data)
        } catch {
          apiClient.setToken(null)
        }
      }
      setIsLoading(false)
    }
    initAuth()
  }, [])

  const login = async (username: string, password: string) => {
    const response = await apiClient.instance.post<TokenResponse>('/auth/login', { username, password })
    apiClient.setToken(response.data.access_token)
    setUser(response.data.user)
  }

  const register = async (data: { username: string; email?: string; password: string; full_name?: string; role?: string }) => {
    await apiClient.instance.post<User>('/auth/register', data)
    await login(data.username, data.password)
  }

  const logout = () => {
    apiClient.setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoading, register }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}