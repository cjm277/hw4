import { createContext, useContext } from 'react'
import type { ChatPage } from './api'

/** Products page URL for the "From your chat" view: /products?view=chat */
export const CHAT_VIEW_PATH = '/products?view=chat'

export type ChatResultsState = {
  /** The latest browse results the chat put on the page, or null. */
  results: ChatPage | null
  /** Show these results on the Products page (navigates there if needed). */
  show: (page: ChatPage) => void
  clear: () => void
}

export const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
