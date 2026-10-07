import { Link } from 'react-router-dom'
import { PHOTO_LIST } from '../campusPhotos'
import Logo from './Logo'

const YEAR = new Date().getFullYear()

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div>
          <Logo variant="light" />
          <p className="footer-tagline">
            Officially licensed Yale Bulldog Blue gear, made for New Haven and everyone who calls it home.
          </p>
        </div>
        <div>
          <h4>Shop</h4>
          <Link to="/products">All products</Link>
          <Link to="/about">About us</Link>
          <Link to="/create-account">Create account</Link>
        </div>
        <div>
          <h4>Visit</h4>
          <p>
            57 Broadway
            <br />
            New Haven, CT 06511
          </p>
        </div>
        <div>
          <h4>Contact</h4>
          <a href="tel:+14753014205">(475) 301-4205</a>
          <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© {YEAR} Campus Customs · Yale Bulldog Blue</span>
        <details className="photo-credits">
          <summary>Campus photo credits</summary>
          <ul>
            {PHOTO_LIST.map((p) => (
              <li key={p.source}>
                <a href={p.source} target="_blank" rel="noreferrer">
                  {p.alt.split(' ').slice(0, 4).join(' ')}…
                </a>{' '}
                by {p.credit} ({p.license}), via Wikimedia Commons
              </li>
            ))}
          </ul>
        </details>
      </div>
    </footer>
  )
}
