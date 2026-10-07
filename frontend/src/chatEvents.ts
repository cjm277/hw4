export const OPEN_CHAT_EVENT = 'cc:open-chat'

/** Open the chat panel from anywhere, optionally pre-filling the input. */
export function openChat(draft?: string) {
  window.dispatchEvent(new CustomEvent(OPEN_CHAT_EVENT, { detail: { draft } }))
}
