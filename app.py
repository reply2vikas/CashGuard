"""
CashGuard demo UI (Gradio) — this is what you screen-record for the 5-min video.

The killer shot: paste a statement -> the timeline shows a RED overdraft day ->
toggle 'Apply CashGuard's fix' -> the same timeline turns GREEN.

Run:
    pip install -r requirements.txt
    export GEMINI_API_KEY=your_key_here      # never hard-code it
    python app.py
"""

from __future__ import annotations
import gradio as gr

from mock_data import as_text, OPENING_BALANCE
from agents import run_cashguard


def _timeline_markdown(series: list[dict]) -> str:
    """Tiny text 'chart' so the balance trend is visible without extra libs."""
    if not series:
        return "_no data_"
    lo = min(p["balance"] for p in series)
    hi = max(p["balance"] for p in series)
    span = (hi - lo) or 1
    rows = []
    for p in series:
        filled = int((p["balance"] - lo) / span * 20)
        bar = "█" * max(filled, 0)
        flag = "  ⬅ OVERDRAFT" if p["balance"] < 0 else ""
        color = "🔴" if p["balance"] < 0 else "🟢"
        rows.append(f"`{p['date']}` {color} {bar} {p['balance']:>8.2f}{flag}  ·{p['event']}")
    return "\n\n".join(rows)


def analyze(statement_text: str, apply_fix: bool):
    result = run_cashguard(statement_text, OPENING_BALANCE)
    if "error" in result:
        return result["error"], "", ""

    forecast = result["fixed"] if apply_fix else result["baseline"]
    header = "### 🟢 With CashGuard's fix applied" if apply_fix else "### 🔴 Current path"
    od = forecast["first_overdraft_date"]
    status = (f"**Projected overdraft: {od}** (lowest balance {forecast['min_balance']})"
              if od else f"**No overdraft — you stay positive** (lowest {forecast['min_balance']})")

    rec = result.get("villain_rec")   # biggest DISCRETIONARY (pausable) charge
    advice = result["advice"]
    if rec:
        advice = (f"**The one habit:** pause **{rec['merchant']}** "
                  f"({rec['occurrences']}× · {rec['total_spent']} total)\n\n" + advice)

    skipped = result["skipped_rows"]
    note = f"\n\n_Recovered gracefully from {len(skipped)} unparseable row(s)._" if skipped else ""
    adk = "✅ ADK team active" if result["adk_available"] else "ℹ️ Running deterministic pipeline (wire ADK to enable the agent team)"

    return f"{header}\n\n{status}{note}\n\n_{adk}_", _timeline_markdown(forecast["series"]), advice


with gr.Blocks(title="CashGuard") as demo:
    gr.Markdown("# 💸 CashGuard\n### Your proactive cashflow-forensics concierge\n"
                "Paste a statement. CashGuard investigates the chain about to overdraw "
                "you and names the one habit to change.")
    with gr.Row():
        with gr.Column():
            statement = gr.Textbox(label="Bank statement", lines=16, value=as_text())
            apply_fix = gr.Checkbox(label="Apply CashGuard's fix (see red → green)", value=False)
            btn = gr.Button("Investigate my cashflow", variant="primary")
        with gr.Column():
            status = gr.Markdown()
            advice = gr.Markdown()
    timeline = gr.Markdown(label="Balance timeline")

    btn.click(analyze, [statement, apply_fix], [status, timeline, advice])
    apply_fix.change(analyze, [statement, apply_fix], [status, timeline, advice])


if __name__ == "__main__":
    demo.launch()
