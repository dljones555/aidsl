# Lessons Learned — AI DSL Project (Week 1)

## PMF Reality

- **The extraction/classification layer is on the model treadmill.** GPT and Claude now do structured output natively. EXTRACT and CLASSIFY are competing with a single API parameter. Shelf life: 6-18 months before models subsume it.
- **Funded competitors own every adjacent space.** Reducto ($108M) for document extraction, Delve ($32M) for compliance automation, Instructor (free/open source) for structured output. A solo founder can't out-resource them.
- **The general-purpose DSL is high risk as a product.** "SQL for AI" sounds good in a pitch but nobody searches for it. Developer tools need massive adoption before they monetize, and the base rate for solo dev tools reaching sustainability is very low.
- **The viable solo path is vertical + consulting hybrid.** Pick one industry, solve one workflow end-to-end, charge $200-400/hr consulting while the product matures. $200K-$500K/yr is the realistic ceiling. Timeline: 2-3 years to sustainability.
- **Talk to buyers before building more.** The pattern of build-for-weeks-then-discover-it's-crowded is solved by 5 conversations with people who have budget and a manual workflow they hate.

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
