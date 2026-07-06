"""
Sample bank statement used for the demo.

Why mock data? The competition rules reward a reproducible demo. Live bank APIs
need OAuth and would break on stage. A curated statement guarantees a clean,
repeatable red -> green moment in your video. Swap in a real CSV any time.

The numbers are deliberately designed so the forecast dips BELOW zero on one day,
then stays positive once the single flagged subscription is removed.
"""

from datetime import date

# Opening balance on the first day of the window.
# Tuned so pausing the top DISCRETIONARY charge (MealKit) clears the overdraft,
# while the baseline still dips red — this makes the demo's red->green land.
OPENING_BALANCE = 450.00

# A "salary lands on the 30th" pattern, with recurring charges before it.
# Each row: (date, description, amount)  -- amount negative = money out.
SAMPLE_STATEMENT = [
    (date(2026, 6, 1),  "Opening balance",            0.00),
    (date(2026, 6, 2),  "Grocery - FreshMart",       -54.20),
    (date(2026, 6, 3),  "StreamFlix Monthly",         -15.99),   # recurring
    (date(2026, 6, 4),  "Coffee - BeanThere",          -4.75),
    (date(2026, 6, 5),  "CloudBackup Pro",             -9.99),    # recurring
    (date(2026, 6, 6),  "Fuel - GoGas",               -48.00),
    (date(2026, 6, 8),  "Coffee - BeanThere",          -4.75),
    (date(2026, 6, 10), "GymPlus Membership",         -39.00),    # recurring
    (date(2026, 6, 11), "Grocery - FreshMart",        -61.30),
    (date(2026, 6, 12), "Coffee - BeanThere",          -4.75),
    (date(2026, 6, 14), "Electricity - PowerCo",      -72.40),
    (date(2026, 6, 15), "MusicWave Premium",          -11.99),    # recurring
    (date(2026, 6, 16), "Coffee - BeanThere",          -4.75),
    (date(2026, 6, 18), "Grocery - FreshMart",        -58.10),
    (date(2026, 6, 19), "Ride - QuickCab",            -22.50),
    (date(2026, 6, 21), "Coffee - BeanThere",          -4.75),
    (date(2026, 6, 22), "MealKit Weekly",             -64.00),    # recurring, the villain
    (date(2026, 6, 24), "Pharmacy - CareRx",          -31.20),
    (date(2026, 6, 25), "Coffee - BeanThere",          -4.75),
    (date(2026, 6, 27), "MealKit Weekly",             -64.00),    # recurring, the villain
    (date(2026, 6, 30), "Salary - Acme Corp",        2100.00),    # income
]


def as_text() -> str:
    """Render the statement the way a user might paste it in."""
    lines = [f"Opening balance: {OPENING_BALANCE:.2f}"]
    for d, desc, amt in SAMPLE_STATEMENT:
        if desc == "Opening balance":
            continue
        lines.append(f"{d.isoformat()}  {desc:<24}  {amt:>9.2f}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(as_text())
