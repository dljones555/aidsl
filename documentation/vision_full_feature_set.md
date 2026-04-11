**AI DSL — Feature Set & Differentiation**

---

**The core thesis no competitor has stated**

- Every other agent framework instruments the AI. AI DSL instruments the whole system — including the human, the compute, the cost, the context, and the proof that it all happened correctly
- Structure when English matters — the SQL moment for AI workflows — readable by domain experts, auditable by regulators, extensible by engineers
- One declarative source of truth that generates everything downstream: execution plan, fluent Python API, visual designer, four operational graphs, compliance artifacts, and cost telemetry — automatically

---

**The language and compiler**

- Declarative AI-first DSL with native concepts: `EXTRACT`, `CLASSIFY`, `DETECT`, `DRAFT`, `FLAG WHEN`, `VERIFY`, `HITL`, `ROUTE`, `UNTIL` — not general programming constructs repurposed for AI
- Domain-specific grammar system — pastoral care, healthcare, manufacturing, fintech each get purpose-built verb sets and policy defaults without changing the underlying compiler
- English-to-DSL generator — natural language spec produces a compliant `.ai` starter file; domain expert refines at the SQL level rather than authoring from scratch
- Two on-ramps, one compiler: `.ai` files for domain experts, fluent Python API for engineers — identical runtime guarantees from both surfaces
- Prompt and example files as first-class citizens — `.prompt` and `.examples` files versioned alongside the `.ai` file, referenced by name, diffable in git
- `UNTIL` goal-driven termination with `OR TIMEOUT` and `OR BUDGET` hard constraints — the pipeline runs until the work is done, not until a timer fires
- `VERIFY` as a first-class stage with a pluggable method registry — deterministic calculator, regulatory database lookup, citation retrieval, LEAN/Coq for formal proofs, LLM chain-of-thought — domain selects the right verifier
- Ad hoc code generation with supply chain constraints — when agents generate Python at runtime, the compiler enforces an allowed package allowlist, sandbox requirements, and tenant scope before execution
- `REGISTER SOURCE` with governance gates — non-technical users cannot connect production data sources without triggering a typed approval chain and full attribution logging
- Schema-validated typed output on every LLM call — field types, constrained enums, required fields enforced by the compiler, not by prompt instruction
- Deterministic rules never touch the LLM — `FLAG WHEN` runs as pure CPU code, identical every run, free, and auditable without stochastic variance

---

**The four operational graphs — the standard no one has defined**

- **Execution graph** — the declared plan: every stage, its compute class, its cost estimate, its dependencies, its schema, its prompt version, its HITL requirements — authored before runtime, versioned, the mental model made explicit
- **Compute graph** — the actual record: what ran, what it cost, how long it took, what prompt version was active, what context hash was in scope, what the inputs and outputs were at each node — plan versus actual at every step
- **Human graph** — the decision record: who decided, when, what was visible to them, what their competency score was at the moment of decision, how long they took, what they decided, what the downstream outcome was — not reconstructed after the fact, recorded in real time
- **Verification graph** — the evidence chain: which methods checked each output, what they found, how they combined into a certainty score, what sources were consulted, what flags were raised — per output, not per pipeline
- All four graphs share a run ID and pipeline ID — any graph is independently queryable for its audience without exposing the others
- Unplanned compute nodes — any agent behavior that runs outside the declared execution graph appears as an anomaly node in the compute graph with an immediate alert — dark code made visible in real time

---

**The human layer — what no agent framework has**

- HITL as a first-class typed primitive with defined decision sets — not a webhook, not a pause, a structured decision record with a required response from a typed option set
- Async HITL routing with competency enforcement — decisions route to qualified reviewers based on domain, minimum fitness score, current cognitive load, and availability — wrong person cannot approve a clinical decision regardless of system access
- Human competency profiles — passive signals from every decision: reversal rate, catch rate, decision latency, approval rate over time — cognitive drift surfaces as a metric before it becomes a risk
- `REQUIRE reviewer.fitness_score OVER threshold` enforced by the compiler — not a suggestion, a gate
- Mirror not surveillance — `PRIMARY_BENEFICIARY` is always the reviewer — competency signals serve personal development first, organizational access requires explicit consent
- SME routing with compensation primitives — `ROUTE TO sme_pool WHERE specialty MATCHES domain` with `COMPENSATE via micropayment PER decision` — human expertise as a schedulable resource in the execution graph
- Human cost as a first-class metric alongside GPU and CPU cost — decision latency, loaded labor rate, total human compute per pipeline run — the cost dimension every current tool ignores
- Cognitive fitness by design — HITL interfaces that require genuine engagement rather than rubber-stamp approval maintain the human judgment that makes the loop meaningful

---

**Context and provenance — the audit story**

