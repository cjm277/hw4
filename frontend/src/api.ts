// Client for the Campus Customs FastAPI backend (backend/main.py).
// Vite proxies /api and /images to http://127.0.0.1:8000 in dev.

export type Product = {
  product_id: string
  name: string
  garment_type: string
  category: string
  description: string
  colors: string[]
  price: number
  image_url: string
  total_stock: number
  /** Sizes with only a few left (1-5), XS->XXL. */
  sizes_low: string[]
  /** Sizes with none left, XS->XXL. */
  sizes_sold_out: string[]
}

/** "You might also like" suggestion (GET /api/products/{id}/similar). */
export type SimilarItem = Product & { reason: string }

export type SizeStock = { size: string; quantity: number }

export type ProductDetail = Product & {
  search_tags: string[]
  sizes: SizeStock[]
}

/** The filters the agent chose for a browse question (mirrors backend models.PageSearch). */
export type PageSearch = {
  title: string
  query: string
  category: string | null
  color: string | null
  max_price: number | null
  size_in_stock: string | null
}

/** Browse results from the chat, rendered as a product grid on the Products page (models.ChatPage). */
export type ChatPage = {
  title: string
  total_matches: number
  search: PageSearch
  products: Product[]
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  /** Specific items -> small cards inside the chat. Built from the DB by the backend. */
  products?: Product[]
  /** Browse results -> product grid on the page. */
  page?: ChatPage | null
  /** The provider's safety filter refused this turn. */
  blocked?: boolean
  /** Sensitive-data guard: notice to show, and the shopper's message with the secret blanked out. */
  privacyNotice?: string | null
  redactedMessage?: string | null
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(res.status === 404 ? 'Not found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export function fetchProducts(params: { q?: string; category?: string } = {}): Promise<Product[]> {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.category) search.set('category', params.category)
  const qs = search.toString()
  return getJson<Product[]>(`/api/products${qs ? `?${qs}` : ''}`)
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

export function fetchSimilar(productId: string): Promise<SimilarItem[]> {
  return getJson<SimilarItem[]>(`/api/products/${encodeURIComponent(productId)}/similar`)
}

export function fetchCategories(): Promise<string[]> {
  return getJson<string[]>('/api/categories')
}

// ---------- Accounts (backend/auth.py) ----------
// The session lives in an HttpOnly cookie, so the browser sends it automatically.

export type User = {
  id: number
  first_name: string
  last_name: string
  email: string
}

export type SignUpInput = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new Error(detail)
  }
  return data as T
}

export function signUp(input: SignUpInput): Promise<User> {
  return postJson<User>('/api/auth/signup', input)
}

export function logIn(email: string, password: string): Promise<User> {
  return postJson<User>('/api/auth/login', { email, password })
}

export function logOut(): Promise<{ ok: boolean }> {
  return postJson('/api/auth/logout')
}

export async function fetchMe(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  return res.ok ? ((await res.json()) as User) : null
}

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

// ---------- Chat (backend/agent.py via POST /api/chat) ----------

/** Send one shopper message plus the earlier turns; get the agent's reply, chat cards, and any page of results. */
/** Where the shopper is when they send a message (models.PageContext). */
export type PageContext = { path: string; product_id: string | null }

export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  page: PageContext,
): Promise<ChatMessage> {
  const res = await postJson<{
    reply: string
    products: Product[]
    page: ChatPage | null
    blocked: boolean
    privacy_notice: string | null
    redacted_message: string | null
  }>(
    '/api/chat',
    {
      message,
      // Guests: this visit's turns. Logged in: the server ignores this and uses the saved history.
      history: history.map(({ role, content }) => ({ role, content })),
      page,
    },
  )
  return {
    role: 'assistant',
    content: res.reply,
    products: res.products,
    page: res.page,
    blocked: res.blocked,
    privacyNotice: res.privacy_notice,
    redactedMessage: res.redacted_message,
  }
}

/** The logged-in shopper's saved chat (GET /api/chat/history), oldest first. */
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const data = await getJson<{ messages: { role: 'user' | 'assistant'; content: string; products: Product[] }[] }>(
    '/api/chat/history',
  )
  return data.messages.map((m) => ({ role: m.role, content: m.content, products: m.products }))
}
