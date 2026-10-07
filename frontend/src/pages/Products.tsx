import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchCategories, fetchProducts, type Product } from '../api'
import { useChatResults } from '../chatResults'
import { PHOTOS } from '../campusPhotos'
import ProductCard from '../components/ProductCard'

type Sort = 'featured' | 'price-asc' | 'price-desc' | 'name'

export default function Products() {
  const [params, setParams] = useSearchParams()
  const category = params.get('category') ?? ''
  const [query, setQuery] = useState(params.get('q') ?? '')
  const [sort, setSort] = useState<Sort>('featured')
  const [categories, setCategories] = useState<string[]>([])
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState('')
  const { results: chatResults, clear: clearChatResults } = useChatResults()
  const chatView = params.get('view') === 'chat'

  // /products?view=chat with nothing to show (e.g. after a page refresh): fall back to the full catalogue.
  useEffect(() => {
    if (chatView && !chatResults) setParams({}, { replace: true })
  }, [chatView, chatResults, setParams])

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => setCategories([]))
  }, [])

  // Debounce typing, then load from the API.
  useEffect(() => {
    const q = query.trim()
    const handle = setTimeout(() => {
      setError('')
      fetchProducts({ q, category })
        .then(setProducts)
        .catch(() => setError("We couldn't load products. Is the backend running?"))
    }, 200)
    return () => clearTimeout(handle)
  }, [query, category])

  const sorted = useMemo(() => {
    if (!products) return null
    const list = [...products]
    if (sort === 'price-asc') list.sort((a, b) => a.price - b.price)
    if (sort === 'price-desc') list.sort((a, b) => b.price - a.price)
    if (sort === 'name') list.sort((a, b) => a.name.localeCompare(b.name))
    return list
  }, [products, sort])

  function pickCategory(next: string) {
    const p = new URLSearchParams(params)
    p.delete('view')
    if (next) p.set('category', next)
    else p.delete('category')
    setParams(p, { replace: true })
  }

  function showAllProducts() {
    clearChatResults()
    setParams({})
  }

  // Results the chat agent put on the page (ChatResponse.page). Same ProductCard -> same detail-page links.
  if (chatView && chatResults) {
    const n = chatResults.total_matches
    return (
      <div className="container section">
        <div className="chat-results-head">
          <div>
            <span className="eyebrow">From your chat</span>
            <h1>{chatResults.title}</h1>
            <p>
              {n} {n === 1 ? 'match' : 'matches'}, pulled live from our catalogue. Tap any card for the full details,
              sizes, and stock.
            </p>
          </div>
          <button className="btn btn-outline" onClick={showAllProducts}>
            Show all products
          </button>
        </div>
        <div className="product-grid">
          {chatResults.products.map((p, i) => (
            <ProductCard key={p.product_id} product={p} index={i} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <>
    <section
      className="photo-banner"
      style={{ backgroundImage: `url("${PHOTOS.lawTowers.src}")`, backgroundPosition: 'center 18%' }}
    >
      <div className="container photo-banner-inner">
        <span className="eyebrow eyebrow-light">The lineup</span>
        <h1>{category || 'All products'}</h1>
        <p>Every item is pulled live from our shop floor. Tap one for sizes and stock.</p>
      </div>
    </section>
    <div className="container section">

      <div className="toolbar">
        <input
          type="search"
          className="input"
          placeholder="Search (try “navy hoodie” or “baseball”)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search products"
        />
        <select className="input select" value={sort} onChange={(e) => setSort(e.target.value as Sort)} aria-label="Sort">
          <option value="featured">Sort: Featured</option>
          <option value="price-asc">Price, low to high</option>
          <option value="price-desc">Price, high to low</option>
          <option value="name">Alphabetical</option>
        </select>
      </div>

      <div className="chips" role="group" aria-label="Categories">
        <button className={`chip ${!category ? 'is-active' : ''}`} onClick={() => pickCategory('')}>
          All
        </button>
        {categories.map((c) => (
          <button key={c} className={`chip ${category === c ? 'is-active' : ''}`} onClick={() => pickCategory(c)}>
            {c}
          </button>
        ))}
      </div>

      {error && <p className="notice notice-error">{error}</p>}
      {!error && sorted === null && <p className="muted">Loading the lineup…</p>}
      {sorted && (
        <>
          <p className="muted result-count">
            {sorted.length} {sorted.length === 1 ? 'item' : 'items'}
          </p>
          {sorted.length === 0 ? (
            <p className="notice">Nothing matches that yet. Try a different search or category.</p>
          ) : (
            <div className="product-grid">
              {sorted.map((p, i) => (
                <ProductCard key={p.product_id} product={p} index={i} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
    </>
  )
}
