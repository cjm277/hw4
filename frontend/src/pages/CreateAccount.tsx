import { useState, type ChangeEvent, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext'
import AuthShell from '../components/AuthShell'
import SignedInCard from '../components/SignedInCard'

// Mirrors backend/auth.py (the server enforces these too).
const MIN_PASSWORD = 6

export default function CreateAccount() {
  const { user, signUp } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ firstName: '', lastName: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (form.password.length < MIN_PASSWORD) return setError(`Password needs at least ${MIN_PASSWORD} characters.`)
    if (form.password !== form.confirm) return setError("Passwords don't match.")
    setError('')
    setSubmitting(true)
    try {
      await signUp({
        first_name: form.firstName,
        last_name: form.lastName,
        email: form.email,
        password: form.password,
        confirm_password: form.confirm,
      })
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
      <h1>Create your account</h1>
      <p className="muted">Save your chats and get help that remembers what you were looking at.</p>
      <form onSubmit={handleSubmit} className="form">
        <div className="form-row">
          <label>
            First name
            <input className="input" required autoComplete="given-name" value={form.firstName} onChange={update('firstName')} />
          </label>
          <label>
            Last name
            <input className="input" required autoComplete="family-name" value={form.lastName} onChange={update('lastName')} />
          </label>
        </div>
        <label>
          Email
          <input className="input" type="email" required autoComplete="email" value={form.email} onChange={update('email')} />
        </label>
        <label>
          Password
          <input
            className="input"
            type="password"
            required
            autoComplete="new-password"
            value={form.password}
            onChange={update('password')}
          />
        </label>
        <label>
          Confirm password
          <input
            className="input"
            type="password"
            required
            autoComplete="new-password"
            value={form.confirm}
            onChange={update('confirm')}
          />
        </label>
        <button className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}
      <p className="muted small">
        Already have one? <Link to="/login">Log in</Link>
      </p>
    </AuthShell>
  )
}
