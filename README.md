# 💸 CashGuard — Proactive Cashflow-Forensics Concierge

> A multi-agent AI concierge that investigates the chain of events about to overdraw your bank account **before it happens**, and names the single habit to change to stay in the green.

**Kaggle · AI Agents: Intensive Vibe Coding Capstone** · Track: **Concierge Agents**

---

## 1. The problem

Most people discover they've run out of money *after* the overdraft fee hits. Existing budgeting apps summarize the past; they don't investigate the near future or point to the one thing to change. For anyone living close to their balance, that gap is expensive and stressful.

## 2. The solution

CashGuard treats your statement like a crime scene. A team of agents reconstructs the causal chain leading to an overdraft, then runs a counterfactual: *"pause this one recurring charge and you stay positive."* Every claim is grounded in a real transaction — no blind predictions.

## 3. Why agents (not a single prompt)

The work is genuinely multi-step and specialised, so it's split across a team, each with one job and its own tools:

| Agent | Responsibility | Tools |
|---|---|---|
| **Parser** | Redact PII, structure the raw statement | `redact_pii`, `parse_statement` |
| **Pattern/Memory** | Find recurring charges (the habits) | `detect_recurring` |
| **Forecast** | Project balance, flag first overdraft day | `forecast_balance` |
| **Advisor** | Write the one-habit recommendation | Gemini |
| **Orchestrator** | Route between the agents | ADK |

All arithmetic and date math live in **deterministic Python tools** — the agents *orchestrate*, they don't calculate. That keeps the forecast trustworthy.

## 4. Architecture

```
                 ┌──────────────────────────────┐
   statement ──▶ │   Orchestrator Agent (ADK)   │
                 └──────────────────────────────┘
                    │        │         │        │
              ┌─────▼──┐ ┌───▼────┐ ┌──▼─────┐ ┌▼────────┐
              │ Parser │ │Pattern │ │Forecast│ │ Advisor │
              │ +PII   │ │/Memory │ │  x2    │ │         │
              └────────┘ └────────┘ └────────┘ └─────────┘
                    │        │         │        │
                    ▼        ▼         ▼        ▼
              deterministic tools (parse / detect / forecast)
```

## 5. Course concepts demonstrated (≥3 required)

1. **Multi-agent system (ADK)** — the `LlmAgent` team in `agents.py`.
2. **Security features** — `redact_pii()` masks account numbers, emails and phone numbers *before* any data reaches the model (`tools.py`).
3. **Deployability** — one-command Gradio app (`app.py`); deploy notes below.
4. **Clever tool use** — deterministic tools own all math/date logic so forecasts are reproducible and auditable.

## 6. Setup & run

```bash
# 1. Install
pip install -r requirements.txt

# 2. Add your key (NEVER commit keys)
export GEMINI_API_KEY="your_key_here"

# 3a. Sanity-check the tools
python tools.py

# 3b. Run the full multi-agent pipeline in the terminal
python agents.py

# 3c. Launch the demo UI (what the video records)
python app.py
```

The app opens with a sample statement pre-loaded. Click **Investigate my cashflow**, then toggle **Apply CashGuard's fix** to watch the timeline flip **red → green**.

## 7. Demo highlight

- **Red path:** projected overdraft on **2026-06-22**.
- **Green path:** pause the biggest discretionary charge (**MealKit Weekly**) → **no overdraft**.
- **Failure recovery:** any unparseable statement row is flagged and skipped, not crashed on.

## 8. Security note

No secrets are stored in this repo. The Gemini API key is read from the `GEMINI_API_KEY` environment variable. PII is redacted client-side before model calls.

## 9. Deploying (optional, for extra credibility)

Any of these satisfy the "public project link" requirement:
- **Hugging Face Spaces** (Gradio SDK) — push this folder, set `GEMINI_API_KEY` as a Space secret.
- **Google Cloud Run** — containerize `app.py`.
- Or simply link **this public GitHub repo** (the rules accept a repo with setup instructions).

## 10. Disclaimer

CashGuard provides informational guidance, not financial advice.
