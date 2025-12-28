import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../services/api'

export interface User {
  id: number
  email: string | null
  first_name: string
  last_name: string | null
  role: string
  preferred_language: string
  preferred_currency: string
  agency_name: string | null
  agency_logo_url: string | null
  avatar_url: string | null
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refreshAccessToken: () => Promise<void>
  fetchUser: () => Promise<void>
  updateUser: (data: Partial<User>) => void
}

interface RegisterData {
  email: string
  password: string
  first_name: string
  last_name?: string
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      
      login: async (email, password) => {
        set({ isLoading: true })
        try {
          const formData = new URLSearchParams()
          formData.append('username', email)
          formData.append('password', password)
          
          const response = await api.post('/auth/login', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
          })
          
          const { access_token, refresh_token } = response.data
          
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })
          
          // Fetch user info
          await get().fetchUser()
        } finally {
          set({ isLoading: false })
        }
      },
      
      register: async (data) => {
        set({ isLoading: true })
        try {
          await api.post('/auth/register', data)
          // Auto login after registration
          await get().login(data.email, data.password)
        } finally {
          set({ isLoading: false })
        }
      },
      
      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },
      
      refreshAccessToken: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          get().logout()
          return
        }
        
        try {
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken
          })
          
          const { access_token, refresh_token } = response.data
          
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
          })
        } catch {
          get().logout()
        }
      },
      
      fetchUser: async () => {
        try {
          const response = await api.get('/auth/me')
          set({ user: response.data })
        } catch {
          get().logout()
        }
      },
      
      updateUser: (data) => {
        set((state) => ({
          user: state.user ? { ...state.user, ...data } : null
        }))
      },
    }),
    {
      name: 'propbase-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
