# AI DSL

Structured DSL for AI workflows. Schema-constrained extraction with deterministic business rules.

See `CONCEPTS.md` for AI-first vocabulary, verb definitions, and design principles.

## Architecture

- `aidsl/parser.py` — Reads .ai files into AST (Program, Schema, FieldDef, FlagRule)
- `aidsl/compiler.py` — AST -> ExecutionPlan (generates typed prompts, builds flag evaluators)
- `aidsl/runtime.py` — Executes plan: reads source, calls LLM, validates output, applies flags
- `aidsl/__main__.py` — CLI entry point

## Commands

- **Run:** `uv run python -m aidsl run examples/expense.ai`
- **Tests:** `uv run pytest -v`
- **Lint:** `uv run ruff check .`
- **Format:** `uv run ruff format .`

## Environment

- `GITHUB_TOKEN` — GitHub PAT with models:read permission (for LLM calls)
- `AIDSL_MODEL` — Override model (default: openai/gpt-4.1-mini)

## Conventions

- Use `from __future__ import annotations` in all Python files
- Use dataclasses for data models
- Use `Path` from pathlib for file operations
- LLM calls go through GitHub Models API (OpenAI chat completions compatible)
- Tests use pytest with `tmp_path` for file isolation and mock httpx for LLM calls
- Never hardcode API tokens — always use environment variables
- Keep parser, compiler, and runtime as separate concerns

## DSL Syntax

```
DEFINE <name>:
  <field>  TEXT | MONEY | NUMBER | YES/NO | ONE OF [values]

FROM <source>
EXTRACT <schema>
FLAG WHEN <condition> [AND|OR <condition>]
OUTPUT <filename>
```

## Git Workflow

- **main** is the stable branch. Never commit broken code to main.
- **Feature branches** for all new work: `feature/<name>` (e.g., `feature/classify-verb`)
- Commit after tests pass and lint is clean.
- Merge feature branches to main when complete.
- Write clear commit messages: what changed and why.

## Testing Approach

- Mock LLM responses via httpx monkey-patching or pytest fixtures
- Test parser with .ai file strings, not files when possible
- Test compiler output (prompt text, JSON schema) independently
- Test flag evaluator with plain dicts — no LLM needed
- Test validation with edge cases (wrong types, missing fields, bad enums)
