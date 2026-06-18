import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { login as apiLogin, getMe, setAccessToken, getAccessToken } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchUser = useCallback(async () => {
    try {
      const res = await getMe()
      setUser(res.data)
    } catch {
      setUser(null)
      setAccessToken(null)
    }
  }, [])

  useEffect(() => {
    if (getAccessToken()) {
      fetchUser().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [fetchUser])

  const login = useCallback(async (username, password) => {
    const res = await apiLogin(username, password)
    setAccessToken(res.data.access)
    await fetchUser()
    return res.data
  }, [fetchUser])

  const logout = useCallback(() => {
    setAccessToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
