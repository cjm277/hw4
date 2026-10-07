"""Tools the Campus Customs agent can call: read-only lookups in data/campus_customs.db (via catalog.py).

search_products         -> find products (ids, names, prices)
get_product_description -> the catalogue description, colors, and type
get_price               -> the exact price
check_stock             -> units on hand, per size
get_customer_profile    -> the logged-in shopper's own account details (from the agent's deps)
"""

from pydantic_ai import RunContext

import catalog
from models import (
    Category,
    ChatDeps,
    Customer,
    ProductDescription,
    ProductNotFound,
    ProductPrice,
    ProductRef,
    ProductSummary,
    SearchResults,
    Size,
    SizeStock,
    StockReport,
    StockStatus,
)

MAX_RESULTS = 10


def _stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= catalog.LOW_STOCK_PER_SIZE else "in_stock"


def _lookup(product_id: str) -> dict | ProductNotFound:
    """The product row, or a not-found result with close matches by name."""
    if product := catalog.get(product_id.strip()):
        return product
    close = catalog.search(q=product_id.replace("-", " "))[:5]
    return ProductNotFound(
        product_id=product_id,
        message="No product has that product_id. Use search_products to find the right one.",
        suggestions=[ProductRef(product_id=p["product_id"], name=p["name"]) for p in close],
    )


def search_products(
    query: str = "",
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size_in_stock: Size | None = None,
) -> SearchResults:
    """Find products in the Campus Customs catalogue and get their product_ids.

    Use this first whenever you need a product_id, or to list options. For a product's description use
    get_product_description, and for size or stock questions use check_stock.

    Args:
        query: A few keywords, e.g. "baseball", "big yale", "branford", "harvard". Every keyword must match,
            so keep it short and leave out words already covered by the other filters. Pass the shopper's words
            as typed: misspellings ("quater zip", "brandford") are corrected automatically.
        category: Limit to one shop category.
        color: The garment color, e.g. "navy", "gray", "white" (matches the item itself, not its print).
        max_price: Only items at or below this price in USD.
        size_in_stock: Only items that currently have this size in stock.
    """
    hits, corrections = catalog.search_with_corrections(
        q=query, category=category, color=color, max_price=max_price, size=size_in_stock
    )
    return SearchResults(
        total_matches=len(hits),
        showing=min(len(hits), MAX_RESULTS),
        corrected_terms=corrections,
        products=[
            ProductSummary(
                product_id=p["product_id"],
                name=p["name"],
                category=p["category"],
                price=p["price"],
                colors=p["colors"],
                in_stock=p["total_stock"] > 0,
            )
            for p in hits[:MAX_RESULTS]
        ],
    )


def get_product_description(product_id: str) -> ProductDescription | ProductNotFound:
    """The catalogue description, colors, and garment type for one product.

    Use for any "what does it look like / tell me about it / what color is it" question.

    Args:
        product_id: The product_id from search_products, e.g. "basic-hoodie-big-yale".
    """
    p = _lookup(product_id)
    if isinstance(p, ProductNotFound):
        return p
    return ProductDescription(
        product_id=p["product_id"],
        name=p["name"],
        category=p["category"],
        garment_type=p["garment_type"],
        colors=p["colors"],
        description=p["description"],
        has_description=bool(p["description"]),
    )


def get_price(product_id: str) -> ProductPrice | ProductNotFound:
    """The exact current price (USD) of one product.

    Args:
        product_id: The product_id from search_products, e.g. "basic-hoodie-big-yale".
    """
    p = _lookup(product_id)
    if isinstance(p, ProductNotFound):
        return p
    return ProductPrice(product_id=p["product_id"], name=p["name"], price=p["price"])


def check_stock(product_id: str, size: Size | None = None) -> StockReport | ProductNotFound:
    """How many units are in stock for one product, per size, read live from the inventory table.

    Use for every stock, availability, or size question, and pass `size` when the shopper names one.

    Args:
        product_id: The product_id from search_products, e.g. "basic-hoodie-big-yale".
        size: The size the shopper asked about (XS, S, M, L, XL, XXL), if any.
    """
    p = _lookup(product_id)
    if isinstance(p, ProductNotFound):
        return p
    sizes = [SizeStock(size=s["size"], quantity=s["quantity"], status=_stock_status(s["quantity"])) for s in p["sizes"]]
    return StockReport(
        product_id=p["product_id"],
        name=p["name"],
        requested=next((s for s in sizes if s.size == size), None) if size else None,
        sizes=sizes,
        total_in_stock=sum(s.quantity for s in sizes),
        sizes_in_stock=[s.size for s in sizes if s.quantity > 0],
        sizes_sold_out=[s.size for s in sizes if s.quantity <= 0],
    )


def get_customer_profile(ctx: RunContext[ChatDeps]) -> Customer | str:
    """The logged-in shopper's own account details: name, email, and member-since date.

    Use when they ask what's on their account (e.g. "what email do you have for me?"). Returns a note if they
    are a guest. There is no access to other shoppers, passwords, orders, or payment details.
    """
    return ctx.deps.customer or "The shopper is a guest (not logged in), so there is no account to look up."


TOOLS = [search_products, get_product_description, get_price, check_stock, get_customer_profile]
