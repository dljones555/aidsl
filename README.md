<p align="center">
  <br>
  <img src="https://img.shields.io/badge/AI--DSL-v0.1-blue?style=for-the-badge" alt="version">
  <img src="https://img.shields.io/badge/tests-165%20passing-brightgreen?style=for-the-badge" alt="tests">
  <img src="https://img.shields.io/badge/python-3.11+-yellow?style=for-the-badge&logo=python&logoColor=white" alt="python">
  <br><br>
</p>

<h1 align="center">AI DSL</h1>

<p align="center">
  <strong>When Structure Matters.</strong><br>
  An AI concepts first DSL with a parser, compiler, and runtime that turns<br>
  10 lines of declarative intent into repeatable, schema-constrained AI workflows.
</p>

<br>

---

## What This Is

Non-engineers write AI agents, prompts and few shot examples in plain English-like syntax (it's like SQL for AI). Engineers plug them into real infrastructure. Both work from the same `.ai` file — readable, diffable, version controlled. Integrates with a fluent Python AI.

The language calls the LLM only when it needs judgment — extraction, classification, drafting — and runs everything else as deterministic code on the CPU: business rules, validation, schema enforcement. Every response comes back as structured, typed JSON. No surprises, no format drift, no prompt babysitting.

Under the hood: a custom **parser**, **compiler**, and **runtime** turn 10 lines of declarative intent into production-grade AI pipelines with typed prompts, JSON schema constraints, few-shot examples, and response validation — all generated automatically from your schema.

---

## Two On-Ramps

### `.ai` files — for analysts, ops, domain experts

```sql
DEFINE expense:
  merchant    TEXT
  amount      MONEY
  category    ONE OF [travel, meals, equipment, software, office]

FROM receipts.csv
EXTRACT expense EXAMPLES expense_samples
FLAG WHEN amount OVER 500
FLAG WHEN category IS travel AND amount OVER 200
OUTPUT expenses.json
```

No Python. No YAML. No prompt engineering. Hand this to someone who's never written code — they can read it, modify it, and run it.

### Python API — for developers, pipelines, integration

```python
from aidsl import Pipeline, SchemaBuilder

expense = (
    SchemaBuilder("expense")
    .text("merchant")
    .money("amount")
    .enum("category", ["travel", "meals", "equipment", "software", "office"])
    .build()
)

results = (
    Pipeline()
    .source("receipts.csv")
    .extract(expense)
    .examples("expense_samples")
    .flag("amount OVER 500")
    .flag("category IS travel AND amount OVER 200")
    .set(model="gpt-4.1", temperature=0, seed=42)
    .output("expenses.json")
    .run()
)
```

Same compiler, same runtime, same guarantees. Embed it in FastAPI, Celery, cron jobs, notebooks — whatever you already use.

---

## What the Compiler Does for You

You write 10 lines. The compiler handles:

- **Typed prompt generation** — field descriptions, constraints, and output format instructions, all derived from your schema
- **JSON schema enforcement** — every LLM response is validated against a generated schema before it reaches your output
- **Few-shot examples** — plain-text `.examples` files are formatted and prepended to prompts automatically
- **Prompt context** — `.prompt` files inject domain knowledge and tone without touching structure
- **Deterministic rules** — `FLAG WHEN` conditions run as pure code, no LLM involved, identical every time
- **Multi-verb pipelines** — chain `EXTRACT` or `CLASSIFY` with `DRAFT` to go from raw text to structured data to generated responses in one pass

---

## Separation of Concerns

The design enforces a clean split between AI judgment and deterministic logic:

| AI (stochastic) | Rules (deterministic) |
|---|---|
| `EXTRACT`, `CLASSIFY`, `DRAFT` | `FLAG WHEN`, validation, schemas |
| Needs an LLM | Pure code, no LLM |
| Costs money per call | Free |
| Variable by nature | Identical every run |

Business rules never touch the LLM. Only the parts that genuinely require judgment use AI. This is why a 10-line `.ai` file produces more consistent results than a carefully written prompt.

---

## Prompt and Examples as Convention

Prompts and few-shot examples live alongside your `.ai` files in a conventional folder structure:

```
project/
  pipeline.ai              # structure, types, rules, flow
  prompts/
    insurance_context.prompt   # tone, domain knowledge, instructions
  examples/
    expense_samples.examples   # input/output pairs for few-shot learning
```

The `.ai` file owns **what** to extract. The `.prompt` file owns **how** to talk. The `.examples` file teaches **by showing**. All plain text. All version controlled. All diffable.

---

## Agent Pattern

The parser/compiler/runtime are just Python — wrap them in 30 lines and you have an agent:

```
inbox/          →  run_agent.py  →  output/clean/
  receipt1.txt                      output/flagged/
  receipt2.txt                      output/errors/
  invoice.pdf                       output/audit/log.jsonl
```

Drop files in a folder. Run on a cron schedule. Results split by outcome. Every run appends an audit log. The `.ai` file **is** the agent's brain — swap it to change behavior without touching code.

---

## Pluggable by Design

AI DSL owns the **language and compilation** layer. It doesn't own your infrastructure:

- **LLM provider** — anything with an OpenAI-compatible chat endpoint (GitHub Models, OpenAI, Azure, local)
- **Sources** — CSV, JSON files, folders of documents, HTTPS APIs with auth headers
- **Sinks** — JSON output today, but `run()` returns plain dicts — route them anywhere
- **Orchestration** — the Python API is a library, not a framework. Call it from FastAPI, Django, Celery, Airflow, Lambda, a Jupyter notebook, or a shell script

The same `.ai` file works everywhere. Override `FROM`/`OUTPUT` at runtime to adapt to each environment.

---

## Quick Start

```bash
git clone https://github.com/dljones555/aidsl.git
cd aidsl && uv sync

export GITHUB_TOKEN=your_token_here    # GitHub Models — free with any GitHub PAT

uv run python -m aidsl run examples/expense.ai
```

---

## Development

```bash
uv run pytest -v          # 165 tests
uv run ruff check .       # lint
uv run ruff format .      # format
```

---

## License

Business Source License 1.1 — free for non-production use. Commercial or production use requires a license. See [LICENSE](LICENSE) for full terms.

Interested in using AI DSL commercially, or want to collaborate on the ideas here? Reach out to [dljones555](https://github.com/dljones555).
