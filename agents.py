"""
CashGuard — multi-agent system (Google ADK).

Course concepts demonstrated here:
  1. Agent / Multi-agent system (ADK)  -> the LlmAgent team below
  2. Security features                 -> redact_pii runs before any model call
  3. Clever tool use                   -> deterministic tools do all math/dates

The team:
  - Parser Agent    : structures the statement (and redacts PII first)
  - Pattern Agent   : finds recurring charges (the habits)
  - Forecast Agent  : projects balance, flags the first overdraft day
  - Advisor Agent   : writes the one-habit recommendation in plain language
  - Orchestrator    : root agent that routes between them

NOTE ON VERSIONS: import paths for ADK can differ slightly between course
versions. If an import fails, open the course's ADK starter notebook and match
its imports — the structure below stays the same. The `run_cashguard()` function
at the bottom does NOT depend on ADK, so your demo works even while you align
the ADK wiring.
"""

from __future__ import annotations
import os

from tools import (
    redact_pii,
    parse_statement,
    detect_recurring,
    pick_pausable,
    forecast_balance,
)

# --- Model config -----------------------------------------------------------
# If you get a "model not found" error, try "gemini-3.5-flash" or "gemini-flash-latest".
MODEL = os.environ.get("CASHGUARD_MODEL", "gemini-2.5-flash")


# ===========================================================================
# ADK MULTI-AGENT DEFINITIONS  (this is your "ADK" concept for the rubric)
# ===========================================================================
try:
    from google.adk.agents import LlmAgent

    parser_agent = LlmAgent(
        name="parser_agent",
        model=MODEL,
        description="Structures a raw bank statement into transactions.",
        instruction=(
            "You receive already-PII-redacted statement text. Call parse_statement "
            "to structure it. Report how many rows were parsed and skipped."
        ),
        tools=[parse_statement],
    )

    pattern_agent = LlmAgent(
        name="pattern_agent",
        model=MODEL,
        description="Finds recurring charges that drive overspending.",
        instruction=(
            "Given structured transactions, call detect_recurring and explain the "
            "top recurring charges by total spend."
        ),
        tools=[detect_recurring],
    )

    forecast_agent = LlmAgent(
        name="forecast_agent",
        model=MODEL,
        description="Projects the balance forward and flags the first overdraft.",
        instruction=(
            "Call forecast_balance to get the daily balance series and the first "
            "overdraft date. Never invent numbers; only report tool output."
        ),
        tools=[forecast_balance],
    )

    advisor_agent = LlmAgent(
        name="advisor_agent",
        model=MODEL,
        description="Recommends the single habit to change, grounded in the data.",
        instruction=(
            "Using the recurring charges and the two forecasts (before and after "
            "removing the biggest recurring charge), tell the user in a warm, plain "
            "tone: (1) the exact date they would overdraw, (2) the one charge to "
            "pause, (3) the new safe date after pausing it. Keep it under 120 words. "
            "Add: 'This is guidance, not financial advice.'"
        ),
    )

    root_agent = LlmAgent(
        name="cashguard_orchestrator",
        model=MODEL,
        description="Coordinates CashGuard's forensics team.",
        instruction=(
            "You investigate a user's cashflow. Delegate in order: parser -> pattern "
            "-> forecast -> advisor. Present the advisor's final recommendation."
        ),
        sub_agents=[parser_agent, pattern_agent, forecast_agent, advisor_agent],
    )

    ADK_AVAILABLE = True
except Exception as _e:  # ADK not installed yet / version mismatch
    ADK_AVAILABLE = False
    root_agent = None


# ===========================================================================
# DETERMINISTIC PIPELINE  (always works — powers the UI + the red->green demo)
# ===========================================================================
def _advisor_summary(villain_rec, base, fixed) -> str:
    """Ask Gemini for the plain-language nudge. Falls back to a template."""
    prompt = (
        "Write a warm, <=120 word alert for a personal-finance app user.\n"
        f"- Without changes they overdraw on: {base['first_overdraft_date']} "
        f"(lowest balance {base['min_balance']}).\n"
        f"- Biggest discretionary recurring charge: {villain_rec['merchant']} "
        f"({villain_rec['occurrences']}x, total {villain_rec['total_spent']}).\n"
        f"- If they pause it, the overdraft becomes: "
        f"{fixed['first_overdraft_date'] or 'no overdraft'} "
        f"(lowest balance {fixed['min_balance']}).\n"
        "End with: 'This is guidance, not financial advice.'"
    )
    try:
        from google import genai

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(model=MODEL, contents=prompt)
        return resp.text.strip()
    except Exception:
        safe = fixed["first_overdraft_date"] or "no overdraft at all"
        return (
            f"Heads up: on {base['first_overdraft_date']} your balance is set to dip "
            f"below zero. The main driver is '{villain_rec['merchant']}', charged "
            f"{villain_rec['occurrences']} times for {villain_rec['total_spent']} total. "
            f"Pause just that one and your projected overdraft moves to {safe}. "
            f"This is guidance, not financial advice."
        )


def run_cashguard(raw_text: str, opening_balance: float) -> dict:
    """
    End-to-end orchestration used by the demo UI.
    Mirrors the ADK team's flow: redact -> parse -> pattern -> forecast x2 -> advise.
    Returns a structured result the UI renders as the red->green timeline.
    """
    # 1. SECURITY: redact before anything leaves the machine.
    safe_text = redact_pii(raw_text)

    # 2. PARSER
    parsed = parse_statement(safe_text)
    txns = parsed["transactions"]
    if not txns:
        return {"error": "No transactions could be parsed. Check the format."}

    # 3. PATTERN / MEMORY
    recurring = detect_recurring(txns)
    villain_rec = pick_pausable(recurring)          # biggest DISCRETIONARY charge
    villain = villain_rec["merchant"] if villain_rec else None

    # 4. FORECAST — baseline and counterfactual
    base = forecast_balance(txns, opening_balance)
    fixed = forecast_balance(txns, opening_balance, remove_merchant=villain) if villain else base

    # 5. ADVISOR
    advice = _advisor_summary(villain_rec, base, fixed) if villain_rec else \
        "No recurring charges detected — your cashflow looks steady."

    return {
        "skipped_rows": parsed["skipped"],
        "recurring": recurring,
        "baseline": base,
        "fixed": fixed,
        "villain": villain,
        "villain_rec": villain_rec,
        "advice": advice,
        "adk_available": ADK_AVAILABLE,
    }


if __name__ == "__main__":
    from mock_data import as_text, OPENING_BALANCE
    import json

    result = run_cashguard(as_text(), OPENING_BALANCE)
    print(json.dumps(
        {k: v for k, v in result.items() if k not in ("baseline", "fixed")},
        indent=2, default=str,
    ))
    print("\nBaseline overdraft:", result["baseline"]["first_overdraft_date"])
    print("After fix:", result["fixed"]["first_overdraft_date"])
