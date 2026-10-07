# Campus Customs: Usability Improvements (Problem 9)

Four improvements: two on the **front end** (what shoppers see) and two on the **back end** (what happens to their chat messages before the agent answers). For each one: what was added, why it helps a Campus Customs shopper or the business, where it lives in the code, and **how to see it in the running app** (http://localhost:5173). Every feature below was checked in a browser on 2026-10-06 against the live database.

| # | Improvement | Type | Where to see it |
|---|---|---|---|
| 1 | "You might also like" row | Front end | Any item page, below the product details |
| 2 | Size-level stock badges (orange "Only a few left in M", red "Sold out in XS, XL and XXL") | Front end | Bottom of every product card, below the price (Products, Home, chat results, similar items, chat cards) |
| 3 | Sensitive-data guard | Back end | Chat: type a card number or password |
| 4 | Typo-tolerant search | Back end | Chat ("quater zips") or the Products search box |

---

## 1. Front end: "You might also like" on the item page

### What we added
- A **"You might also like"** section under every item page: a row of **4 similar products**, each a normal product card (photo, name, price, short description) that opens that item's page.
- Each card has a small pill explaining why it was picked: **"Same category & colour"**, **"Same category"**, or **"Same colour"**.
- How items are chosen (`catalog.similar()` in `backend/catalog.py`):
  1. A candidate must share the item's **shop category** (e.g. Hoodies) **or** its **main colour family**. `colors[0]` is the garment colour, grouped into families, so "navy" and "navy blue" match, as do "heather gray" and "charcoal gray".
  2. Ranking: same category **and** colour first, then same category, then same colour; in-stock before out-of-stock; then the most shared search tags (same sport, college, or school); then A–Z.
- API: `GET /api/products/{product_id}/similar` returns the 4 cards plus `reason`. Front end: `frontend/src/components/SimilarItems.tsx`, rendered at the bottom of `pages/ProductDetail.tsx`. On phones the row scrolls sideways.

### Why it helps
- **Shoppers:** if the item isn't quite right, or **their size is sold out**, close alternatives are one click away instead of a trip back to the full catalogue. The reason pill makes the suggestion trustworthy ("same colour" when they liked the navy).
- **Business:** classic cross-sell. It keeps shoppers browsing and turns a dead end (sold-out size) into another possible sale. Because it uses the live catalogue and stock, it never pushes items that are out of stock.

### How to see it
Open any product, e.g. **Football Left Chest T Shirt** (`/products/football-left-chest-t-shirt`), and scroll below "Ask the chat about this".

### Verified
- Football Left Chest T Shirt → Track Field Left Chest T Shirt, Boola Boola T Shirt, School Of Management Crest T Shirt, School Of Nursing Crest T Shirt (all navy T-shirts, all "Same category & colour"), shown in one row under the details.
- Branford 1 4 Zip → four other gray quarter-zips. Berkeley Sweater Fleece Jacket (no colours in the catalogue) → four other jackets ("Same category").
- Clicking a suggestion opens its item page, which shows its own "You might also like" row.

![You might also like](screenshots/p9-1-you-might-also-like.jpg)

---

## 2. Front end: Size-level stock badges on product cards

### What we added
- At the **bottom of every product card, right below the price**, coloured badges show stock **per size**:
  - **Orange, "Only a few left in M"** (`#ef6c00`): the sizes with **5 or fewer** units left.
  - **Red, "Sold out in XS, XL and XXL"** (`#d32f2f`): the sizes with **none** left. If every size is gone, it simply says **"Sold out"**.
  - Several sizes are listed naturally: "in M", "in XS and XL", "in S, M and XL". A product can show both badges, and a product with every size well stocked shows none.
- **One rule, in one place:** the backend works out `sizes_low` (1–5 left) and `sizes_sold_out` (0 left) for every product from the live `inventory` table (`catalog.LOW_STOCK_PER_SIZE = 5`). The **same threshold** drives the item page's size grid ("Only 2 left") and the chat agent's `check_stock` tool, so the card, the item page, and the chat always agree.
- One shared front-end component (`frontend/src/components/StockBadge.tsx`), so the badges look the same everywhere a product card appears: **Products page, Home "Crowd favorites", chat results grid, "You might also like" row, and (smaller) on the product cards inside the chat**. The item page itself already shows the full colour-coded size grid, so it doesn't repeat the badges.
- *Design change (follow-up):* the first version showed one badge on the photo, based on the product's **total** stock (≤ 20 units). Only 4 products qualified, and it couldn't tell a shopper that *their* size was gone. Switching to per-size badges below the price makes them useful on almost every card.

### Why it helps
- **Shoppers:** shoppers buy one size, not the product total. Seeing "Sold out in M" on the card means a medium-wearer skips that item without clicking in, and "Only a few left in L" tells a large-wearer not to wait. That saves clicks and disappointment, especially on phones.
- **Business:** honest, specific urgency on items that really are running low, and fewer dead-end page views on sizes that are gone. Staff also get an at-a-glance view of which sizes need restocking.

### How to see it
Products page: almost every card now has badges under the price, for example:
- **Baseball Left Chest Crewneck:** orange "Only a few left in M" + red "Sold out in XS and XL"
- **Football Left Chest T Shirt:** orange "Only a few left in S, L and XXL" + red "Sold out in XS, M and XL"
- **Basic Hoodie Big Yale:** orange "Only a few left in S, M and XL"

### Verified
- In the browser on the Products page (102 cards): **100 cards show badges**, with **71 orange** and **77 red**. Only Tri Blend Sports Football T Shirt and Yale Law School 1 4 Zip are well stocked in every size, so they show none. That matches the database exactly (71 products have a size with 1–5 left, 77 have a sold-out size, 0 are sold out in every size).
- Every badge sits **below the price** at the bottom of the card, none are on the photo, and the measured colours are orange `rgb(239, 108, 0)` and red `rgb(211, 47, 47)`.
- Spot checks against `inventory`: Baseball Left Chest Crewneck XS 0, M 5, XL 0 → "Only a few left in M" + "Sold out in XS and XL" ✔. Football Left Chest T Shirt XS 0, S 2, M 0, L 2, XL 0, XXL 5 → "Only a few left in S, L and XXL" + "Sold out in XS, M and XL" ✔.

![Size-level stock badges below the price](screenshots/p9-2-size-stock-badges.jpg)

---

## 3. Back end: Sensitive-data guard

### What we added
- `backend/guard.py`: every chat message goes through `guard.scrub()` **first**, in `POST /api/chat`, **before** it can reach the AI model (and Portkey), the `chat_messages` table, or the logs. Guest history sent by the browser is scrubbed too.
- What it blanks out, replacing it with a placeholder like `[card number removed]`:

| Kind | Example that's caught |
|---|---|
| Card numbers | any 13–19 digit run, spaces or dashes allowed (`4111 1111 1111 1111`, even a fake `1234 5678 9012 3456`) |
| Card security code / expiry | `cvv 123`, `exp 12/27` |
| Passwords, passcodes, PINs | `my password is hunter2`, `password: …`, `pin is 4821` |
| Government ID | `123-45-6789`, `SSN is 123456789` |
| Bank details | `routing number 021000021`, `account number 1234…`, `IBAN …` |
| Access keys and tokens | `sk-…`, `ghp_…`, `AKIA…`, `Bearer …` |

- **What happens next:**
  - The shopper sees an amber **"Privacy notice"** in the chat: *"For your security, I removed the card number from your message and didn't save it. Please don't share card numbers, passwords, or other sensitive details in chat. Campus Customs will never ask for them here. For payment or account help, call (475) 301-4205."*
  - Their own chat bubble is swapped for the blanked-out version, so the secret disappears from the screen too.
  - If the rest of the message had a real question ("…can you hold the Branford quarter zip in M?"), the agent still answers it, having only seen the placeholders. If the message was basically just the secret, the model is skipped and only the notice is shown, which also saves an API call.
  - For logged-in shoppers, only the blanked-out text is saved to `chat_messages`.
- The prompt (`prompts/prompt.md`) tells the agent what the placeholders mean: don't ask for the data again, don't repeat the warning, and explain that orders can't be placed in chat.
- **Deliberately not blanked:** emails, phone numbers, and names. Shoppers use them normally ("what email is on my account?"), and the shop's own phone number appears in answers. Normal messages like "I forgot my password, how do I reset it?" or "do you sell lapel pins?" pass through untouched.

### Why it helps
- **Shoppers:** people sometimes paste card details or passwords into a chat box out of habit. The guard protects them even when they slip up, and tells them politely how to get real help.
- **Business:** sensitive data never reaches a third-party AI service, never sits in the chat-history table, and never ends up in logs. That cuts the risk and liability of storing payment data (PCI-style concerns) and builds trust.

### How to see it
Open the chat and send: `my card is 4111 1111 1111 1111 exp 09/28, can you hold the Branford quarter zip in M for me?` (or just `password: hunter2`).

### Verified
- In the browser, the shopper's bubble became *"my card is [card number removed] exp [card expiry date removed], can you hold…"*, followed by the amber Privacy notice (`rgb(255, 248, 225)`) and a helpful answer (20 in M, visit the shop or call). `password: hunter2` showed only the notice. The text "4111" and "hunter2" appeared **nowhere on the page** afterwards.
- Logged in as Conrad: the database stored `Here is my card [card number removed] exp [card expiry date removed] cvv [card security code removed], …` and `my password is [password removed]`. A search of all of `chat_messages` for `4111`, `hunter2`, and `021000021` found **0 rows**.
- 16 test messages: all 9 sensitive ones were caught, and all 7 normal ones (including "I forgot my password, how do I reset it?", lapel pins, an email address, and a phone number) were left alone.
- Found while testing: the agent once told a shopper to "check out through the website", but this site has no online checkout. The prompt now says to visit the shop or call/email instead.

---

## 4. Back end: Typo-tolerant search

### What we added
- In `catalog.search_with_corrections()` (`backend/catalog.py`): if a search word matches **no product at all**, it's swapped for the closest word that does appear in the catalogue. The vocabulary comes from product names, types, descriptions, colours, and tags, and similarity is measured with Python's `difflib` (≥ 0.8).
  - `quater → quarter`, `brandford → branford`, `crewnek → crewneck`, `sweatshrt → sweatshirt`, `baseabll → baseball`, `hoddie → hoodie`.
- **Safety rails:** words that already match something are never changed, and words under 4 letters are never changed (so "tee" can't become "the"). A real miss stays a miss: "pink" or "purple hoodie" still correctly return nothing instead of a wrong guess.
- The agent's `search_products` tool returns `corrected_terms` (e.g. `{"quater": "quarter"}`). The prompt tells it to just answer, not ask the shopper to retype.
- Bonus: the same search powers the **Products page search box**, so typing "quater zip" there works too.

### Why it helps
- **Shoppers:** people type fast, often on phones. Before this change, *"do you have any quater zips?"* searched for "quater", found 0 products, and the shopper was asked to try again. Now they just get the quarter-zips.
- **Business:** a "no results" answer is a lost sale. Typo tolerance keeps shoppers moving toward a product and makes the assistant feel smart instead of picky.

### How to see it
In the chat, ask **"do you have any quater zips?"** or **"anything from brandford college?"**. Or type **"quater zip"** in the Products page search box.

### Verified (before → after, same database)

| Query | Before | After |
|---|---|---|
| `quater zip` | 0 results | 12 (corrected to "quarter") |
| `brandford` | 0 | 1, the Branford 1 4 Zip |
| `crewnek` | 0 | 30 |
| `sweatshrt` | 0 | 59 |
| `baseabll` | 0 | 4 |
| `pink` / `purple hoodie` | 0 | 0 (correctly still nothing) |

- In the browser chat, "do you have any quater zips?" → *"Yep, here are our quarter-zips, all $72.00…"* and the page switched to **"From your chat: Quarter-zips", 11 cards**.
- "anything from brandford college?" → *"We have one Branford item: the Branford 1/4 Zip, $72.00."*
- Products search box, `quater zip` → 12 items (was 0).

---

## Screenshots for graders

Saved in `output/screenshots/`:
- `p9-1-you-might-also-like.jpg`: the row of 4 similar T-shirts with their reason pills.
- `p9-2-size-stock-badges.jpg`: Products page cards with orange "Only a few left in …" and red "Sold out in …" badges below the price.

The screenshot pane in my tool stopped drawing partway through, so the chat features were verified through the page's content and computed styles (above). Suggested screenshots to take in your own browser: the chat privacy notice after sending a test card number, and the chat results page after "do you have any quater zips?".
