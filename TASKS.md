# Sprint Tasks

Each task is scoped to one focused session. Model recommendation in brackets.

## Day 0 — Foundation (before building features)

- [x] **T01** [Sonnet] Remove mock extractor from runtime.py ✓
  - Delete _extract_mock, _guess_merchant, _match_category, _CATEGORY_KEYWORDS
  - Remove --mock flag from __main__.py
  - Remove `import re` if no longer needed
  - Clean up run() to only have the LLM path

- [x] **T02** [Sonnet] Add pytest infrastructure ✓
  - Add pytest and ruff to pyproject.toml dev dependencies
  - Create tests/ directory
  - Create tests/conftest.py with shared fixtures:
    - mock_llm_response: patches httpx.Client.post to return controlled JSON
    - sample_program: returns a parsed Program for the expense schema
    - sample_plan: returns a compiled ExecutionPlan
    - tmp_csv: writes a temp CSV and returns the path

- [x] **T03** [Sonnet] Write tests for existing code ✓
  - tests/test_parser.py: parse DEFINE, FROM, EXTRACT, FLAG WHEN, OUTPUT
  - tests/test_compiler.py: prompt generation, JSON schema, enum constraints
  - tests/test_flags.py: flag evaluator with OVER, UNDER, IS, AND/OR combos
  - tests/test_validator.py: valid records, missing fields, bad enums, type coercion
  - tests/test_runtime.py: full pipeline with mocked LLM returning good/bad JSON

## Day 1 — Language: Verbs and Prompt Library

- [x] **T04** [Sonnet] Add CLASSIFY verb ✓
  - Parser: recognize CLASSIFY <field> INTO <schema> or similar
  - Compiler: generate classification prompt with enum constraint
  - Tests: parser, compiler output, end-to-end with mock

- [x] **T05** [Sonnet] Add DRAFT verb with prompt library ✓ (split into T05a-d below)
  - Parser: recognize DRAFT <output_field> WITH <prompt_name>
  - Load .prompt files from prompts/ folder relative to .ai file
  - Compiler: inject prompt text into LLM system message
  - Tests: prompt file loading, compiler output, missing prompt error

- [x] **T05a** [Sonnet] WITH keyword + .prompt file loading ✓
- [x] **T05b** [Sonnet] USE keyword + .examples file loading ✓
- [x] **T05c** [Sonnet] DRAFT verb v1 (simple — append field to record) ✓

- [x] **T05d** [Sonnet] DRAFT v2 — {field} placeholder substitution ✓
  - Support {field} placeholders in .prompt templates, substituted from record before LLM call
  - Hybrid approach: deterministic scaffolding (known fields) + creative generation (LLM)
  - e.g. "Write a reply to this {type} from {name}, policy {policy_number}"
  - Compiler substitutes known fields, LLM generates the creative parts
  - Resolved prompt saved as _draft_prompt in output JSON for audit trail
  - Remaining items moved to PBI-DRAFT-V3

## Day 2 — Types, Sources, and Config

- [x] **T06a** [Opus] Add nested/referenced types ✓
  - Parser: LIST OF <type> for arrays, bare type name for nested object references
  - Compiler: recursive JSON schema generation via _field_to_json_schema / _schema_to_json
  - Validator: recursive _validate_object for nested objects and arrays
  - Examples: invoice.ai (LIST OF line_item), contact.ai (reusable address type ref)
  - Tests: 21 tests — parser, compiler, validator, end-to-end (test_nested.py)

- [x] **T06b** [Sonnet] FROM folder source ✓
  - FROM supports directory path (e.g. FROM invoices/) — reads all non-hidden files
  - Runtime: _load_source detects folder vs CSV, _row_to_text handles both formats
  - Standard CSV support: multi-column CSVs sent as JSON to LLM, clean _source in output
  - Examples: invoices/ folder, contacts.csv (standard multi-column CSV)
  - Tests: 15 tests — folder loading, _row_to_text, standard CSV (test_folder_source.py)

