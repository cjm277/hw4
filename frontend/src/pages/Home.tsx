import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type Product } from '../api'
import { PHOTOS } from '../campusPhotos'
import { openChat } from '../chatEvents'
import ProductCard from '../components/ProductCard'

const FEATURED_IDS = [
  'big-yale-tri-blend-t-shirt',
  'basic-hoodie-big-yale',
  'brooks-brothers-bomber-jacket-yale',
  'baseball-left-chest-crewneck',
]

// Each category tile is fronted by one real product from that category.
const CATEGORY_TILES = [
  { name: 'T-Shirts', blurb: 'Easy everyday tees', cover: 'big-yale-tri-blend-t-shirt' },
  { name: 'Hoodies', blurb: 'For the 8am walk to class', cover: 'basic-hoodie-big-yale' },
  { name: 'Crewnecks', blurb: 'The classic, done right', cover: 'baseball-left-chest-crewneck' },
  { name: 'Quarter-Zips', blurb: 'Interview-ready layers', cover: 'branford-1-4-zip' },
  { name: 'Jackets', blurb: 'New Haven winter, handled', cover: 'brooks-brothers-bomber-jacket-yale' },
]

export default function Home() {
  const [all, setAll] = useState<Product[]>([])

  useEffect(() => {
    fetchProducts()
      .then(setAll)
      .catch(() => setAll([]))
  }, [])

  const byId = new Map(all.map((p) => [p.product_id, p]))
  const featured = FEATURED_IDS.map((id) => byId.get(id)).filter((p): p is Product => Boolean(p))

  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <span className="eyebrow eyebrow-light hero-rise">Officially licensed · New Haven, CT · Est. 1975</span>
            <h1 className="hero-rise">
              Bulldog gear that keeps up with <em>your day.</em>
            </h1>
            <p className="hero-rise">
              Hoodies for the early lecture, tees for game day, quarter-zips for when you need to look like you have it
              together. Browse the lineup, or just ask our chat assistant -&gt; it'll tell you straight up what's in
              stock in your size.
            </p>
            <div className="hero-actions hero-rise">
              <Link to="/products" className="btn btn-light">
                Shop all products
              </Link>
              <button className="btn btn-outline-light" onClick={() => openChat()}>
                Ask the chat
              </button>
            </div>
          </div>
          <figure className="hero-arch hero-rise">
            <img src={PHOTOS.harkness.src} alt={PHOTOS.harkness.alt} />
            <figcaption>Harkness Tower, a short walk from our shop</figcaption>
          </figure>
        </div>
      </section>

      <section className="container section reveal">
        <div className="section-head">
          <div>
            <span className="eyebrow">Shop by category</span>
            <h2>What are you after?</h2>
          </div>
        </div>
        <div className="category-grid">
          {CATEGORY_TILES.map((c) => {
            const cover = byId.get(c.cover)
            return (
              <Link key={c.name} to={`/products?category=${encodeURIComponent(c.name)}`} className="category-tile">
                <span className="category-tile-img">{cover && <img src={cover.image_url} alt="" loading="lazy" />}</span>
                <span className="category-tile-text">
                  <strong>{c.name}</strong>
                  <span>{c.blurb}</span>
                </span>
              </Link>
            )
          })}
        </div>
      </section>

      <section className="container section reveal">
        <div className="section-head">
          <div>
            <span className="eyebrow">Crowd favorites</span>
            <h2>What New Haven is wearing</h2>
          </div>
          <Link to="/products" className="text-link">
            See everything →
          </Link>
        </div>
        <div className="product-grid">
          {featured.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      </section>

      <section className="gameday reveal" style={{ backgroundImage: `url("${PHOTOS.yaleBowl.src}")` }}>
        <div className="container gameday-inner">
          <span className="eyebrow eyebrow-light">Game day at the Bowl</span>
          <h2>Game day looks better in Bulldog Blue.</h2>
          <p>Tees, crewnecks, and hoodies built for tailgates, The Game, and every Saturday in between.</p>
          <div className="hero-actions">
            <Link to="/products?category=T-Shirts" className="btn btn-light">
              Shop game-day tees
            </Link>
            <Link to="/products?category=Hoodies" className="btn btn-outline-light">
              Hoodies for the cold seats
            </Link>
          </div>
        </div>
      </section>

      <section className="value-strip reveal">
        <div className="container value-grid">
          <div>
            <span className="value-icon" aria-hidden="true">✓</span>
            <strong>Officially licensed</strong>
            <span>The real deal, approved by Yale.</span>
          </div>
          <div>
            <span className="value-icon" aria-hidden="true">◎</span>
            <strong>Honest stock info</strong>
            <span>Sizes and counts come straight from our shop floor.</span>
          </div>
          <div>
            <span className="value-icon" aria-hidden="true">↺</span>
            <strong>30-day returns</strong>
            <span>Unworn with tags? Send it back, no drama.</span>
          </div>
        </div>
      </section>

      <section className="container section visit reveal">
        <figure className="visit-photo">
          <img src={PHOTOS.sterlingLibrary.src} alt={PHOTOS.sterlingLibrary.alt} loading="lazy" />
        </figure>
        <div className="visit-copy">
          <span className="eyebrow">Visit the shop</span>
          <h2>Come say hi in person</h2>
          <p>
            Want to try it on first? Swing by the shop at <strong>57 Broadway, New Haven</strong>. It's right in the
            middle of campus, a short walk from Sterling Library, so it's an easy stop between classes.
          </p>
          <Link to="/about" className="btn btn-primary">
            More about us
          </Link>
        </div>
      </section>
    </>
  )
}
