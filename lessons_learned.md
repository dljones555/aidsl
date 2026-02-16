# Lessons Learned — AI DSL Project

## PMF Reality

- **The extraction/classification layer is on the model treadmill.** GPT and Claude now do structured output natively. EXTRACT and CLASSIFY are competing with a single API parameter. Shelf life: 6-18 months before models subsume it.
- **Funded competitors own every adjacent space.** Reducto ($108M) for document extraction, Delve ($32M) for compliance automation, Instructor (free/open source) for structured output. A solo founder can't out-resource them.
- **The general-purpose DSL is high risk as a product.** "SQL for AI" sounds good in a pitch but nobody searches for it. Developer tools need massive adoption before they monetize, and the base rate for solo dev tools reaching sustainability is very low.
- **The viable solo path is vertical + consulting hybrid.** Pick one industry, solve one workflow end-to-end, charge $200-400/hr consulting while the product matures. $200K-$500K/yr is the realistic ceiling. Timeline: 2-3 years to sustainability.
- **Talk to buyers before building more.** The pattern of build-for-weeks-then-discover-it's-crowded is solved by 5 conversations with people who have budget and a manual workflow they hate.

## Market Validation (Week 2)

- **The core functionality is commoditized.** Major platforms already have AI verbs in SQL: Databricks `AI_CLASSIFY()`, `AI_EXTRACT()`, Snowflake `COMPLETE()`. This isn't a gap — it's a solved problem at the platform layer.
- **Open source covers both sides.** DuckDB, Polars, jq handle the CPU/deterministic side. OpenAI `json_schema` handles structured output. The full stack exists, just scattered.
- **The low-code gap may still be real.** Analysts and ops teams don't have Databricks seats ($$$) or Python skills. Assembling DuckDB + OpenAI + jq is a developer task. There may be a niche for packaged, accessible AI workflows — but it's a narrow wedge.
- **The execution plan is a genuine differentiator for regulated work.** Audit trail showing what went to the LLM vs what was deterministic is something compliance teams actually want. This is a consulting selling point, not a product feature.
- **Sell the pattern and skill, not the tool.** The transferable offering is: "I can audit your LLM workflows, identify GPU/CPU boundaries, structure your AI pipelines, and deliver auditable execution plans." The `.ai` files are your delivery accelerator.

## Architecture Insights

- **LLM workflows decompose into GPU (intelligence) and CPU (logic).** EXTRACT/CLASSIFY need GPU. FLAG WHEN, GROUP BY, COUNT, SORT are CPU operations — 10,000-100,000x cheaper. The DSL explicitly codifies this boundary.
- **Three approaches occupy a spectrum.** Code-writing (GPU does everything, flexible, expensive, unpredictable) → Tools/MCP (CPU executes, GPU orchestrates, middle ground) → DSL (GPU extracts, CPU does everything else, cheapest, least flexible).
- **FLAG WHEN is the interesting pattern.** It's not just a feature — it's a principle: audit your LLM workflow, find every operation that doesn't require intelligence, move it to code. This applies to any LLM system, not just this DSL.
- **The DSL is missing the full "CPU verb" set.** FLAG WHEN is just WHERE. GROUP BY, SUM, COUNT, HAVING, SORT, LIMIT, JOIN are all zero-token CPU operations that would complete the picture. The DSL is a GPU/CPU allocation plan.
- **Pydantic/Instructor is the middle ground.** Schema validation runs on CPU, but retries on validation failure cost GPU. The DSL goes further — FLAG WHEN does *work* on CPU, not just validation.

## Takeaways

- **The project's real value is learning, not shipping.** We learned Claude Code orchestration, iterative co-development, and discovered the GPU/CPU decomposition pattern. That carries forward regardless of what happens to aidsl.
- **Spaced iteration beats single-prompt building.** The marinating time between sessions is where the real thinking happens — pivots, pattern recognition, questioning assumptions. Usage constraints force intentionality.
- **The co-creative workflow is the skill.** Decompose the problem, point the AI at it, walk away, come back with better questions. The tool gets cheaper quarterly; the ability to architect and redirect doesn't.
- **The transferable insight is boundary detection.** In any LLM system: what needs intelligence (GPU) vs what's just logic (CPU)? FLAG WHEN is one answer. The general principle — systematically extracting deterministic logic from LLM calls — is applicable everywhere.
- **If this becomes something, it's as internal tooling powering a vertical solution.** The .ai file is your development speed advantage, not a user-facing product. The FLAG WHEN audit trail is what regulated buyers actually need. The DSL is the engine, not the car.

## Project Conclusion

- **Status: core complete, product paused.** 3 verbs, 5 types, multiple sources, 165 tests, Python API. The DSL works. Further feature development (PDF ingestion, output formats, etc.) is not justified without customer pull.
- **What to carry forward:** (1) The GPU/CPU decomposition pattern as a consulting framework. (2) The co-creative Claude Code workflow as a repeatable skill. (3) The execution plan concept for regulated AI work.
- **Next move: find customers, not features.** Offer AI workflow structuring as a service. Use the DSL as internal tooling and proof of expertise. Let client needs drive what gets built next.

## Notes — 2/16/2026

### Framing: DSL as Static Analysis for AI Workflows
- The DSL is akin to **static analysis** for LLM pipelines. Static analysis catches bugs before runtime; the execution plan catches waste, non-determinism, and audit gaps before inference. The compiler draws the GPU/CPU boundary at compile time, not runtime.
- The execution plan is an **audit artifact** spanning CPU, GPU, compute cost, energy cost, and human-in-the-loop factors. Not just "what did the LLM do" but "what resources were consumed and who reviewed it."

### Ideation Sources
- **Karpathy ([post](https://x.com/karpathy/status/2023476423055601903)) and Thomas Wolf ([post](https://x.com/Thom_Wolf/status/2023387043967959138)) (2/16/2026)** — Both point toward typed, formally verifiable languages winning as LLMs reshape software. The DSL's schema enforcement, compile-time GPU/CPU boundary, and execution plan as audit artifact align with this direction — not as a programming language, but as a specification language for constraining LLM behavior. The durable insight is the pattern (boundary detection, audit trails), not the tool — which holds up if, as Karpathy predicts, large fractions of software get rewritten many times over.
- **Grok/X ideation session re: Medicaid dataset** — explored applying the DSL pattern to Medicaid data processing. Government/healthcare datasets are a natural fit: regulated, structured, high-volume, manual review burden. Python patterns and existing tools worked well for prototyping.

### Market Question: Cost Tier Gap
- **Is there a market between enterprise platforms and DIY?** Databricks, Snowflake charge enterprise prices. Zapier, Make are workflow tools but lack structured AI extraction with audit trails. The original target audience — analysts, ops teams, non-engineers — can't afford Databricks seats and can't assemble Python pipelines.
- The question is whether packaged, accessible AI workflows at a lower cost tier have enough pull to sustain a product, or whether the audience just uses ChatGPT manually and lives with the inconsistency.
- Medicaid/government data processing could be a concrete vertical to test this: high compliance requirements, budget-constrained teams, repetitive extraction tasks.
