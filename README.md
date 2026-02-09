<p align="center">
  <br>
  <img src="https://img.shields.io/badge/AI--DSL-v0.1-blue?style=for-the-badge" alt="version">
  <img src="https://img.shields.io/badge/tests-70%20passing-brightgreen?style=for-the-badge" alt="tests">
  <img src="https://img.shields.io/badge/python-3.12+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="python">
  <br><br>
</p>

<h1 align="center">AI DSL</h1>

<p align="center">
  <strong>Structure beats English.</strong><br>
  A declarative language for AI workflows that non-engineers can read, write, and trust.
</p>

<br>

---

## The Problem

You paste a receipt into ChatGPT and say *"extract the merchant, amount, and category."* It works. Sometimes. Then:

- Run it again — different JSON keys
- Change the wording — different categories
- Hand it to a colleague — completely different output
- Try to audit it — there's nothing to audit

**Prompts are stochastic. Schemas are deterministic.** AI DSL separates what needs AI judgment from what doesn't.

---

## 14 Lines. Typed. Auditable. Repeatable.

```sql
DEFINE expense:
  merchant    TEXT
  amount      MONEY
  category    ONE OF [travel, meals, equipment, software, office]

FROM receipts.csv
EXTRACT expense USE expense_samples
FLAG WHEN amount OVER 500
FLAG WHEN category IS travel AND amount OVER 200
OUTPUT expenses.json
```

That's it. No Python. No YAML. No prompt engineering. The compiler handles:

- Typed prompt generation with JSON schema constraints
- Few-shot examples injected automatically from plain-text files
- Deterministic business rules that never touch the LLM
- Schema validation on every response

---

## How It Works

```
                    ┌─────────────┐
                    │   .ai file  │  ← You write this
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Parser    │  ← Reads your DSL
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Compiler   │  ← Generates typed prompts + JSON schema
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │                         │
     ┌────────▼────────┐    ┌──────────▼──────────┐
     │   LLM Runtime   │    │   Flag Evaluator    │
     │  (AI judgment)   │    │ (deterministic rules)│
     └────────┬────────┘    └──────────┬──────────┘
              │                         │
              └────────────┬────────────┘
                           │
                    ┌──────▼──────┐
                    │   Output    │  ← Structured JSON
                    └─────────────┘
```

**Two worlds, clearly separated:**

| AI (stochastic) | Rules (deterministic) |
|---|---|
| EXTRACT, CLASSIFY | FLAG WHEN |
| Needs LLM | Pure code, no LLM |
| Costs money per call | Free |
| Variable by nature | Identical every run |

---

## Features

### Verbs — What AI Does

| Verb | Purpose | Example |
|------|---------|---------|
| `EXTRACT` | Pull structured fields from text | `EXTRACT expense` |
| `CLASSIFY` | Assign a category from a set | `CLASSIFY type INTO [a, b, c]` |

### Types — What Data Looks Like

| Type | Description | Example |
|------|-------------|---------|
| `TEXT` | Free-form string | `merchant TEXT` |
| `MONEY` | Dollar amount (numeric) | `amount MONEY` |
| `NUMBER` | Numeric value | `score NUMBER` |
| `YES/NO` | Boolean | `approved YES/NO` |
| `ONE OF [...]` | Constrained enum | `category ONE OF [a, b, c]` |

### Modifiers — What Controls Behavior

| Modifier | Purpose | Example |
|----------|---------|---------|
| `FLAG WHEN` | Deterministic business rule | `FLAG WHEN amount OVER 500` |
| `WITH` | Named prompt context | `EXTRACT x WITH my_context` |
| `USE` | Few-shot examples | `EXTRACT x USE my_samples` |

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/dljones555/aidsl.git
cd aidsl
uv sync

# Set your API token (GitHub Models — free with any GitHub PAT)
export GITHUB_TOKEN=your_token_here

# Run the expense processor
uv run python -m aidsl run examples/expense.ai
```

---

## Prompt Library

**WITH** loads a `.prompt` file — system context for tone and domain knowledge:

```
# prompts/insurance_context.prompt

You are a claims processor for a large insurance company.
Policy types include auto, home, life, and commercial.
Be precise with categorization.
```

**USE** loads a `.examples` file — few-shot input/output pairs:

```
# examples/expense_samples.examples

INPUT: Uber ride to airport, $47.50
OUTPUT: {"merchant": "Uber", "amount": 47.50, "category": "travel"}

INPUT: MacBook Pro from Apple Store, $2499.00
OUTPUT: {"merchant": "Apple Store", "amount": 2499.00, "category": "equipment"}
```

Both are plain text. Version controlled. Diffable. Auditable.

The `.ai` file owns structure. The `.prompt` file owns tone. The `.examples` file teaches by showing.

---

## Real Example: Ticket Triage

```sql
FROM tickets.csv
CLASSIFY type INTO [policy, claim, inquiry, complaint]
  WITH insurance_context USE ticket_samples
FLAG WHEN type IS complaint
OUTPUT classified.json
```

This reads support tickets, classifies each one using domain context and few-shot examples, flags complaints for escalation, and writes structured JSON — all in 5 lines.

---

## Why Not Just Use Prompts?

| | Raw Prompts | AI DSL |
|---|---|---|
| **Output format** | Whatever the LLM feels like | Schema-constrained JSON |
| **Business rules** | Baked into prompt (unreliable) | Deterministic code (FLAG WHEN) |
| **Consistency** | Varies run to run | Typed, validated, repeatable |
| **Audit trail** | Copy-paste from chat | Versioned .ai files |
| **Who can write it** | Prompt engineers | Anyone who can read SQL |
| **Few-shot examples** | Manual copy-paste | Named, reusable .examples files |

---

## Development

```bash
uv run pytest -v          # 70 tests
uv run ruff check .       # lint
uv run ruff format .      # format
```

---

<p align="center">
  <strong>Schema Labs</strong><br>
  <em>Structure beats English.</em>
</p>
