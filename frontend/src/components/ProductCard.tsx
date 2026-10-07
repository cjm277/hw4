import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { formatPrice, type Product } from '../api'
import StockBadges from './StockBadge'

/** One product card. Used on Home, Products, chat results, and "You might also like". Links to the item page. */
export default function ProductCard({ product, note, index = 0 }: { product: Product; note?: string; index?: number }) {
  return (
    <Link
      to={`/products/${product.product_id}`}
      className="product-card reveal"
      style={{ '--i': Math.min(index, 11) } as CSSProperties}
    >
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        <span className="product-card-cta" aria-hidden="true">
          View details →
        </span>
      </div>
      <div className="product-card-body">
        <span className="eyebrow">{product.category}</span>
        <h3>{product.name}</h3>
        {note && <span className="product-card-note">{note}</span>}
        {product.description && <p className="product-card-desc">{product.description}</p>}
        <div className="product-card-foot">
          <span className="price">{formatPrice(product.price)}</span>
          <StockBadges product={product} />
        </div>
      </div>
    </Link>
  )
}
