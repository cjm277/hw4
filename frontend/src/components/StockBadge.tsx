import type { Product } from '../api'

const ALL_SIZES = 6

/** "XS" -> "XS", ["XL","XXL"] -> "XL and XXL", ["XS","XL","XXL"] -> "XS, XL and XXL" */
function listSizes(sizes: string[]) {
  return sizes.length < 2 ? sizes.join('') : `${sizes.slice(0, -1).join(', ')} and ${sizes[sizes.length - 1]}`
}

/**
 * Size-level stock badges: orange "Only a few left in M" (1-5 left in a size) and red "Sold out in XS, XL and XXL".
 * Nothing when every size is well stocked.
 */
export default function StockBadges({
  product,
  small = false,
}: {
  product: Pick<Product, 'sizes_low' | 'sizes_sold_out'>
  small?: boolean
}) {
  const { sizes_low: low, sizes_sold_out: out } = product
  if (low.length === 0 && out.length === 0) return null
  const cls = `stock-badge${small ? ' stock-badge-sm' : ''}`
  return (
    <span className="stock-badges">
      {low.length > 0 && <span className={`${cls} stock-badge-few`}>Only a few left in {listSizes(low)}</span>}
      {out.length > 0 && (
        <span className={`${cls} stock-badge-out`}>
          {out.length === ALL_SIZES ? 'Sold out' : `Sold out in ${listSizes(out)}`}
        </span>
      )}
    </span>
  )
}
