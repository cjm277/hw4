import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Scroll motion: any element with class "reveal" fades up the first time it scrolls into view.
 * Watches for elements added later (e.g. product grids that load after a fetch).
 * Skipped entirely when the shopper prefers reduced motion (the CSS shows everything immediately).
 */
export function useReveal() {
  const { pathname, search } = useLocation()

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
      document.documentElement.classList.add('no-motion')
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible')
            io.unobserve(e.target)
          }
        }
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.08 },
    )
    const watch = () => document.querySelectorAll('.reveal:not(.is-visible)').forEach((el) => io.observe(el))
    watch()
    const mo = new MutationObserver(watch)
    mo.observe(document.body, { childList: true, subtree: true })
    return () => {
      io.disconnect()
      mo.disconnect()
    }
  }, [pathname, search])
}
