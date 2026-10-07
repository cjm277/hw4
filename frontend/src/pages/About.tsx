import { Link } from 'react-router-dom'
import { PHOTOS } from '../campusPhotos'

export default function About() {
  return (
    <>
      <section
        className="photo-banner photo-banner-tall"
        style={{ backgroundImage: `url("${PHOTOS.lawSchool.src}")` }}
      >
        <div className="container photo-banner-inner">
          <span className="eyebrow eyebrow-light">About us · Since 1975</span>
          <h1>We make the stuff you actually wear to class.</h1>
          <p>Family-run and right across from Yale on Broadway since 1975.</p>
        </div>
      </section>

      <div className="container section about">
        <section className="about-block reveal">
          <h2>Who we are</h2>
          <p>
            Campus Customs runs Yale Bulldog Blue, an officially licensed Yale shop based right on Broadway in New
            Haven. Basically, we wanted a place where you could grab a hoodie that's comfy enough for a late night in
            the library and still looks sharp at a game. So that's what we built.
          </p>
          <p>
            Everything we carry is officially licensed, from big block-letter tees to residential college quarter-zips
            and team crewnecks. Whether you're a student, an alum, or a parent who just dropped someone off at move-in,
            there's something here for you.
          </p>
        </section>

        <section className="about-block reveal">
          <h2>What we care about</h2>
          <ul className="about-list">
            <li>
              <strong>Comfort first.</strong> If it's not something you'd reach for on a lazy Sunday, it doesn't make the
              cut.
            </li>
            <li>
              <strong>Real Bulldog pride.</strong> Licensed designs that rep the school, your college, or your team.
            </li>
            <li>
              <strong>Straight answers.</strong> Our chat assistant pulls prices and stock right from our system, so
              if it says your size is there, it's there. If it isn't, it'll tell you.
            </li>
          </ul>
        </section>

        <section className="about-block reveal">
          <h2>Shipping &amp; returns, the short version</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3>Shipping</h3>
              <p>
                Most orders get made in 5–8 business days (a bit longer around big game weekends and holidays), then
                head out, usually via UPS. You'll get a tracking link once it ships. We ship internationally too, but
                customs fees and duties are on the buyer.
              </p>
            </div>
            <div className="info-card">
              <h3>Returns</h3>
              <p>
                You've got 30 days from the ship date to send things back, as long as they're unworn with the tags on.
                Refunds land in 2–10 business days depending on your bank. Original shipping isn't refunded, and
                custom pieces are final sale.
              </p>
            </div>
          </div>
        </section>

        <section className="about-block reveal">
          <h2>Find us</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3>The shop</h3>
              <p>
                57 Broadway
                <br />
                New Haven, CT 06511
              </p>
            </div>
            <div className="info-card">
              <h3>Get in touch</h3>
              <p>
                <a href="tel:+14753014205">(475) 301-4205</a>
                <br />
                <a href="mailto:orderdept@campuscustoms.com">orderdept@campuscustoms.com</a>
              </p>
            </div>
          </div>
        </section>

        <div className="about-cta">
          <Link to="/products" className="btn btn-primary">
            Start shopping
          </Link>
        </div>
      </div>
    </>
  )
}