- Context snapshot at every consequential moment — which prompt version, which data source version, which model config, which tool registry state was active when each output was produced — reconstructable months later
- Prompt versioning as a compiler-enforced requirement in regulated domains — not optional instrumentation, a policy gate
- Agent identity with birth record, scope declaration, and death record — the agent that no longer exists still has a complete lifecycle log
- Immutable decision record — what the AI extracted, what rules fired, what the verifier found, who reviewed it, what their qualifications were, what they decided, what happened downstream — one retrievable artifact per decision
- Full attribution chain — from English spec to DSL to compiled graph to runtime execution to human decision to verified output — every layer traceable to its author and its context
- Dark code detection — any runtime behavior outside the declared execution graph flags immediately — cross-tenant cache writes, unscoped output destinations, unlisted package imports — not forensic investigation after a breach, real-time enforcement

---

**The visual designer layer**

- Domain-adaptive rendering from the same schema — The Ledger for financial and administrative users, The Playbook for pastoral and coaching domains, The Floor for manufacturing and operations — same compiled pipeline, different visual grammar
- `RENDER AS [leddle | floor | playbook]` as a DSL verb — domain expert selects the visual surface appropriate to their audience
- Formula bar pattern — visual canvas is a view, DSL is always the canonical truth — bidirectional live sync
- Bespoke HITL surfaces generated from schema — the human decision card knows the person's name, their urgency, their channel, the verification result — not a generic approval modal
- Design tournament pattern — `RUN design_tournament UNTIL goal.approvals >= 2 OR TIMEOUT 5 days OR BUDGET $20` — iterative human-AI collaborative design with typed SME review and goal-driven termination

---

**The loop system — what no execution framework has unified**

- Eight distinct loop levels as a typed language hierarchy — from simple controlled iteration through goal-directed convergence, durable persistent execution, distributed parallel coordination, OODA meta-adaptation, safety-verified formal guarantees, and the full Fourier feedback architecture — expressed as composable DSL primitives, not hand-rolled Python
- `do_while`, `do_until`, and `meta_loop` as distinct first-class loop types with different termination semantics — reactive loops respond to environment state, goal-directed loops pursue objectives with safety caps, meta loops observe and adapt the loops beneath them — no current framework distinguishes these
- `METRICS` as inline eval — goal declarations with typed targets and delta thresholds embedded in the pipeline declaration alongside the workflow, versioned with it, evaluated at every execution node — not a separate eval framework bolted on afterward
- `DELTA_THRESHOLD` as a stagnation detector — the difference between not there yet and stuck, triggering diagnosis and adaptation rather than blind retry
- `DIAGNOSE [prompt, spec, context, tool]` on stagnation — targeted component diagnosis before remediation, not generic retry — the system identifies which layer is responsible for failure before deciding how to recover
- `ON_STAGNATION → META_LOOP refine_goals()` — the OODA learning loop above the execution loop — Observe telemetry, Orient by analyzing deltas, Decide on goal refinements, Act with updated parameters — self-adapting pipelines without human intervention
- `DEMONSTRATE → EVAL → SKILL` as a typed skill acquisition pipeline — train with a safety envelope, evaluate against a confidence metric with a threshold, promote to a reusable SKILL when the threshold is met — the skill is not deployed until the eval passes
- `MAX_LOOP_TURNS` as a compiler-enforced anti-runaway cap — not a suggestion to the model, a hard constraint that prevents infinite execution regardless of agent behavior
- LTL safety properties as compiler-verified invariants — `ALWAYS presence.kids IMPLIES robot_speed <= 0.3` is verified across all possible execution paths before deployment, not checked at runtime — the pipeline cannot be deployed if a safety invariant can be violated
- Behavioral Trees as the compositional tactical execution substrate — Sequence, Fallback, and Selector nodes with typed success and failure propagation, composing into arbitrarily complex task execution within the safety envelope declared by LTL
- Durable persistent loops — `UNTIL goal IS met OR TIMEOUT 5 days OR BUDGET $20` persists across process restarts, machine failures, and arbitrary delays — state is checkpointed at every meaningful transition and resumed exactly — built on Temporal-style durable execution under the hood, invisible to the domain expert
- The Fourier feedback architecture — sensor loop at milliseconds, task loop at seconds to minutes, session loop at minutes to hours, learning loop at hours to days, HITL loop at async human pace, telemetry loop at organizational frequency — each running at its natural rate, each producing signals that propagate to the appropriate level, the system behavior at any moment the superposition of all active loops
- Multi-agent coordination as language primitives — `SIGNAL TO PEERS`, `COORDINATE WITH ... VIA quorum_vote`, `PARALLEL MAX N` — typed inter-agent communication through declared channels, consensus mechanisms, and bounded parallelism without shared mutable state
- Named loop pattern classification — `loop_pattern ONE OF [ralph, alice, bob, ...]` in the action log — behavioral taxonomy that makes agent execution patterns diagnosable, not just observable — named patterns can be characterized, detected, and treated differently
- `MAX_PARALLEL_TASKS` as a typed concurrency constraint — bounded parallelism enforced by the compiler, not hoped for by the developer

---

**What the current field does and where it stops**

