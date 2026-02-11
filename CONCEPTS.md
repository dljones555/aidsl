# AI DSL — Core Concepts

The vocabulary and design primitives of the DSL. Every verb, type, and keyword
maps to a first-class AI or workflow concept. This shared language is used in
design discussions, user documentation, and the DSL syntax itself.

## Design Principle

**Structure beats English.** Prompts are stochastic. Schemas are deterministic.
The DSL separates what needs AI judgment from what doesn't, and constrains
AI output with typed schemas so results are consistent, auditable, and repeatable.

## Nouns (Data)

**Schema** — A typed definition of a structured object. Schemas are the core
contract between the DSL author and the AI. They constrain LLM output to
specific fields with specific types.
```
DEFINE expense:
  merchant  TEXT
  amount    MONEY
  category  ONE OF [travel, meals, equipment]
```

**Field Types:**
- `TEXT` — Free-form string (name, description, address)
- `MONEY` — Numeric dollar amount, no currency symbol
- `NUMBER` — Numeric value (quantity, score, count)
- `YES/NO` — Boolean (true/false)
- `ONE OF [values]` — Constrained enum, LLM must pick exactly one

**Source** — Where input data comes from (CSV, JSON, API).
**Output** — Where structured results go (JSON, CSV).

## Verbs (Actions)

Each verb represents a distinct AI capability. The compiler chooses the right
inference parameters for each verb type. Users express intent; the compiler
handles prompt engineering.

**EXTRACT** — Pull multiple structured fields from unstructured text.
The workhorse verb. Takes raw text, returns a typed record matching a schema.
Use when you need several fields from a document.
- Inference: precision (temp 0, fixed seed)
- Input: unstructured text
- Output: typed record (multiple fields)
```
EXTRACT expense
```

**CLASSIFY** — Assign a single category from a defined set.
The most common AI task in business workflows. Takes text, returns one label.
Use when the only question is "which bucket does this belong in?"
- Inference: precision (temp 0, fixed seed)
- Input: unstructured text
- Output: single enum value
```
CLASSIFY INTO [policy, claim, inquiry, complaint]
```

**DRAFT** — Generate text using a named prompt template.
The creative verb. Takes structured data, produces human-readable output.
Use for emails, summaries, reports, notifications.
- Inference: creative (temp 0.7)
- Input: structured record + named prompt template
- Output: generated text
```
DRAFT response PROMPT customer_reply
```

## Modifiers (Control)

**FLAG WHEN** — Deterministic business rule. No LLM involved. Pure logic
applied after AI extraction. Auditable, predictable, 100% consistent.
```
FLAG WHEN amount OVER 500
FLAG WHEN category IS travel AND amount OVER 200
```

**PROMPT** — Reference a named prompt template from the prompts/ folder.
Separates tone/wording (content person) from structure/rules (business person).
```
DRAFT summary PROMPT executive_brief
```

**EXAMPLES** — Reference a named examples file from the examples/ folder.
Few-shot learning: show the LLM input/output pairs so it mimics the pattern.
More reliable than describing what you want — demonstrate it instead.
```
EXTRACT expense EXAMPLES expense_samples
CLASSIFY type INTO [a, b] EXAMPLES ticket_samples
```

**SET** — Override default inference parameters. Power user feature.
Most users never touch this. The compiler picks smart defaults per verb.
```
SET temperature 0
SET seed 42
SET model openai/gpt-4.1
```

## The Two Worlds

The DSL enforces a clean separation between AI and deterministic logic:

| AI (stochastic) | Rules (deterministic) |
|---|---|
| EXTRACT | FLAG WHEN |
| CLASSIFY | Validation |
| DRAFT | Schema constraints |
| Needs LLM | Pure code, no LLM |
| Variable by nature | Identical every run |
| Costs money per call | Free |

This separation is why the DSL produces more consistent results than raw
prompting. Business rules don't go through an LLM. Only the parts that
genuinely require judgment use AI.

## Prompt Library

Named `.prompt` files in a `prompts/` folder. Referenced by name with `PROMPT`.

- `.ai` file — owns structure, types, rules, flow (business person)
- `.prompt` file — owns tone, wording, instructions (content person)

Both are plain text, version controlled, diffable, auditable.

## Examples Library

Named `.examples` files in an `examples/` folder. Referenced by name with `EXAMPLES`.

Format — plain text `INPUT:/OUTPUT:` pairs, blank line between:
```
INPUT: Uber ride to airport, $47.50
OUTPUT: {"merchant": "Uber", "amount": 47.50, "category": "travel"}

INPUT: MacBook Pro from Apple Store, $2499.00
OUTPUT: {"merchant": "Apple Store", "amount": 2499.00, "category": "equipment"}
```

Few-shot examples are injected into the system prompt before the user's input.
The LLM sees the pattern and follows it — more effective than instructions alone.

## Design Rules for New Verbs

When adding a verb to the DSL, answer these questions:
1. Is it a distinct AI capability, not just a variation of an existing verb?
2. Does a non-engineer understand the verb name immediately?
3. Is it precision (temp 0) or creative (temp > 0)?
4. What is the input shape? (text, record, list)
5. What is the output shape? (record, single value, text)
6. Can the output be schema-validated?