- [x] **T07** [Sonnet] Add SET block ✓
  - Parser: SET MODEL, SET TEMPERATURE, SET TOP_P, SET SEED
  - Settings dataclass flows through compiler onto ExecutionPlan
  - Runtime: _apply_settings injects params into both extract and draft LLM calls
  - SET MODEL overrides AIDSL_MODEL env var; unset params use API defaults
  - Example: expense.ai updated with SET MODEL gpt-4.1, TEMPERATURE 0, SEED 42
  - Tests: 13 tests — parser, compiler passthrough, runtime apply (test_set.py)

- [x] **T10+T11** [Sonnet] JSON file source + HTTPS API source ✓
  - JSON files: array or single object, auto-detected by .json extension
  - Folders: .json files parsed (arrays flattened), .txt kept as text blobs
  - HTTPS API: FROM https://... does GET, parses JSON response as records
  - SET HEADER for API auth (e.g. SET HEADER Authorization Bearer token)
  - Query params work in URL (e.g. ?per_page=5)
  - Examples: tickets.json, tickets_json.ai, api_demo.ai, api_public.ai, api_github.ai
  - Tests: 13 tests — JSON source (7), API source (6)

- [ ] **T12** [Sonnet] Build consistency comparison script
  - Run same extraction 5x with raw prompt (no schema)
  - Run same extraction 5x with DSL (schema-constrained)
  - Output report: field-by-field consistency scores
  - Show category drift, amount format drift, key name drift

- [ ] **T13** [Sonnet] Create demo .ai files for other use cases
  - Support ticket triage example
  - Invoice extraction example (uses nested types)
  - Shows breadth of the DSL

## Day 4 — Polish

- [x] **T14** [Sonnet] Write README.md ✓
  - What it is, why it exists (the "calculator vs spreadsheet" pitch)
  - Quick start: install, run expense example
  - DSL syntax reference
  - Examples

- [ ] **T15** [Sonnet] End-to-end cleanup
  - Run all tests, fix failures
  - Lint and format
  - Verify demo runs in one command
  - Final push to GitHub

---

## Product Backlog (PBI)

Items below are scoped but not scheduled. Pull into a sprint day when ready.

- [ ] **PBI-DRAFT-V3** [Sonnet] DRAFT v3 — mail merge, output templates, creative temp
  - If template is 100% placeholders with no creative prompt, skip LLM call (free mail merge)
  - Support output templates for formatted responses (email headers, signatures, structure)
  - Target use case: customer service email auto-replies, chatbot responses, form letters
  - temp 0.7 creative mode (vs temp 0 for EXTRACT/CLASSIFY) — ties into T09

- [ ] **PBI-INBOX** Inbox/outbox/archive agent runner pattern
  - FROM inbox/ → process files → move processed to archive/
  - Write structured outputs to outbox/
  - Error handling: failed files stay in inbox or go to outbox/errors/
  - Ties into INFRA_DESIGN.txt (cron + folder pattern)
  - Design needed: partial failure, retry semantics, file locking
  - This is an ops/deployment feature, not a language feature — build after core DSL is solid

- [ ] **PBI-CASE-INSENSITIVE** Make DSL keywords case-insensitive
  - Convention is uppercase but parser should accept lowercase/mixed case
  - One file change (parser.py), ~15 touch points
  - Use `upper = stripped.upper()` for keyword matching, preserve original case for values

- [X] **PBI-PYTHON-API** Composable fluent Python API (LINQ-style)
  - Thin builder layer: `Schema("invoice").text("vendor").money("total").list_of("items", line_item)`
  - Chainable pipeline: `Pipeline().source(...).extract(...).flag(...).output(...).run()`
  - Builds Program AST directly — same compiler/runtime underneath, zero new infra
  - Enables embedding in FastAPI, Celery, queues, cron jobs, notebooks
  - Two on-ramps: .ai files for analysts, Python API for developers
  - `.run_one(text)` for single-record processing (API/webhook use case)
  - ~150 lines estimated — builder classes over existing Program/Schema dataclasses

