"""Customer memory: logged-in shoppers' chats are saved in chat_messages and loaded back on return.

Storage (the seed table, unchanged):
    chat_messages(id, user_id -> users.id, role 'user'|'assistant', content, products_json, created_at)
- One row per message. A chat turn = a 'user' row + an 'assistant' row, written in one transaction.
- products_json (assistant rows only): the product cards shown with that reply, as a JSON list.
  On reload, cards are rebuilt from the live catalogue by product_id, so prices/stock are current.
- Guests are never stored. Turns the provider's safety filter blocked are never stored either.
"""

import json

import catalog
from auth import db
from models import ChatResponse, ChatTurn, ProductCard, StoredMessage

AGENT_HISTORY_MESSAGES = 20  # most recent saved messages sent to the model as context
DISPLAY_HISTORY_MESSAGES = 60  # most recent saved messages shown in the chat widget


def init_db() -> None:
    with db() as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")


def _recent_rows(user_id: int, limit: int) -> list:
    with db() as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at FROM chat_messages
            WHERE user_id = ? AND role IN ('user', 'assistant')
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))  # oldest first


def _cards(products_json: str | None) -> list[ProductCard]:
    if not products_json:
        return []
    try:
        ids = [p["product_id"] for p in json.loads(products_json) if isinstance(p, dict) and "product_id" in p]
    except (ValueError, TypeError):
        return []
    return [ProductCard(**catalog.card(p)) for p in catalog.get_many(ids)]


def _product_names(products_json: str | None) -> list[str]:
    try:
        items = json.loads(products_json) if products_json else []
        return [f"{p['name']} ({p['product_id']})" for p in items if isinstance(p, dict) and "product_id" in p]
    except (ValueError, TypeError, KeyError):
        return []


def recent_turns(user_id: int) -> list[ChatTurn]:
    """The shopper's saved conversation, as the agent's message history.

    Assistant turns get a note listing the product cards they showed, so the agent remembers *which*
    items were discussed (e.g. what "this" was on a product page) on the shopper's next visit.
    """
    turns = []
    for r in _recent_rows(user_id, AGENT_HISTORY_MESSAGES):
        content = r["content"]
        if r["role"] == "assistant" and (names := _product_names(r["products_json"])):
            content += "\n[Product cards shown: " + "; ".join(names) + "]"
        turns.append(ChatTurn(role=r["role"], content=content[:4000]))
    return turns


def load_history(user_id: int) -> list[StoredMessage]:
    """The shopper's saved conversation, for the chat widget to show when they come back."""
    return [
        StoredMessage(role=r["role"], content=r["content"], products=_cards(r["products_json"]), created_at=r["created_at"])
        for r in _recent_rows(user_id, DISPLAY_HISTORY_MESSAGES)
    ]


def save_turn(user_id: int, message: str, response: ChatResponse) -> None:
    products_json = json.dumps([c.model_dump() for c in response.products]) if response.products else None
    with db() as conn:  # one transaction: both rows or neither
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, response.reply or response.privacy_notice or "", products_json),
        )
