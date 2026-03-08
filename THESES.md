# The 12 Theses of AI DSL

## When English Needs Structure

A slide deck and manifesto for the lingua franca of AI agents.

---

### 1. When English Needs Structure

English is expressive but ambiguous. "Be careful around the dog" is 7
tokens of poetry — a robot needs geometry, velocity caps, sensor weights,
and fallback policies. The DSL separates human intent (English) from
machine execution (typed schemas, deterministic rules, formal contracts).
Both coexist. Neither is eliminated. Structure is where English goes to
become reliable.

### 2. GPU/CPU Separation

Not everything needs an LLM. EXTRACT needs intelligence. FLAG WHEN
doesn't. The DSL makes this boundary explicit at compile time. The
execution plan is a provable artifact showing where money is spent and
where it isn't. Every operation has a type: GPU (costs tokens), CPU
(free), or HITL (costs human time). This is the "query optimizer" for
AI pipelines.

### 3. The Compiler is Smarter Than the User

You write 10 lines. The compiler generates typed prompts, JSON schema
constraints, few-shot example injection, Pydantic validation models, and
response verification — all derived automatically from your schema.
Users express intent. The compiler handles prompt engineering. This is
why a .ai file beats a hand-written prompt every time.

### 4. English and Structure Coexist

Prompts (.prompt files) are English — tone, context, domain knowledge.
Schemas (DEFINE blocks) are structure — types, fields, constraints.
Examples (.examples files) are English-by-example — show, don't tell.
Each lives in its own file. Each is owned by a different role (content
person, business person, developer). They compose without tangling.

### 5. The Execution Plan is the Product

Not the output JSON. The plan itself — showing what went to the LLM,
what was deterministic, what was validated, what was flagged, what it
cost — is the audit artifact. This is what compliance officers,
regulators, insurers, and skeptical stakeholders actually need. No
other framework produces this.

### 6. Cost Estimation at Compile Time

You should know what a pipeline will cost before you run it. CPU ops
are free. GPU ops cost tokens. HITL ops cost labor hours. The DSL
estimates all three from the execution plan before a single API call
is made. Like a SQL EXPLAIN plan but for AI workloads — with dollars
attached.

### 7. Deterministic Rules Never Touch the LLM

FLAG WHEN, RULE WHEN, schema validation, enum enforcement — these are
pure code. Identical every run. Free. Un-injectable. The more business
logic lives here instead of in prompts, the cheaper, safer, and more
predictable the system becomes. This is the single most actionable
insight: if it doesn't need intelligence, don't pay for intelligence.

### 8. Two On-Ramps, One Engine

.ai files for the non-engineer — the analyst, the ops person, the
teenager, the merged-role generalist. Python API for the developer —
FastAPI, Celery, notebooks, ML pipelines. Same compiler, same runtime,
same guarantees. The Python API is generated from the .ai file (one
source of truth, not two maintained in parallel).

### 9. Schema Validation is the Security Firewall

Prompt injection can make an LLM say anything. The Pydantic validator
doesn't care what the LLM says — it only cares whether the output
matches the typed schema. Closed-world enums can't be expanded by
injection. Type enforcement catches garbage. The schema is the wall
that English guardrails can never be.

### 10. Verbs are the Instruction Set

EXTRACT, CLASSIFY, DRAFT are shipped. SUMMARIZE, STAGE, ROUTE,
REVIEW, and CONVERSE are on the roadmap. Each is an atomic AI or
workflow capability with a defined input/output shape, inference
mode, and cost class. New verbs go through a design gate (is it a
distinct capability? does a non-engineer understand it? precision
or creative?). Domain packs extend the vocabulary further (PERCEIVE,
NAVIGATE, MONITOR). Community developers propose and build new verbs
through an open process — these are the equivalent of Salesforce
Flows or MCP tools, but governed by a language standard, not a
platform.

### 11. The Verify Graph Closes the Trust Loop

Every response carries metadata showing how it was verified — which
methods ran (LLM inference, deterministic code, web retrieval, HITL
review), how long each took, what confidence each contributed. This is
the "nutrition label for AI output" — consumer-friendly, machine-
readable, diffable over time. For non-STEM answers (recipes, advice,
business decisions) where formal proofs don't apply, this is how trust
is built and measured.

### 12. Portable by Design

The .ai file runs against any OpenAI-compatible endpoint. No platform
lock-in. No vendor dependency. The language owns the specification; the
runtime is pluggable. Same pipeline works on GitHub Models, OpenAI,
Azure, Anthropic, local models, or a Raspberry Pi. The structure is
yours. The intelligence is commodity. This is what makes it the lingua
franca — it speaks every model's language.

---

## The Vision

AI DSL is the structured layer between English and execution — the
frontman for Python and English working together.

It is the everyman language. The merged-role generalist who can write
SQL but not Python. The teenager learning to program a home robot. The
factory floor operator configuring a quality check. The compliance
officer auditing an AI pipeline. The support desk manager who writes
a triage workflow in 10 lines.

It runs everywhere structure matters: help desks, smart homes, factory
floors, military missions, compliance systems, CRM pipelines, home
robots, and whatever domains come next.

It is not a platform. It is a language. Languages outlast platforms.

Do you speak Bocce?