- [ ] **PBI-COMPILE-VALIDATION** Compile-time validation (was T08)
  - Check schema references exist (EXTRACT names a defined schema)
  - Check FLAG WHEN fields exist in the schema
  - Check enum values in FLAG conditions match schema enums
  - Report errors with line numbers

- [ ] **PBI-VERB-PARAMS** Compiler-chosen inference params per verb (was T09)
  - EXTRACT, CLASSIFY: temp 0, fixed seed (precision)
  - DRAFT: temp 0.7 (creative)
  - SET block overrides these defaults

- [ ] **PBI-PDF-IMAGE** PDF and image ingestion
  - FROM supports .pdf files (OCR/text extraction before LLM)
  - FROM supports image files (.png, .jpg) via OCR or vision model
  - Plugin architecture: `FROM invoices/ USING tesseract` or similar
  - Core question: build OCR or integrate (Tesseract, Azure Doc Intelligence, AWS Textract)
  - This is the #1 customer-facing gap — invoices and receipts are PDFs/images, not CSV

- [ ] **PBI-OUTPUT-FORMATS** Flexible output sinks
  - OUTPUT detects .json/.csv by extension, writes accordingly
  - CSV output with headers from schema fields
  - Webhook/API POST output (send results to endpoint)
  - Database output (SQLite, PostgreSQL via connection string)

- [ ] **PBI-COST-CONTROL** Token usage and cost guardrails
  - Track token usage per run (input/output tokens)
  - SET MAX_TOKENS, SET MAX_COST budget limits
  - Dry run mode: show what would be processed without calling LLM
  - Per-row token estimates before execution

- [ ] **PBI-PAGINATION** API pagination support
  - Handle paginated API responses (next page links, offset/limit)
  - SET PAGE_SIZE, SET MAX_PAGES controls
  - Auto-follow Link headers or cursor-based pagination

- [ ] **PBI-ERROR-RECOVERY** Partial failure and retry
  - Resume from last successful row on failure
  - Checkpoint file for long-running batch jobs
  - Per-row error capture without aborting the whole run
  - Ties into PBI-INBOX (retry semantics)

- [ ] **PBI-COMPLIANCE** Regulated environment support
  - SET ENDPOINT for self-hosted / private LLM endpoints (Azure OpenAI, on-prem)
  - REDACT keyword: mask PII fields before sending to LLM, restore after
  - Audit logging: full request/response trail per row
  - RBAC: who can run which .ai files, who approves flagged records
  - Encryption at rest for output files
  - Structural advantages already in place: deterministic FLAG WHEN, schema constraints, .ai file as audit artifact

- [ ] **PBI-PERFORMANCE** Scale and throughput
  - Concurrent/parallel LLM calls (async httpx, configurable concurrency)
  - Streaming output: write results as they complete, not all at end
  - Large file handling: chunked reading for big CSVs/JSON
  - Progress bar / ETA for batch runs

- [ ] **PBI-RUNTIME-CONFIG** Decouple source/output paths from .ai file definitions
  - Runtime config layer so .ai files are portable across environments
  - FROM/OUTPUT become overridable at invocation time
  - e.g. `aidsl run pipeline.ai --from inbox/ --output output/`
  - .ai file defines defaults; CLI flags or Python API kwargs override them
  - Enables same pipeline.ai for dev (local folders) and prod (S3, API, etc.)

- [x] **PBI-KEYWORD-CLARITY** Rename WITH/USE keywords for readability ✓
  - `WITH` → `PROMPT`, `USE` → `EXAMPLES` across parser, compiler, examples, tests, API, docs
  - New syntax: `EXTRACT expense PROMPT context EXAMPLES samples`
  - Python API: `.with_prompt()` → `.prompt()`, `.use_examples()` → `.examples()`