- LangGraph implements Levels 2-4 — stateful loops with persistent checkpointing within a session — no goal metrics, no stagnation detection, no meta loops, no LTL safety verification
- Temporal.io implements Level 4 correctly — durable persistent workflows that survive failures — but exposes infrastructure complexity to the engineer, has no AI-native primitives, and stops there
- DSPy implements a narrow version of Level 6 — prompt optimization in a meta loop against a metric — right idea, narrow scope, Python-only, no integration with execution loops
- Airflow and Prefect implement Level 5 DAG scheduling for data pipelines — no agent semantics, no goal-directed termination, no HITL primitives
- Ray implements Level 5 distributed execution — actor model, parallel task graphs — no AI-native loop types, no safety verification, no human loop
- BehaviorTree.CPP implements the Level 7 execution substrate — mature behavioral trees for robotics — no LTL safety compiler, no AI integration, no connection to the loops above it
- TLA+ and SPIN implement Level 7 safety verification — rigorous formal model checking — inaccessible to domain experts, not integrated with any agent runtime
- Nobody has assembled Levels 2 through 8 into a unified abstraction that is expressed as readable DSL, compiled to verified execution plans, backed by durable distributed infrastructure, and accessible to a domain expert who has never heard of Pi-calculus or model checking

---

**The one-sentence version**

Every framework gives you a loop. AI DSL gives you a loop system — typed, goal-directed, self-adapting, safety-verified, durable, distributed, and running at every frequency from milliseconds to weeks — expressed in ten lines that a domain expert can read and a compiler can verify before a single line of Python executes.

**The metrics and ROI layer**

- Three cost dimensions simultaneously — GPU spend, CPU spend (almost always zero for deterministic rules), and human labor cost — the cost the CFO actually cares about made visible
- Plan versus actual at every node — estimated cost versus actual cost per stage, deviation flagging, anomaly detection
- Work accomplished metrics alongside compute metrics — claims processed, decisions made, reversals, verification checks run, compliance coverage — not just token counts
- ROI dashboard as a byproduct — savings versus manual baseline, cost per unit of work, reversal rate versus industry average — produced automatically from the four graphs
- Compliance coverage as a metric — prompts versioned, context snapshotted, HITL competency enforced, audit trail complete — percentage, not a checkbox
- `ALERT WHEN unplanned_compute_nodes OVER 0` — the dark code monitor as a first-class operational alert
- Role-appropriate reporting — ops dashboard daily, CFO summary weekly, compliance officer monthly — same underlying graphs, different views

---

**The supply chain and extensibility layer**

- Policy skills as invisible compliance infrastructure — regulated domain constraints published as `SKILL.md` files that domain experts reference without knowing what they enforce
- `USE POLICY financial_reporting_standard` — one line that activates prompt versioning, context snapshotting, tenant isolation, and approval chains for the whole pipeline
- Two-layer authoring separation — governance architects write policy grammars once, domain experts write workflow logic at the SQL level with policies enforcing compliance underneath invisibly
- Neo4j integration path — `DEFINE` blocks compile to ontology schema, execution graph decisions log to knowledge graph, audit queries run as graph traversals rather than JSON file searches
- SKILL.md consumption from the 500,000-item marketplace — `USING PROMPT` references resolve to any compatible skill without custom integration
- MCP connector compatibility — Gmail, Planning Center, QuickBooks, GroupMe, any REST API with auth — `FROM` verb resolves through the MCP layer
- Pluggable LLM providers — any OpenAI-compatible endpoint, GitHub Models, Azure, local — swap providers without touching the `.ai` file

---

**What this is versus the current field**

| | AI DSL | LangChain | Zapier / n8n | Claude Projects / GPTs | Copilot / Cowork |
|---|---|---|---|---|---|
| Domain expert authoring | Yes | No | Partial | Partial | No |
| Typed schema enforcement | Compiler | Optional | No | No | No |
| Deterministic rules separate from LLM | Yes | No | Partial | No | No |
| HITL as typed primitive | Yes | Workaround | No | No | No |
| Human competency enforcement | Yes | No | No | No | No |
| Prompt versioning | Yes | Manual | No | No | No |
| Context snapshot at decision time | Yes | No | No | No | No |
| Four operational graphs | Yes | No | No | No | No |
| Dark code detection | Yes | No | No | No | No |
| Human cost as metric | Yes | No | No | No | No |
| Compliance coverage as metric | Yes | No | No | No | No |
| English-to-DSL generation | Yes | No | No | Partial | No |
| Visual domain-adaptive designer | Yes | No | Partial | No | No |
| Goal-driven termination | Yes | Manual | No | No | No |
| ROI dashboard from graph byproduct | Yes | No | No | No | No |

---

**The one-sentence version for the room**

When the auditor, the regulator, or the jury asks what your AI system did with their data last Tuesday — not what it was configured to do, not what it was supposed to do, but what it actually did, who approved it, what it cost, and whether the output was verified — AI DSL is the only architecture that can answer all four questions from artifacts it produced automatically while doing the work.