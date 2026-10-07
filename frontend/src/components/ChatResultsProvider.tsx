import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import type { ChatPage } from '../api'
import { CHAT_VIEW_PATH, ChatResultsContext, type ChatResultsState } from '../chatResults'

/** Holds the chat's latest browse results so the Products page can render them as cards. */
export default function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ChatPage | null>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const onChatView = location.pathname === '/products' && new URLSearchParams(location.search).get('view') === 'chat'

  const show = useCallback(
    (page: ChatPage) => {
      setResults(page)
      if (!onChatView) navigate(CHAT_VIEW_PATH)
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },
    [navigate, onChatView],
  )

  const clear = useCallback(() => setResults(null), [])

  const value = useMemo<ChatResultsState>(() => ({ results, show, clear }), [results, show, clear])
  return <ChatResultsContext.Provider value={value}>{children}</ChatResultsContext.Provider>
}
