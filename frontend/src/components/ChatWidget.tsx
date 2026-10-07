import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, matchPath, useLocation } from 'react-router-dom'
import { fetchChatHistory, formatPrice, sendChatMessage, type ChatMessage } from '../api'
import { useAuth } from '../authContext'
import { OPEN_CHAT_EVENT } from '../chatEvents'
import { useChatResults } from '../chatResults'
import StockBadges from './StockBadge'

/** `omit`: shown in the chat but never sent back as history (failed or filter-blocked turns). */
type UiMessage = ChatMessage & { error?: boolean; omit?: boolean; privacy?: boolean }

/** Messages belong to whoever was signed in (null = guest), so logging in/out never mixes conversations. */
type ChatState = { owner: number | null; messages: UiMessage[] }
const NO_MESSAGES: UiMessage[] = []

/** Render **bold** (older saved replies use it); everything else stays plain text. */
function renderText(content: string) {
  return content.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

export default function ChatWidget() {
  const { user } = useAuth()
  const { show: showOnPage } = useChatResults()
  const { pathname, search } = useLocation()
  // Page context sent with every message, so "do you have this in pink?" works on a product page.
  const viewingProductId = matchPath('/products/:productId', pathname)?.params.productId ?? null
  const [open, setOpen] = useState(false)
  const owner = user?.id ?? null
  const [chat, setChat] = useState<ChatState>({ owner: null, messages: [] })
  const messages = chat.owner === owner ? chat.messages : NO_MESSAGES
  // Logged in but their saved chat hasn't arrived yet.
  const loadingHistory = owner !== null && chat.owner !== owner
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const greeting: UiMessage = {
    role: 'assistant',
    content:
      user && messages.length > 0
        ? `Welcome back, ${user.first_name}! Here's our chat from before. Pick up wherever you like.`
        : `Hey${user ? ` ${user.first_name}` : ''}! I'm the Campus Customs assistant. Ask me about our gear, sizes, or what's in stock.`,
  }

  /** Update the current owner's messages (drops anything left over from a different user). */
  const updateMessages = (fn: (m: UiMessage[]) => UiMessage[]) =>
    setChat((c) => ({ owner, messages: fn(c.owner === owner ? c.messages : []) }))

  // Customer memory: when someone logs in (or returns already logged in), reload their saved chat.
  useEffect(() => {
    if (owner === null) return
    let cancelled = false
    fetchChatHistory()
      .then((saved) => !cancelled && setChat({ owner, messages: saved }))
      .catch(() => !cancelled && setChat({ owner, messages: [] }))
    return () => {
      cancelled = true
    }
  }, [owner])

  useEffect(() => {
    const onOpen = (e: Event) => {
      const draft = (e as CustomEvent<{ draft?: string }>).detail?.draft
      setOpen(true)
      if (draft) setInput(draft)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
    window.addEventListener(OPEN_CHAT_EVENT, onOpen)
    return () => window.removeEventListener(OPEN_CHAT_EVENT, onOpen)
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || sending || loadingHistory) return
    const history = messages.filter((m) => !m.omit)
    updateMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    // Drop the shopper's message too, so a failed/blocked turn doesn't poison later turns.
    const omitLastUser = (m: UiMessage[]) => m.map((msg, i) => (i === m.length - 1 ? { ...msg, omit: true } : msg))
    try {
      const reply = await sendChatMessage(text, history, { path: pathname + search, product_id: viewingProductId })
      updateMessages((m) => {
        if (reply.blocked) return [...omitLastUser(m), { ...reply, omit: true }]
        // Sensitive-data guard: swap the shopper's bubble for the blanked-out version and show the notice.
        const shown = reply.redactedMessage
          ? m.map((msg, i) => (i === m.length - 1 ? { ...msg, content: reply.redactedMessage! } : msg))
          : m
        const notice: UiMessage[] = reply.privacyNotice
          ? [{ role: 'assistant', content: reply.privacyNotice, privacy: true, omit: true }]
          : []
        return [...shown, ...notice, ...(reply.content ? [reply] : [])]
      })
      if (reply.page) showOnPage(reply.page) // browse question -> update the page with every match
    } catch (err) {
      const content = (err as Error).message || "Sorry, I couldn't reach the shop just now. Mind trying again?"
      updateMessages((m) => [...omitLastUser(m), { role: 'assistant', content, error: true, omit: true }])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat">
          <header className="chat-header">
            <span className="chat-avatar" aria-hidden="true">
              C
            </span>
            <div className="chat-header-text">
              <strong>Campus Customs Assistant</strong>
              <small>{user ? 'Your chat is saved to your account' : 'Prices and stock straight from our shop'}</small>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
              ×
            </button>
          </header>

          <div className="chat-messages" ref={listRef}>
            {[greeting, ...messages].map((m, i) => (
              <div
                key={i}
                className={`chat-msg chat-msg-${m.role}${m.error ? ' chat-msg-error' : ''}${m.privacy ? ' chat-msg-privacy' : ''}`}
                role={m.privacy ? 'status' : undefined}
              >
                {m.privacy && <span className="chat-privacy-label">Privacy notice</span>}
                <p>{renderText(m.content)}</p>
                {m.page && (
                  <button className="chat-page-link" onClick={() => showOnPage(m.page!)}>
                    See all {m.page.total_matches} on the page →
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                        <img src={p.image_url} alt="" />
                        <span>
                          {p.name}
                          <strong>{formatPrice(p.price)}</strong>
                          <StockBadges product={p} small />
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loadingHistory && <p className="chat-loading">Loading your saved chat…</p>}
            {sending && (
              <div className="chat-msg chat-msg-assistant chat-typing" aria-label="Assistant is typing">
                <span />
                <span />
                <span />
              </div>
            )}
          </div>

          <form className="chat-form" onSubmit={handleSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about hoodies, sizes, stock..."
              aria-label="Chat message"
            />
            <button
              className="chat-send"
              disabled={!input.trim() || sending || loadingHistory}
              aria-label="Send message"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path d="M3 11.5 20 4l-7.5 17-2.2-7.3L3 11.5z" fill="currentColor" />
              </svg>
            </button>
          </form>
        </section>
      )}

      <button
        className="chat-launcher"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? (
          '×'
        ) : (
          <>
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
              <path
                d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4h0A2.5 2.5 0 0 1 3 13.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinejoin="round"
              />
            </svg>
            Chat with us
          </>
        )}
      </button>
    </div>
  )
}
