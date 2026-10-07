import { Link } from 'react-router-dom'
import { useAuth } from '../authContext'
import AuthShell from './AuthShell'

/** Shown on Log In / Create account when someone is already signed in. */
export default function SignedInCard() {
  const { user, logOut } = useAuth()
  if (!user) return null
  return (
    <AuthShell>
      <h1>You're logged in</h1>
      <p className="muted">
        Signed in as <strong>{user.email}</strong>.
      </p>
      <div className="form">
        <Link to="/products" className="btn btn-primary btn-block">
          Keep shopping
        </Link>
        <button className="btn btn-outline btn-block" onClick={() => logOut()}>
          Log out
        </button>
      </div>
    </AuthShell>
  )
}
