import { createContext, useContext } from 'react'
import type { SignUpInput, User } from './api'

export type AuthState = {
  user: User | null
  loading: boolean
  logIn: (email: string, password: string) => Promise<User>
  signUp: (input: SignUpInput) => Promise<User>
  logOut: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
