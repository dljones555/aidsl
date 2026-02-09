# Agent Guidelines

## Model Selection

Use Sonnet for:
- Adding new verbs that follow existing patterns (CLASSIFY, DRAFT)
- Writing tests
- File I/O changes (new source/sink formats)
- Straightforward parser/compiler extensions
- README and documentation

Use Opus for:
- Architecture decisions (new language features, type system changes)
- Complex parser/compiler changes (nested types, new syntax)
- Debugging subtle issues across parser -> compiler -> runtime
- Design reviews and tradeoff discussions

## Before Making Changes

- Read CLAUDE.md for project conventions
- Read the existing parser.py, compiler.py, runtime.py to understand patterns
- Check pyproject.toml for installed dependencies — prefer what's there
- Run tests before and after changes: `uv run pytest -v`

## Code Patterns

- Follow existing patterns in the codebase
- Use `from __future__ import annotations` in all files
- Parser returns dataclasses, compiler transforms them, runtime executes
- New verbs follow the EXTRACT pattern: parser recognizes keyword, compiler generates prompt, runtime executes and validates
- Deterministic logic (FLAG WHEN, CHECK) should never call the LLM
- All LLM calls go through _make_llm_extractor or similar factory pattern

## Testing

- NO simulated/regex mock extractors in production code
- Use pytest fixtures and httpx mocking for LLM call tests
- Each layer is testable independently:
  - Parser: string in -> Program dataclass out
  - Compiler: Program in -> ExecutionPlan out (check prompt text, JSON schema)
  - Flag evaluator: dict in -> flag reasons out
  - Validator: dict + schema in -> bool out
  - Runtime: mock the LLM, test the full pipeline

## What NOT to Do

- Don't add dependencies without checking if stdlib or existing deps cover it
- Don't build infrastructure (cloud, queues, hosting) — this runs locally
- Don't over-abstract — three similar lines beats a premature helper function
- Don't add features not on the current sprint plan
- Don't hardcode API tokens or model names in source code
