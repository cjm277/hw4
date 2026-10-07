import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext'
import Logo from './Logo'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)
  const { user, logOut } = useAuth()
  const navigate = useNavigate()

  async function handleLogOut() {
    close()
    await logOut()
    navigate('/')
  }

  return (
    <header className="site-header">
      <div className="announcement" aria-label="Store announcements">
        <div className="announcement-track">
          {[0, 1].map((copy) => (
            <span key={copy} aria-hidden={copy === 1}>
              <b>Yale Bulldog Blue</b> · Officially licensed Yale gear · Shop in person at 57 Broadway, New Haven · 30-day
              returns on unworn gear · Ask our chat what&apos;s in stock in your size ·{' '}
            </span>
          ))}
        </div>
      </div>
      <nav className="nav container" aria-label="Main">
        <Link to="/" className="brand" onClick={close} aria-label="Campus Customs home">
          <Logo />
        </Link>

        <button
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="nav-links"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? 'Close' : 'Menu'}
        </button>

        <div id="nav-links" className={`nav-links ${open ? 'is-open' : ''}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className="nav-link" onClick={close}>
              {l.label}
            </NavLink>
          ))}
          <span className="nav-divider" aria-hidden="true" />
          {user ? (
            <>
              <span className="nav-greeting">Hi, {user.first_name}</span>
              <button className="btn btn-outline btn-sm" onClick={handleLogOut}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="nav-link" onClick={close}>
                Log In
              </NavLink>
              <NavLink to="/create-account" className="btn btn-primary btn-sm" onClick={close}>
                Create account
              </NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  )
}
