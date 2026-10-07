"""Sensitive-data guard for chat messages.

Every chat message (and any guest history the browser sends) passes through scrub() FIRST, before it can
reach the model, the database (chat_messages), or the logs. Anything that looks like a secret is replaced
with a placeholder such as "[card number removed]", and the shopper gets a polite privacy notice.

What counts as sensitive here (a merch shop never needs any of it in chat):
- card numbers: any run of 13-19 digits (spaces/dashes allowed), Luhn-valid or not
- card security codes (CVV/CVC) and expiry dates when labelled
- passwords, passcodes, and PINs when labelled ("my password is ...", "pin: 1234")
- US Social Security numbers, bank account / routing numbers, IBANs
- API keys and access tokens (sk-..., ghp_..., AKIA..., "Bearer ...")

Not blanked: email addresses, phone numbers, and names. Shoppers use those normally ("what email is on my
account?"), and the shop's own phone number appears in answers.
"""

import re
from dataclasses import dataclass, field

# (label shown to the shopper, pattern). Group "secret" (if present) is the part to blank; otherwise the whole match.
PATTERNS: list[tuple[str, re.Pattern]] = [
    ("card number", re.compile(r"(?<![\d-])(?:\d[ -]?){12,18}\d(?![\d-])")),
    ("card security code", re.compile(r"\b(?:cvv2?|cvc2?|csc|security code)\b\W{0,3}(?:is\W{0,3})?(?P<secret>\d{3,4})\b", re.I)),
    (
        "card expiry date",
        re.compile(r"\b(?:exp(?:iry|iration)?|expires)(?: date)?\W{0,3}(?:is\W{0,3})?(?P<secret>(?:0?[1-9]|1[0-2])\s?[/-]\s?(?:\d{4}|\d{2}))\b", re.I),
    ),
    ("Social Security number", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("Social Security number", re.compile(r"\b(?:ssn|social security(?: number| no\.?)?)\W{0,3}(?:is\W{0,3})?(?P<secret>\d{9})\b", re.I)),
    (
        "bank account number",
        re.compile(r"\b(?:bank account|account|acct|routing)(?: number| no\.?| #)?\s*(?:is|:|=|#)?\s*(?P<secret>\d[\d -]{5,20}\d)\b", re.I),
    ),
    ("bank account number", re.compile(r"\biban\W{0,3}(?P<secret>[A-Z]{2}\d{2}[A-Z0-9 ]{11,30})", re.I)),
    (
        "password",
        re.compile(r"\b(?:password|passwd|pwd|passcode|pass code)\b\s*(?:is|was|=|:|-)\s*[\"'“‘]?(?P<secret>[^\s\"'”’]+)", re.I),
    ),
    ("PIN", re.compile(r"\bpin(?: code| number)?\s*(?:is|was|=|:)\s*(?P<secret>\d{4,8})\b", re.I)),
    (
        "access key",
        re.compile(r"\b(?:sk-[A-Za-z0-9_\-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    ),
    ("access key", re.compile(r"\bbearer\s+(?P<secret>[A-Za-z0-9._\-]{20,})", re.I)),
]

# Fewer real words than this (outside the placeholders) means the message was basically just the secret,
# so there's nothing to ask the model; the shopper just gets the notice.
MIN_WORDS_FOR_MODEL = 4


@dataclass
class GuardResult:
    text: str  # the message with sensitive parts replaced
    found: list[str] = field(default_factory=list)  # labels, e.g. ["card number", "password"]

    @property
    def redacted(self) -> bool:
        return bool(self.found)

    @property
    def needs_model(self) -> bool:
        words = re.findall(r"[A-Za-z]{2,}", re.sub(r"\[[^\]]* removed\]", " ", self.text))
        return len(words) >= MIN_WORDS_FOR_MODEL

    def notice(self) -> str | None:
        if not self.found:
            return None
        kinds = list(dict.fromkeys(self.found))
        what = kinds[0] if len(kinds) == 1 else ", ".join(kinds[:-1]) + " and " + kinds[-1]
        return (
            f"For your security, I removed the {what} from your message and didn't save it. "
            "Please don't share card numbers, passwords, or other sensitive details in chat. "
            "Campus Customs will never ask for them here. For payment or account help, call (475) 301-4205."
        )


def scrub(text: str) -> GuardResult:
    found: list[str] = []
    for label, pattern in PATTERNS:

        def blank(m: re.Match, label: str = label) -> str:
            found.append(label)
            placeholder = f"[{label} removed]"
            if "secret" in pattern.groupindex and m.group("secret"):
                start, end = m.span("secret")
                whole_start = m.start()
                return m.group(0)[: start - whole_start] + placeholder + m.group(0)[end - whole_start :]
            return placeholder

        text = pattern.sub(blank, text)
    return GuardResult(text=text, found=found)
