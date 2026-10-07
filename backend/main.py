"""Campus Customs API: products, images, accounts (auth.py), and the shop chatbot (agent.py).

Run from the backend/ folder (with hw4/.venv active):
    uvicorn main:app --reload --port 8000
"""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic_ai.exceptions import UsageLimitExceeded

import audit
import auth
import catalog
import guard
import memory
from agent import AgentNotConfigured, run_chat
from models import ChatHistory, ChatRequest, ChatResponse, ChatTurn, SimilarItem

log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
auth.init_db()
memory.init_db()
app.include_router(auth.router)
# Only the product image folder is public, never the data/ folder (it holds the DB).
app.mount("/images", StaticFiles(directory=catalog.PRODUCTS_DIR), name="images")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/categories")
def categories() -> list[str]:
    return catalog.CATEGORIES


@app.get("/api/products")
def list_products(q: str | None = None, category: str | None = None) -> list[dict]:
    return [catalog.card(p) for p in catalog.search(q=q, category=category)]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    product = catalog.get(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/products/{product_id}/similar")
def similar_products(product_id: str, limit: int = 4) -> list[SimilarItem]:
    """'You might also like' for the item page: same category and/or same main colour."""
    if catalog.get(product_id) is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return [SimilarItem(**catalog.card(p), reason=reason) for p, reason in catalog.similar(product_id, min(limit, 8))]


@app.get("/api/chat/history")
def chat_history(request: Request) -> ChatHistory:
    """The logged-in shopper's saved chat, so the widget can reload it when they come back."""
    user = auth.current_user(request)
    if user is None:
        raise HTTPException(401, "Log in to see your saved chat.")
    return ChatHistory(messages=memory.load_history(user["id"]))


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    """One chat turn: message + page context in; reply, chat cards, and (for browsing) a page of results out.

    Logged in: history comes from chat_messages (the browser's copy is ignored) and the turn is saved.
    Guest: history is whatever the browser sends for this visit, and nothing is saved.

    Sensitive-data guard runs FIRST: card numbers, passwords, etc. are blanked out of the message (and of any
    guest history) before anything reaches the model, the database, or the logs.

    Every turn, whatever the outcome, is appended to output/audit_trail.json (see audit.py).
    """
    user = auth.current_user(request)
    scrubbed = guard.scrub(body.message)
    if user:
        history = memory.recent_turns(user["id"])
    else:
        history = [ChatTurn(role=t.role, content=guard.scrub(t.content).text) for t in body.history]

    turn = audit.TurnAudit(user_id=user["id"] if user else None, page=body.page.path[:120], message=scrubbed.text)
    if scrubbed.redacted:
        turn.safety.append("guard_redacted: " + ", ".join(dict.fromkeys(scrubbed.found)))
    if audit.injection_suspected(scrubbed.text):
        turn.safety.append("possible_prompt_injection")
    if any(audit.injection_suspected(t.content) for t in body.history if not user):
        turn.safety.append("possible_prompt_injection_in_history")

    try:
        if scrubbed.needs_model:
            response = await run_chat(scrubbed.text, history, user, body.page, turn)
        else:  # the message was basically just the secret: nothing to ask the model
            response = ChatResponse(reply="")
            turn.stop("guard_only_model_skipped")
    except AgentNotConfigured as e:
        log.error("Chat unavailable: %s", e)
        turn.stop("not_configured")
        _write_audit(turn)
        raise HTTPException(503, "The chat assistant isn't set up yet. Please try again later.")
    except UsageLimitExceeded:
        log.warning("Chat turn hit the model-request limit")
        turn.stop("usage_limit_exceeded")
        _write_audit(turn)
        raise HTTPException(502, "Sorry, that one took too many steps. Could you ask it a simpler way?")
    except Exception as e:
        log.exception("Chat turn failed")
        turn.stop(f"error: {type(e).__name__}")
        _write_audit(turn)
        raise HTTPException(502, "Sorry, I hit a snag answering that. Mind trying again?")
    if scrubbed.redacted:
        response.privacy_notice = scrubbed.notice()
        response.redacted_message = scrubbed.text
    if user and not response.blocked:
        try:
            memory.save_turn(user["id"], scrubbed.text, response)  # never the raw message
        except Exception:
            log.exception("Saving chat history failed")  # the shopper still gets their answer

    turn.reply = response.reply or response.privacy_notice or ""
    turn.product_ids = [p.product_id for p in response.products]
    turn.page_results = response.page.total_matches if response.page else None
    _write_audit(turn)
    return response


def _write_audit(turn: audit.TurnAudit) -> None:
    try:
        turn.write()
    except Exception:
        log.exception("Writing the audit trail failed")  # never break the chat over logging
