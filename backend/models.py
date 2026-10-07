"""Pydantic types shared by the chat API, the agent's deps and structured output, and its tools."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["T-Shirts", "Hoodies", "Crewnecks", "Quarter-Zips", "Jackets", "Long Sleeves"]
Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
StockStatus = Literal["in_stock", "low_stock", "sold_out"]

MAX_CARDS = 6
COLORS_NOTE = "First = the garment color; the rest = print/trim colors. Not separate color options."


# ---------- Tool results (what the agent sees) ----------

class ProductRef(BaseModel):
    product_id: str
    name: str


class ProductNotFound(BaseModel):
    """Returned instead of a result when a product_id doesn't exist."""

    found: Literal[False] = False
    product_id: str
    message: str
    suggestions: list[ProductRef] = Field(description="Close matches by name. Confirm with the shopper before using one.")


class ProductSummary(BaseModel):
    """One search hit: enough to identify and list a product, not to answer detail or stock questions."""

    product_id: str
    name: str
    category: str
    price: float = Field(description="Current price in USD from the catalogue.")
    colors: list[str] = Field(description=COLORS_NOTE)
    in_stock: bool = Field(description="True if at least one size has stock.")


class SearchResults(BaseModel):
    total_matches: int
    showing: int
    products: list[ProductSummary]
    corrected_terms: dict[str, str] = Field(
        default_factory=dict, description='Typos fixed in the query, e.g. {"quater": "quarter"}.'
    )


class ProductDescription(BaseModel):
    product_id: str
    name: str
    category: str
    garment_type: str
    colors: list[str] = Field(description=COLORS_NOTE + " Empty when the catalogue lists none.")
    description: str = Field(description="Catalogue description. Empty when there is none.")
    has_description: bool = Field(description="False means do not describe the item's look, fabric, or fit.")


class ProductPrice(BaseModel):
    product_id: str
    name: str
    price: float = Field(description="Exact price from the catalogue.")
    currency: Literal["USD"] = "USD"


class SizeStock(BaseModel):
    size: str
    quantity: int = Field(description="Units on hand right now.")
    status: StockStatus = Field(description="sold_out = 0, low_stock = 1-5, in_stock = 6+.")


class StockReport(BaseModel):
    product_id: str
    name: str
    requested: SizeStock | None = Field(description="The size the shopper asked about, if any.")
    sizes: list[SizeStock] = Field(description="Every size XS-XXL, in order.")
    total_in_stock: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]


# ---------- Agent context: who is chatting and where they are (ChatDeps) ----------

class Customer(BaseModel):
    """The logged-in shopper, read from the users table. Never includes the password hash or session data."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date (users.created_at, UTC).")


class ViewingProduct(BaseModel):
    """The product whose page the shopper has open, looked up in the catalogue (not taken from the browser)."""

    product_id: str
    name: str
    category: str
    colors: list[str] = Field(description=COLORS_NOTE)
    price: float


class PageInfo(BaseModel):
    """Where the shopper is on the site when they send a message."""

    page_name: str = Field(description="One of a fixed set of names, e.g. 'Home', 'Products', 'Product page'.")
    product: ViewingProduct | None = None


@dataclass
class ChatDeps:
    """Per-request context handed to the agent (PydanticAI deps): instructions and tools read it via RunContext."""

    customer: Customer | None  # None = guest
    page: PageInfo


# ---------- Agent output ----------

class PageSearch(BaseModel):
    """A catalogue search whose full results the website shows as a product grid (same filters as search_products)."""

    title: str = Field(max_length=60, description="Short heading for the grid, e.g. 'T-shirts' or 'Navy hoodies under $70'.")
    query: str = ""
    category: Category | None = None
    color: str | None = None
    max_price: float | None = None
    size_in_stock: Size | None = None


class ChatReply(BaseModel):
    """The agent's final answer for one turn."""

    reply: str = Field(description="What to say to the shopper: plain text, friendly, concise.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_CARDS,
        description=(
            "product_id values (from tool results) of the specific items this reply recommends or talks about, "
            "best match first. Shown as small cards in the chat. Empty if none."
        ),
    )
    page_search: PageSearch | None = Field(
        default=None,
        description=(
            "Set when the shopper is browsing a type or group of items (e.g. 'what t-shirts do you have?'): "
            "the filters of the search_products call that answered it. The website then shows every match "
            "as product cards. Null for one specific item, store/policy questions, or when nothing matched."
        ),
    )


# ---------- Chat API (frontend <-> FastAPI) ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageContext(BaseModel):
    """Sent by the browser with every chat message: where the shopper is right now."""

    path: str = Field(default="/", max_length=300, description="location.pathname + search, e.g. '/products/x'.")
    product_id: str | None = Field(default=None, max_length=120, description="Set on a single-item page.")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(
        default_factory=list,
        max_length=50,
        description="Guests only: this visit's earlier turns. Ignored when logged in (history comes from the DB).",
    )
    page: PageContext = Field(default_factory=PageContext)


class ProductCard(BaseModel):
    """Everything a product card needs. Built from the database by the backend, never by the model."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    colors: list[str]
    price: float
    image_url: str
    total_stock: int
    sizes_low: list[str] = Field(description="Sizes with only a few left (1-5), XS->XXL. Orange card badge.")
    sizes_sold_out: list[str] = Field(description="Sizes with none left, XS->XXL. Red card badge.")


class SimilarItem(ProductCard):
    """A 'You might also like' suggestion on the item page."""

    reason: str = Field(description="'Same category & colour', 'Same category', or 'Same colour'.")


class ChatPage(BaseModel):
    """Search results the website renders as a product grid (the Products page, in 'From your chat' view)."""

    title: str
    total_matches: int
    search: PageSearch = Field(description="The exact filters that produced these results.")
    products: list[ProductCard]


class ChatResponse(BaseModel):
    reply: str = Field(description="Empty when the message was only sensitive data (then only privacy_notice is shown).")
    products: list[ProductCard] = Field(default_factory=list, description="Specific items -> small cards in the chat.")
    page: ChatPage | None = Field(default=None, description="Browse results -> product grid on the page.")
    blocked: bool = Field(
        default=False,
        description="True when the model provider's safety filter refused the message. "
        "The frontend leaves that turn out of the history it sends next time.",
    )
    privacy_notice: str | None = Field(
        default=None, description="Set when the sensitive-data guard blanked something out of the shopper's message."
    )
    redacted_message: str | None = Field(
        default=None, description="The shopper's message as it was actually used and stored (secrets replaced)."
    )


class StoredMessage(BaseModel):
    """One saved chat message (chat_messages row), with its product cards rebuilt from the live catalogue."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    messages: list[StoredMessage]
