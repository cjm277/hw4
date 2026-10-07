"""Campus Customs shop agent: PydanticAI wiring.

- Model: OPENAI_MODEL from the root .env, called through Portkey with PORTKEY_API_KEY.
- Instructions: prompts/prompt.md, re-read on every chat turn, so prompt edits apply without a restart.
- Deps: models.ChatDeps = who is chatting (Customer, or None for guests) + where they are (PageInfo).
- Tools: tools.py (search, description, price, stock, customer profile; all read-only).
- Output: models.ChatReply (reply text + product ids + optional page_search). Product cards, and the
  page of search results, are then built from the database, never from the model, so prices and stock
  on every card are real.
"""

import os
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

import catalog  # noqa: E402
from audit import TurnAudit  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from models import (  # noqa: E402
    ChatDeps,
    ChatPage,
    ChatReply,
    ChatResponse,
    ChatTurn,
    Customer,
    PageContext,
    PageInfo,
    PageSearch,
    ProductCard,
    ViewingProduct,
)
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, RunContext  # noqa: E402
from pydantic_ai.exceptions import ModelHTTPError  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart  # noqa: E402
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402
from tools import TOOLS  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# Nearest .env wins (load_dotenv never overrides a variable that is already set).
for folder in (BACKEND_DIR, *BACKEND_DIR.parents):
    if (folder / ".env").is_file():
        load_dotenv(folder / ".env")

PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
MAX_MODEL_REQUESTS = 8  # per chat turn (tool calls + final answer)
HISTORY_TURNS = 20  # most recent messages sent back to the model
PAGE_NAMES = {"/": "Home", "/products": "Products", "/about": "About Us", "/login": "Log In", "/create-account": "Create account"}
BLOCKED_REPLY = (
    "I can only help with Campus Customs stuff: our gear, sizes, stock, and store info. "
    "What are you shopping for today?"
)


class AgentNotConfigured(RuntimeError):
    """Missing API key or model name. The shop still works, only chat is unavailable."""


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").strip()


def model_name() -> str:
    name = os.getenv("OPENAI_MODEL", "").strip()
    if not name:
        raise AgentNotConfigured("Set OPENAI_MODEL in the root .env file (a gpt-5.6 or gpt-6 model).")
    return name


@lru_cache(maxsize=1)
def build_agent() -> Agent[ChatDeps, ChatReply]:
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentNotConfigured("Set PORTKEY_API_KEY in the root .env file.")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    model = OpenAIResponsesModel(model_name(), provider=OpenAIProvider(openai_client=client))
    agent = Agent(
        model,
        deps_type=ChatDeps,
        output_type=ChatReply,
        tools=TOOLS,
        retries=2,
    )

    @agent.instructions
    def system_prompt() -> str:
        return load_prompt()

    @agent.instructions
    def customer_context(ctx: RunContext[ChatDeps]) -> str:
        c = ctx.deps.customer
        if c is None:
            return "Who you're talking to: a guest (not logged in). Nothing from this chat is saved."
        return (
            f"Who you're talking to: {c.first_name} {c.last_name} ({c.email}), logged in, "
            f"customer since {c.member_since[:10]}. Earlier messages above are their saved chat history "
            "from previous visits, so you can pick up where you left off."
        )

    @agent.instructions
    def page_context(ctx: RunContext[ChatDeps]) -> str:
        page = ctx.deps.page
        if page.product is None:
            return f"Where they are: the {page.page_name} page."
        p = page.product
        colors = ", ".join(p.colors) if p.colors else "not listed"
        return (
            f"Where they are: the product page for {p.name} (product_id: {p.product_id}, category: {p.category}, "
            f"colors: {colors}, price: ${p.price:.2f}). If they say 'this', 'this one', 'it', or 'here' without "
            "naming a product, they mean this item. Still use the tools for stock and any detail you quote."
        )

    return agent


def to_message_history(turns: list[ChatTurn]) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    for turn in turns[-HISTORY_TURNS:]:
        if turn.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return history


def is_content_filter(error: ModelHTTPError) -> bool:
    """The provider (Azure OpenAI behind Portkey) rejects jailbreak/harmful prompts with a 400 content_filter."""
    return error.status_code == 400 and "content_filter" in str(error.body)


def customer_from(user: dict | None) -> Customer | None:
    if user is None:
        return None
    return Customer(
        user_id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        member_since=user["member_since"],
    )


def page_from(context: PageContext) -> PageInfo:
    """Turn the browser's page context into trusted facts. Raw client text never reaches the prompt:
    the page name comes from a fixed list, and the product comes from the catalogue by id."""
    product = catalog.get(context.product_id) if context.product_id else None
    if product:
        return PageInfo(
            page_name="Product page",
            product=ViewingProduct(**{k: product[k] for k in ViewingProduct.model_fields}),
        )
    path, _, query = context.path.partition("?")
    if path == "/products" and "view=chat" in query:
        return PageInfo(page_name="Products (showing results from this chat)")
    return PageInfo(page_name=PAGE_NAMES.get(path, "Campus Customs website"))


async def run_chat(
    message: str, history: list[ChatTurn], user: dict | None, page: PageContext, turn: TurnAudit
) -> ChatResponse:
    agent = build_agent()
    turn.model = model_name()
    try:
        result = await agent.run(
            message,
            message_history=to_message_history(history),
            deps=ChatDeps(customer=customer_from(user), page=page_from(page)),
            usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS),
        )
    except ModelHTTPError as e:
        if is_content_filter(e):
            turn.stop("blocked_by_provider_filter")
            turn.safety.append("provider_content_filter")
            return ChatResponse(reply=BLOCKED_REPLY, blocked=True)
        raise
    turn.add_run(result.new_messages())
    usage = result.usage
    turn.usage = {
        "model_requests": usage.requests,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }
    turn.stop("final_answer")
    reply: ChatReply = result.output
    cards = [ProductCard(**catalog.card(p)) for p in catalog.get_many(reply.product_ids)]
    page_results = build_page(reply.page_search, reply.product_ids) if reply.page_search else None
    return ChatResponse(reply=reply.reply.strip(), products=cards, page=page_results)


def build_page(search: PageSearch, picks: list[str]) -> ChatPage | None:
    """Run the agent's chosen search against the DB. Every match becomes a card; the agent's picks go first."""
    hits = catalog.search(
        q=search.query,
        category=search.category,
        color=search.color,
        max_price=search.max_price,
        size=search.size_in_stock,
    )
    if not hits:
        return None
    rank = {pid: i for i, pid in enumerate(picks)}
    hits.sort(key=lambda p: rank.get(p["product_id"], len(rank)))  # stable: the rest stay A-Z
    return ChatPage(
        title=search.title,
        total_matches=len(hits),
        search=search,
        products=[ProductCard(**catalog.card(p)) for p in hits],
    )
