"""Read-only access to the product catalogue and inventory in data/campus_customs.db.

Shared by the website endpoints (main.py) and the agent's tools (tools.py), so the site
and the chatbot always show the same prices and stock.
"""

import difflib
import json
import re
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
PRODUCTS_DIR = DATA_DIR / "products"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# garment_type has 22 messy variants; collapse them into shop categories.
CATEGORY_RULES = [
    ("Quarter-Zips", ("quarter-zip",)),
    ("Jackets", ("jacket", "full-zip fleece")),
    ("Hoodies", ("hood",)),
    ("Crewnecks", ("crewneck", "mockneck")),
    ("Long Sleeves", ("long-sleeve",)),
    ("T-Shirts", ("t-shirt",)),
]
CATEGORIES = [name for name, _ in CATEGORY_RULES]

# Fields sent to the browser for a product card (Products page, chat cards, chat results grid, similar items).
CARD_FIELDS = (
    "product_id", "name", "garment_type", "category", "description", "colors", "price", "image_url",
    "total_stock", "sizes_low", "sizes_sold_out",
)

# Stock is judged per size: 1-5 left in a size = "only a few left"; 0 = sold out in that size.
# Used by the card badges, the item page's size grid, and the agent's check_stock tool.
LOW_STOCK_PER_SIZE = 5

# Main-colour families for "You might also like" (colors[0] is the garment colour).
COLOR_FAMILIES = [
    ("navy", ("navy",)),
    ("gray", ("gray", "grey", "charcoal")),
    ("cream", ("cream", "ivory", "oatmeal", "natural")),
    ("red", ("red", "coral", "crimson", "maroon", "pink")),
    ("green", ("green",)),
    ("blue", ("blue",)),
    ("white", ("white",)),
    ("black", ("black",)),
]

# Typo tolerance: a query word that matches nothing is swapped for the closest catalogue word
# (difflib similarity >= 0.8), e.g. "quater" -> "quarter". Words under 4 letters are never changed.
FUZZY_CUTOFF = 0.8
MIN_FUZZY_LEN = 4

# Search helpers: shoppers type "tees" and "hoodies"; the catalogue says "t-shirt" and "hoodie".
SYNONYMS = {"tee": "t-shirt", "tshirt": "t-shirt", "hoody": "hoodie"}
STOPWORDS = {"a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "some", "any", "something", "yale"}


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    for name, keywords in CATEGORY_RULES:
        if any(k in g for k in keywords):
            return name
    return "Other"


def clean_description(description: str) -> str:
    """Blank out placeholder descriptions (3 catalogue rows were never described)."""
    if description.startswith("Campus Customs product photo") and "filename-based stub" in description:
        return ""
    return description


def image_url(image_file_path: str) -> str:
    """Map the catalogue's data-relative path (products/x.jpg) to the /images mount."""
    return "/images/" + (DATA_DIR / image_file_path).relative_to(PRODUCTS_DIR).as_posix()


def sizes_low(sizes: list[dict]) -> list[str]:
    """Sizes with only a few left (1-5), in XS->XXL order."""
    return [s["size"] for s in sizes if 0 < s["quantity"] <= LOW_STOCK_PER_SIZE]


def sizes_sold_out(sizes: list[dict]) -> list[str]:
    """Sizes with none left, in XS->XXL order."""
    return [s["size"] for s in sizes if s["quantity"] <= 0]


def color_family(color: str) -> str:
    c = color.lower()
    for family, keywords in COLOR_FAMILIES:
        if any(k in c for k in keywords):
            return family
    return c


def _sort_sizes(sizes: list[dict]) -> list[dict]:
    rank = {s: i for i, s in enumerate(SIZE_ORDER)}
    return sorted(sizes, key=lambda s: rank.get(s["size"], len(SIZE_ORDER)))


def product_out(row: sqlite3.Row, sizes: list[dict]) -> dict:
    total = sum(s["quantity"] for s in sizes)
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": category_for(row["garment_type"]),
        "description": clean_description(row["description"]),
        "colors": json.loads(row["colors"]),
        "price": row["price"],
        "image_url": image_url(row["image_file_path"]),
        "total_stock": total,
        "sizes_low": sizes_low(sizes),
        "sizes_sold_out": sizes_sold_out(sizes),
        "sizes": sizes,
        "search_tags": json.loads(row["search_tags"]),
    }


def _load_all() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        stock: dict[str, list[dict]] = {}
        for s in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(s["product_id"], []).append({"size": s["size"], "quantity": s["quantity"]})
    return [product_out(r, _sort_sizes(stock.get(r["product_id"], []))) for r in rows]


