import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext'
import AuthShell from '../components/AuthShell'
import SignedInCard from '../components/SignedInCard'

export default function LogIn() {
  const { user, logIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await logIn(email, password)
      navigate('/')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (user) return <SignedInCard />

  return (
    <AuthShell>
      <h1>Welcome back</h1>
      <p className="muted">Log in to pick up your chat where you left off.</p>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Email
          <input
            className="input"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            className="input"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log In'}
        </button>
      </form>
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      <p className="muted small">
        New here? <Link to="/create-account">Create an account</Link>
      </p>
    </AuthShell>
  )
}
