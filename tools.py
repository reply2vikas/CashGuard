"""
CashGuard tools — plain Python functions the agents call.

Design rule from the course: do NOT ask the LLM to do arithmetic or date math.
Write deterministic tools and let the agent ORCHESTRATE them. This is exactly
the "clever use of existing toolsets" the judges reward, and it keeps the
forecast trustworthy (every number traces to a real transaction).

These functions are framework-agnostic: they work whether you wire them into
ADK, an MCP server, or call them directly.
"""

from __future__ import annotations
import re
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean


# ---------------------------------------------------------------------------
# SECURITY: redact personally identifiable information before anything is sent
# to the model. This is one of the 3+ course concepts you must demonstrate.
# ---------------------------------------------------------------------------
_PII_PATTERNS = [
    (re.compile(r"\b\d{12,19}\b"), "[CARD_OR_ACCT]"),         # long account/card numbers
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),  # emails
    (re.compile(r"\b(?:\+?\d[\d\s-]{8,}\d)\b"), "[PHONE]"),    # phone-like numbers
]


def redact_pii(text: str) -> str:
    """Mask account numbers, emails and phone numbers. Returns safe text."""
    safe = text
    for pattern, replacement in _PII_PATTERNS:
        safe = pattern.sub(replacement, safe)
    return safe


# ---------------------------------------------------------------------------
# PARSER: turn free-text statement lines into structured transactions.
# ---------------------------------------------------------------------------
_LINE_RE = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<desc>.+?)\s+(?P<amt>-?\d+(?:\.\d{1,2})?)\s*$"
)


def parse_statement(raw_text: str) -> list[dict]:
    """
    Parse pasted statement text into [{date, description, amount}, ...].
    Rows that don't match are skipped (and reported by the caller) — this is
    where you show graceful failure-recovery in the demo.
    """
    transactions, skipped = [], []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _LINE_RE.search(line)
        if not m:
            skipped.append(line)
            continue
        transactions.append(
            {
                "date": m.group("date"),
                "description": m.group("desc").strip(),
                "amount": float(m.group("amt")),
            }
        )
    return {"transactions": transactions, "skipped": skipped}


# ---------------------------------------------------------------------------
# PATTERN / MEMORY: find recurring charges (the habits driving the problem).
# ---------------------------------------------------------------------------
def _normalize(desc: str) -> str:
    return re.sub(r"[^a-z ]", "", desc.lower()).strip()


# Essentials can't realistically be "paused" as advice (you can't stop buying
# groceries or paying electricity). Only discretionary charges are candidates
# for the "pause this one habit" recommendation.
ESSENTIALS = ("grocery", "electricity", "power", "utility", "pharmacy",
              "fuel", "gas", "rent", "salary", "loan", "insurance")


def is_discretionary(desc: str) -> bool:
    """True if this charge is something the user could plausibly pause."""
    n = _normalize(desc)
    return not any(e in n for e in ESSENTIALS)


def detect_recurring(transactions: list[dict]) -> list[dict]:
    """
    Group outflows by merchant name; anything charged 2+ times is 'recurring'.
    Returns them sorted by total spend (biggest offender first), each tagged
    with whether it's discretionary (pausable).
    """
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in transactions:
        if t["amount"] < 0:
            groups[_normalize(t["description"])].append(t)

    recurring = []
    for key, items in groups.items():
        if len(items) >= 2:
            total = sum(-i["amount"] for i in items)
            recurring.append(
                {
                    "merchant": items[0]["description"],
                    "occurrences": len(items),
                    "avg_amount": round(mean(-i["amount"] for i in items), 2),
                    "total_spent": round(total, 2),
                    "discretionary": is_discretionary(items[0]["description"]),
                }
            )
    return sorted(recurring, key=lambda r: r["total_spent"], reverse=True)


def pick_pausable(recurring: list[dict]) -> dict | None:
    """The habit to recommend pausing = biggest DISCRETIONARY recurring charge."""
    if not recurring:
        return None
    discretionary = [r for r in recurring if r["discretionary"]]
    return (discretionary or recurring)[0]


# ---------------------------------------------------------------------------
# FORECAST: project the running balance forward, flag the first overdraft day.
# ---------------------------------------------------------------------------
def forecast_balance(
    transactions: list[dict], opening_balance: float, remove_merchant: str | None = None
) -> dict:
    """
    Walk transactions in date order, tracking the running balance.
    If remove_merchant is given, pretend those charges were cancelled — this
    powers the red -> green counterfactual in the demo.
    Returns the daily balance series and the first date it goes negative.
    """
    ordered = sorted(transactions, key=lambda t: t["date"])
    balance = opening_balance
    series, first_overdraft = [], None

    for t in ordered:
        if remove_merchant and _normalize(remove_merchant) in _normalize(t["description"]):
            continue  # counterfactual: this charge no longer happens
        balance = round(balance + t["amount"], 2)
        series.append({"date": t["date"], "balance": balance, "event": t["description"]})
        if balance < 0 and first_overdraft is None:
            first_overdraft = t["date"]

    return {
        "series": series,
        "first_overdraft_date": first_overdraft,
        "min_balance": min((p["balance"] for p in series), default=opening_balance),
        "end_balance": balance,
    }


if __name__ == "__main__":
    # Quick self-test so you can verify the tools before wiring agents.
    from mock_data import SAMPLE_STATEMENT, OPENING_BALANCE, as_text

    parsed = parse_statement(as_text())
    txns = parsed["transactions"]
    print(f"Parsed {len(txns)} transactions, skipped {len(parsed['skipped'])}.")

    recurring = detect_recurring(txns)
    print("\nTop recurring charges:")
    for r in recurring[:3]:
        print(f"  {r['merchant']}: {r['occurrences']}x, total {r['total_spent']}")

    base = forecast_balance(txns, OPENING_BALANCE)
    print(f"\nBaseline first overdraft: {base['first_overdraft_date']} "
          f"(min balance {base['min_balance']})")

    villain = recurring[0]["merchant"]
    fixed = forecast_balance(txns, OPENING_BALANCE, remove_merchant=villain)
    print(f"After cancelling '{villain}': first overdraft = "
          f"{fixed['first_overdraft_date']} (min balance {fixed['min_balance']})")