def _terms(query: str) -> list[str]:
    terms = []
    for word in re.findall(r"[a-z0-9\-]+", query.lower()):
        if word in STOPWORDS:
            continue
        word = SYNONYMS.get(word, word)
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = SYNONYMS.get(word[:-1], word[:-1])  # hoodies -> hoodie, tees -> t-shirt
        terms.append(word)
    return terms


def _haystack(p: dict) -> str:
    return " ".join(
        [p["name"], p["garment_type"], p["category"], p["description"], " ".join(p["colors"]), " ".join(p["search_tags"])]
    ).lower()


def _vocabulary(products: list[dict]) -> list[str]:
    words: set[str] = set()
    for p in products:
        for w in re.findall(r"[a-z0-9\-]+", _haystack(p)):
            words.add(w)
            words.update(part for part in w.split("-") if part)  # "quarter-zip" -> "quarter", "zip"
    return sorted(words)


def correct_terms(terms: list[str], products: list[dict]) -> tuple[list[str], dict[str, str]]:
    """Swap query words that match no product for the closest catalogue word ("quater" -> "quarter")."""
    stacks = [_haystack(p) for p in products]
    vocab: list[str] | None = None
    fixed, corrections = [], {}
    for t in terms:
        if len(t) < MIN_FUZZY_LEN or any(t in h for h in stacks):
            fixed.append(t)
            continue
        vocab = vocab or _vocabulary(products)
        match = difflib.get_close_matches(t, vocab, n=1, cutoff=FUZZY_CUTOFF)
        if match:
            corrections[t] = match[0]
        fixed.append(match[0] if match else t)
    return fixed, corrections


def search_with_corrections(
    q: str | None = None,
    category: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
) -> tuple[list[dict], dict[str, str]]:
    """Products matching every given filter, plus any typo corrections applied to `q`.

    `q` keywords must all appear (name, type, colors, tags, description); misspelled ones are corrected first.
    """
    everything = _load_all()
    products = everything
    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    if color:  # colors[0] is the garment itself; the rest are print/trim colors
        c = color.lower().strip()
        products = [p for p in products if p["colors"] and c in p["colors"][0].lower()]
    if max_price is not None:
        products = [p for p in products if p["price"] <= max_price]
    if size:
        products = [p for p in products if any(s["size"] == size.upper() and s["quantity"] > 0 for s in p["sizes"])]
    corrections: dict[str, str] = {}
    if q and (terms := _terms(q)):
        terms, corrections = correct_terms(terms, everything)
        products = [p for p in products if all(t in _haystack(p) for t in terms)]
    return products, corrections


def search(
    q: str | None = None,
    category: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
) -> list[dict]:
    """Products matching every given filter (typo-tolerant; see search_with_corrections)."""
    return search_with_corrections(q=q, category=category, color=color, max_price=max_price, size=size)[0]


def similar(product_id: str, limit: int = 4) -> list[tuple[dict, str]]:
    """'You might also like': other products in the same category and/or the same main colour family.

    Ranked: same category + colour, then same category, then same colour; in-stock first; then the
    most shared search tags (e.g. same sport or college); then name. Returns (product, reason) pairs.
    """
    base = get(product_id)
    if base is None:
        return []
    family = color_family(base["colors"][0]) if base["colors"] else None
    tags = {t.lower() for t in base["search_tags"]} - {"yale", "campus customs", "college merch"}
    scored = []
    for p in _load_all():
        if p["product_id"] == product_id:
            continue
        same_category = p["category"] == base["category"]
        same_color = family is not None and bool(p["colors"]) and color_family(p["colors"][0]) == family
        if not (same_category or same_color):
            continue
        shared_tags = len(tags & {t.lower() for t in p["search_tags"]})
        reason = "Same category & colour" if same_category and same_color else (
            "Same category" if same_category else "Same colour"
        )
        scored.append((2 * same_category + same_color, p["total_stock"] > 0, shared_tags, p["name"], p, reason))
    scored.sort(key=lambda x: (-x[0], not x[1], -x[2], x[3]))
    return [(x[4], x[5]) for x in scored[:limit]]


def get(product_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        sizes = [
            {"size": s["size"], "quantity": s["quantity"]}
            for s in conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,))
        ]
    return product_out(row, _sort_sizes(sizes))


def get_many(product_ids: list[str]) -> list[dict]:
    """Products for the given ids, in the given order. Unknown ids are skipped."""
    found = []
    for pid in dict.fromkeys(product_ids):  # de-duplicate, keep order
        if (p := get(pid)) is not None:
            found.append(p)
    return found


def card(p: dict) -> dict:
    return {k: p[k] for k in CARD_FIELDS}
