import { useEffect, useState } from 'react'
import { fetchSimilar, type SimilarItem } from '../api'
import ProductCard from './ProductCard'

/** "You might also like": a row of items in the same category and/or the same main colour. */
export default function SimilarItems({ productId }: { productId: string }) {
  const [result, setResult] = useState<{ id: string; items: SimilarItem[] }>()

  useEffect(() => {
    fetchSimilar(productId)
      .then((items) => setResult({ id: productId, items }))
      .catch(() => setResult({ id: productId, items: [] }))
  }, [productId])

  const items = result?.id === productId ? result.items : []
  if (items.length === 0) return null

  return (
    <section className="similar" aria-labelledby="similar-heading">
      <h2 id="similar-heading">You might also like</h2>
      <p className="muted">Picked from the same category or a similar colour.</p>
      <div className="similar-row">
        {items.map((p, i) => (
          <ProductCard key={p.product_id} product={p} note={p.reason} index={i} />
        ))}
      </div>
    </section>
  )
}
