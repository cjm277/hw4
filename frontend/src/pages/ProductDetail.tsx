import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, type ProductDetail as Detail } from '../api'
import { openChat } from '../chatEvents'
import SimilarItems from '../components/SimilarItems'

const LOW_STOCK = 5

function stockLabel(quantity: number) {
  if (quantity === 0) return 'Sold out'
  if (quantity <= LOW_STOCK) return `Only ${quantity} left`
  return `${quantity} in stock`
}

export default function ProductDetail() {
  const { productId = '' } = useParams()
  // Results are tagged with the id they belong to, so a stale result reads as "loading".
  const [result, setResult] = useState<{ id: string; product?: Detail; error?: string }>()

  useEffect(() => {
    fetchProduct(productId)
      .then((product) => setResult({ id: productId, product }))
      .catch((e: Error) =>
        setResult({
          id: productId,
          error: e.message === 'Not found' ? "We couldn't find that product." : "We couldn't load this product.",
        }),
      )
  }, [productId])

  const current = result?.id === productId ? result : undefined
  const product = current?.product
  const error = current?.error

  if (error) {
    return (
      <div className="container section">
        <p className="notice notice-error">{error}</p>
        <Link to="/products" className="text-link">
          ← Back to all products
        </Link>
      </div>
    )
  }
  if (!product) return <div className="container section muted">Loading…</div>

  return (
    <div className="container section">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link to="/products">Products</Link>
        <span>/</span>
        <Link to={`/products?category=${encodeURIComponent(product.category)}`}>{product.category}</Link>
        <span>/</span>
        <span aria-current="page">{product.name}</span>
      </nav>

      <div className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <span className="eyebrow">{product.garment_type}</span>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>

          {product.description && <p className="detail-desc">{product.description}</p>}

          {product.colors.length > 0 && (
            <>
              <h2 className="detail-label">Colors</h2>
              <div className="color-list">
                {product.colors.map((c) => (
                  <span key={c} className="color-pill">
                    {c}
                  </span>
                ))}
              </div>
            </>
          )}

          <h2 className="detail-label">Sizes &amp; stock</h2>
          <ul className="size-grid">
            {product.sizes.map((s) => (
              <li
                key={s.size}
                className={`size-cell ${s.quantity === 0 ? 'is-out' : s.quantity <= LOW_STOCK ? 'is-low' : ''}`}
              >
                <strong>{s.size}</strong>
                <span>{stockLabel(s.quantity)}</span>
              </li>
            ))}
          </ul>
          <p className="muted small">
            {product.total_stock > 0 ? `${product.total_stock} total across all sizes.` : 'Sold out in every size.'}
          </p>

          <button className="btn btn-primary btn-block" onClick={() => openChat(`Tell me more about the ${product.name}`)}>
            Ask the chat about this
          </button>

          {product.search_tags.length > 0 && (
            <div className="tag-list">
              {product.search_tags.map((t) => (
                <span key={t} className="tag">
                  #{t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      <SimilarItems productId={product.product_id} />
    </div>
  )
}
