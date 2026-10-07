import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import * as api from '../api'
import { AuthContext, type AuthState } from '../authContext'

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<api.User | null>(null)
  const [loading, setLoading] = useState(true)

  // Restore the session from the cookie on first load.
  useEffect(() => {
    api
      .fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const logIn = useCallback(async (email: string, password: string) => {
    const u = await api.logIn(email, password)
    setUser(u)
    return u
  }, [])

  const signUp = useCallback(async (input: api.SignUpInput) => {
    const u = await api.signUp(input)
    setUser(u)
    return u
  }, [])

  const logOut = useCallback(async () => {
    await api.logOut()
    setUser(null)
  }, [])

  const value = useMemo<AuthState>(
    () => ({ user, loading, logIn, signUp, logOut }),
    [user, loading, logIn, signUp, logOut],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
