# Strategy Sheet — An Open AI Execution Stack

*A "general-audience Palantir": thin open primitives above the models, authored by domain experts, governed by humans.*
**Status:** working strategy · **Companion to:** `OSS_AI_Kernel_DSL_UI_RFC.md` · **Date:** May 2026

---

## The spine — three compute classes

Everything below serves one idea: **AI knowledge work is the allocation of work across three compute classes — deterministic, non-deterministic, and human — each with its own trust class, cost curve, and role. The hard problem is doing that allocation honestly, making it legible, and keeping all three healthy.**

| Class | What it does | Trust | Cost | Notes |
|---|---|---|---|---|
| **Deterministic** (CPU) | code, math, queries, transactions, conditionals | high — reproducible, self-auditing | low | try this first; the more work lands here, the cheaper and more auditable the system |
| **Non-deterministic** (the model) | judgment, extraction, classification, drafting, summarization | conditional — **not self-certifying** | per-token, per-tier | bounded-error; "citations" are themselves model output, not ground truth |
| **Human** | (1) source of spec/knowledge · (2) authority — the binding decision · (3) reviewer — the calibration check on the model · (4) the leg that must stay competent to do 1–3 | authoritative — legally distinct from what the other two produce | the scarcest and most expensive | **the only class that decays if you underuse it** |

Three consequences that shape the whole design:

- **The boundary holds all the way to the goal evaluator.** "Done" is decided by the right class: deterministic completion criteria where expressible, model-judged only as a *labeled* fallback, human for the authoritative gates. Coding tools today run deterministic everywhere and then quietly route the *acceptance gate* to an LLM judge — that's a triad violation, and it's the one that matters most.
- **Review is dual-purpose, not overhead.** When the human leg reviews the model leg's output it is simultaneously the quality gate, the calibration signal (the only way `confidence ≥ 0.90` comes to mean anything), and the exercise that keeps the human leg sharp. Three jobs, one act — so HITL can't be designed as "the slow annoying path."
- **Atrophy is a routing constraint.** Route 100% of judgment to the model and let humans rubber-stamp, and the human leg's competence decays — hollowing the authority and review legs and collapsing the governance story quietly. So the router carries a *competence-preservation floor*: deliberately send some cases to humans even when the model could handle them, the way you'd inject chaos to keep an on-call team sharp. "Cognitive fitness as a primitive" means exactly this — a constraint on the scheduler, not a wellness slogan.

The primitives, the four graphs, the DSL, and the UIs below all hang off this: they exist to **route** work across the triad, **account** for all three, and **keep all three healthy**. (The *count* of primitives isn't sacred — the set is what keeps showing up in real systems, not a magic number.)

## 1 · Why open source AI, why now

- **The frameworks churn won't survive model progress.** LangChain, orchestration platforms, vendor agent APIs are jQuery-before-React / Unix-flavors-before-Linux: ubiquitous, useful, temporary. They encode current model quirks; better models dissolve them.
- **The primitives already converged — nobody wrote the spec.** Claude Code, Codex CLI, Cursor, Copilot agent mode, Aider, Grok independently landed on the same shape: agent loop, filesystem-as-state, shell exec, MCP, resumable/forkable sessions, sub-agents, permission tiers, a project config file, hooks, memory, skills. Fragmentation is everyone shipping a different *spelling* of the same syscalls.
- **MCP is the one solved layer** — the "device driver" interface. Everything above it (process model, context, provenance, authority, HITL) is still vendor-private.
- **Open won the last three platform shifts** (Linux, SQL, the web) — durable because open, not because fastest. US/China competitiveness arguments point the same way.
- **Coding ate all the oxygen.** Tooling investment is coding-shaped because that's where the builders and the tight feedback loops are. A standard runtime is exactly what insurance/health/legal ops *can't build themselves and won't get from a coding-first vendor*.

## 2 · The POSIX comparison (the mental model)

| POSIX | AI-stack equivalent | Standardized today? |
|---|---|---|
| process / `fork()` | session, sub-agent, longview run | no |
| `exec()` | tool call / shell exec | de-facto (JSON-schema tools) |
| VFS — "everything is a file" | MCP resources + tools — *"everything is a resource with provenance"* | **yes — MCP** |
| signals | interrupt, preempt, pause-for-human, hooks | no |
| scheduler / `init` / systemd | the loop runner; background & cron tasks; managed-agent runtime | no |
| `ulimit` / cgroups | token / `$` / time / turn budgets | no |
| uid·gid · `chmod` · sudo | authority tiers, permission modes, approval gates | no |
| `syslog` | provenance → JSONL transcript + OTel | partial |
| `/etc`, `.profile` | `CLAUDE.md` / `AGENTS.md` / `.cursorrules` / settings.json | no — the `/etc` wars |

**Framing correction:** the model is the *non-deterministic* part, so it is a **device, not the kernel**. The kernel is the deterministic supervisor that schedules calls to the model the way an OS schedules a GPU — and that's exactly why provenance and authority belong *in* the kernel: you don't trust the device to self-report. We standardize the *interface*, version it, keep it thin — a ratification of what converged, not a clean-room redesign. (POSIX also ossified 1988 mistakes for 40 years; thin spec, plural implementations is the guardrail.)

## 3 · The primitives (the un-standardized syscalls)

*The set, not the count — these are what keep showing up; add or merge as real systems teach us. They exist to route work across the triad and account for all three legs.*

- **Process manager / scheduler** — admits runs to a queue; schedules agents + sub-agents + longview sessions; delivers signals; brokers human interaction; **routes each node to a compute class** (deterministic / model / human) *subject to a competence-preservation floor* (the atrophy constraint — see the spine). **HITL pause = a blocking syscall** (run parks → queue item → signed decision unparks). **Budgets are first-class resource limits**; exceeding one *preempts*, never crashes (`SIGXCPU`-style → escalate).
- **Goal** *(a predicate over a typed state vector, not "a prompt")* — evaluated **deterministic-first → model-judged → human-authority** (a triad boundary — the acceptance gate belongs to the right class); LLM-as-judge is the labeled fallback. A small **family by scope/timescale**: `RunGoal` (completion ∧ within-budget — knowable now) · `OperationalGoal` (rolling-window quality/rework/override — the meta-loop's) · `BusinessGoal` (lagging, *attributed*, **ingested from external systems** — NPS, new customers, ROAS, cost-to-serve). Business goals ship with **constraints (the box)** + a **human-authority gate on budget moves** + a **measurement method with its own trust class**. *The agent never edits its own goal definition — it proposes; a person signs.*
- **Loop** — `work` (operates on domain state) and `meta` (operates on the work loop's metrics). Same primitive, different observation target. Stagnation policy: diagnose · escalate · meta-loop · fail.
- **Session** — fork · pause · resume · compact, full serialized state, append-only JSONL history.
- **Provenance** — on every artifact, part of the type: producer · time · sources · confidence · **cost · compute class** · authority level.
- **Authority** — legal/epistemic weight; checked by the runtime on every decision that requires it; mismatch = compile-time error where possible, runtime failure otherwise.

> Application-level, *not* kernel: retrieval strategy, prompt templates, agent topology, specific tool integrations, memory, skills.

## 3.5 · The execution model — durable typed pipes for agentic work

*The kernel-y picture, concretely. **Not** process-per-step (Unix pipes are cheap because text is cheap; agent state isn't) — **process-per-seam**, passing **handles** to context instead of bytes.*

- **Eight services, narrow interfaces:** supervisor/scheduler · **model gateway** (one shared prompt cache + cost ledger + vendor-swap point) · context manager (the tiered store + `pin`/`evict`/`rehydrate`) · tool runners (typed I/O, MCP-style) · **HITL broker** (queues, signed-decision capture — the blocking-syscall implementation) · memory service (ontology + RSI behind a typed API) · provenance sink (writes the durable log; the four graphs are views over it) · skill/command registry (signed, versioned). *MCP is the only one of these the industry already cut as a separate process — proof the decomposition works.*
- **Pipes with shape, not pipes of bytes.** Every inter-component message carries `{payload, schema_ref, provenance, cost, compute_class}` — composition is **statically checkable** (you can't feed a `Claim` into a stage expecting a `PolicyRecord`); provenance is *carried alongside the payload*, not reconstructed after. Prior art to steal from: PowerShell/nushell (typed pipelines), Arrow/Flight (zero-copy typed streams), gRPC + protobuf/Cap'n Proto (schema evolution), Erlang/OTP (supervision trees), Temporal/Restate/Inngest/DBOS (durable execution), Beam/Dagster/Pachyderm (typed dataflow + lineage). None has the *agentic* layer; the combination is the empty cell.
- **Agentic commands ≠ Unix commands** — five properties Unix verbs don't carry: **durable** (state checkpoints to the log; workers are fungible) · **longview** (a command can park for hours/days without burning a slot) · **typed I/O with shape contracts** (plus `(confidence, evidence)` return on non-det) · **compute-class tagged** (`deterministic | model | human` declared, not inferred) · **provenance-emitting** (the envelope is the payload's lineage; composition preserves it automatically).
- **The four graphs are views over the substrate, not bolt-ons.** Plan graph = the pipeline DAG · compute graph = the durable log · decision graph = log entries with authority+evidence stamps · verification graph = log entries showing grounding method per claim. *This is what makes regulability mechanical instead of aspirational.*
- **The scheduler is where the triad becomes operational.** It routes each node to a compute class (T0 det → T1 local model → T2 frontier → T3 human), enforces budgets as `ulimit`-style **preemption** (not crash), parks/wakes for HITL, applies the **competence-preservation floor** (the atrophy constraint — see the spine), and reconciles plan-vs-actual.
- **Ship in-process by default, decompose by deployment choice.** All eight services run in one binary in *embedded mode* — the **interfaces are the architecture, not the topology**. Split them across processes when scale demands. (Dodges the "8 microservices is harder than 1 binary" failure mode while preserving the design.)
- **Honest costs:** latency at boundaries (fine for workflow agents at seconds-per-step; wrong for coding-IDE agents at sub-second feel — a *feature* for our wedge, not a bug); the supervisor↔context-manager seam must use **handle semantics** (don't ship 50k tokens per message); schema evolution is real ops work, not free.

> Reframed in industry terms: the project is **a durable-execution engine for typed agentic workflows with first-class triad routing and provenance-as-payload**. Temporal-class, Beam-class, and LangGraph-class systems each cover *some* of that cell; none cover the combination. The monolithic agent harnesses (Claude Code, Cowork, Cursor, Codex) explicitly can't, by construction — which is also why their security model is "trust the whole process."

## 4 · Context — tiered storage, not a black-box window

- Three tiers: **hot** (in-window) · **warm** (retrievable verbatim — files, transcript) · **cold** (compacted, lossy). Not demand-paging — you can't re-fault a summary back to the original for free.
- **Context tools** as explicit, *accounted* ops: `pin` / `evict` / `rehydrate` — each with visible cost, each logged to the compute graph.
- A **context budget** (an RSS limit) + a **pluggable eviction policy** — the standard replaces the invisible auto-compaction every vendor does privately.
- **Tracks token I/O, model calls, `$`** continuously — context pressure and spend are observable, not inferred.

## 5 · Memory & RSI — two layers, kept apart on purpose

- **Ontology** — typed, schema-constrained, *closed-ish*. Postgres + pgvector + Apache AGE (default; analysts know SQL) or Neo4j (when multi-hop traversal dominates); DSL `MATCH` compiles to either. The target of **deterministic inference** (traversal, joins, constraint propagation). **Write path:** LLM extract → pydantic (shape) → provenance stamp → `GROUND` against source → promote. **Two-tier:** `candidate` (model-extracted, advisory) vs `asserted` (grounded/human-confirmed); deterministic inference runs over `asserted` only. **Ontology is a projection of systems of record, never a fork — ingest, don't fork.**
- **RSI / experiential layer** — markdown/wiki accumulation (Karpathy-style lessons; Anthropic's memory/"dream" demos). Open-ended, **advisory — never decides**. Append-only, every entry stamped with the run(s) that produced it + a staleness signal. **Garbage-collected by the meta-loop** (it reconciles contradictions, proposes pruning diffs for human review).
- **Tiered inference**, supervisor routes per-node on `(confidence needed, cost budget, authority required)`: **T0** deterministic over the ontology (no model) → **T1** local/cheap model + retrieval + pydantic (classify, extract, summarize, draft, flag) → **T2** frontier model (hard/novel reasoning) → **T3** human authority. The execution-plan graph colors each node by tier. Local models earn their keep on high-volume bounded ops + on-prem data; the win is the *routing*, not the model.

## 6 · The four graphs (the kernel's accounting structures)

1. **Execution-plan graph** — `EXPLAIN` for a run, *static, pre-run*: ≈N model calls / ≈M tool calls, est. cost range, critical path, "swap opus→haiku here saves 60%", which nodes need web/tool access. *Audience: the author.* (Claude Code's plugin/cost preview is the embryo.)
2. **Compute graph** — what actually happened: plan-vs-actual, per-node tokens/latency/cost/retries. *Audience: ops.* (OTel + JSONL, rendered as the same graph so you can diff prediction vs reality.)
3. **Decision graph** — provenance of every human/agent decision: who · under what authority · on what evidence · reversible? *Audience: the auditor / the court.* This is the artifact a regulator subpoenas.
4. **Verification graph** — which claims were grounded against which method, and the **trust class** of each (web search ≠ a Lean proof ≠ a SQL query ≠ a calculator ≠ a human attestation). *Audience: the reviewer — "how do we know this is true."*

> Graphs 3 & 4 are what make the space **regulable**: "AI in a regulated decision must emit a conformant decision graph" becomes a writable rule the moment the format is standard.

## 7 · The DSL — analyst-readable, not Python

- **Reads at the SQL/Excel level**; writable by the same person (with LLM assist). **Declarative, diffable, version-controlled.** Domain experts author the substrate — *if it needs a Python developer, it failed.* (TAM: tens of millions of SQL/Excel-literate operators.)
- **Not Python** — Python fails analyst-readability *and* you can't statically verify a Turing-complete language (no `EXPLAIN` graph for arbitrary code).
- **Verbs that recur in knowledge work like `grep` recurs in text** — bounded, typed-output, `(confidence, evidence)`-returning: `EXTRACT` · `CLASSIFY` · `SUMMARIZE` · `DRAFT` · `GROUND` · `MATCH` (→ Cypher/SQL) · `COMPUTE` (deterministic) · `DECIDE` (records provenance) · `WHEN`/`FLAG` (deterministic — never runs in the model) · `SEND`/`RECORD`/`UPDATE`/`ATTACH` (transactional, logged). Prompts and examples are versioned data; signed where it matters.
- **Compiles through MLIR-style dialects** — surface syntax → typed execution graph (every node carries its provenance contract) → target code (orchestration / Cypher / SQL / prompt templates). Each lowering has a **verifier**: missing `GROUND` evidence, missing authority on a HITL block, stage type mismatches — caught at compile time.
- **Wraps best-in-class tools**, doesn't reinvent: docling / langextract for parsing, pydantic for validation, the strongest open eval framework for `EVAL`.

## 8 · Knowledge engineering — the spec layer (why FDEs exist)

- **Spec quality is the new bottleneck.** Agents underperform because the spec is thin, not because the model is weak. The hard, human, high-leverage work moved from writing code to *eliciting and formalizing tacit domain knowledge* — which is why FDEs and "software-factory" shops (Palantir's FDE model, 8090.ai, et al.) exist. Better models raise the leverage on that role; they don't remove it. *The OS can't automate tacit-knowledge extraction — it supports it.*
- **Specs are source, not documentation.** Spec + ontology + DSL workflows + prompts + canonical examples + evals all live in **one versioned repo** — diffable, reviewable, branchable ("try this policy change on a branch"). Markdown hierarchy (`STRUCTURE`), Karpathy-append style — *executable and incremental*, refined against the four graphs, not a 200-page upfront document.
- **Managed prompts = signed, versioned units — not strings.** A prompt is `{template, contract (inputs/outputs/required citations), test set (canonical examples it must pass), version, signature}`. Git gives versioning + blame + signed commits/tags; "managed" adds the contract + test set + a provenance stamp (prompt id + hash) in every artifact it produces — exactly what the verification graph and the signed-resources security requirement consume. Signing buys *integrity + attribution* ("this is what was approved, unmodified"), like signed releases — not correctness; don't oversell it.
- **The OS ships the kit.** Project scaffolding (`STRUCTURE build`), per-domain starter templates (claims processing, prior-auth, contract review, KYC…), and **canonical examples** — golden input→output pairs that double as documentation *and* eval fixtures. The Rails-generators / cookiecutter move: encode the conventions, make the good path the easy path. Skip it and every deployment reinvents structure — the standardization benefit evaporates.
- **The spec is in the improvement loop.** High override/rework on a stage is usually an *underspecified spec*, not a model failure — the meta-loop surfaces it and routes a **spec-revision task** to a human (FDE / ops lead), failing cases attached. The spec evolves with the deployment.
- **This is the deployment-specialist's kit — and what makes the labor portable.** "Marketplace of deployment specialists" really means a marketplace of *knowledge engineers*: elicitation + formalization + iteration. The kit — spec format, scaffolding, templates, example library, prompt discipline, eval harness, the ontology as the place to put what you extract — is what turns "I deploy agent workflows" into a portable trade, the way "I know SQL" is.

## 9 · New UIs — beyond chat, built for agent + HITL work

- **Not a chatbot, not Zapier/n8n, not an AI layer bolted onto SaaS.** Chat-as-primary-surface and thinking animations are the wrong center of gravity; visual flow-builders aren't diffable/versionable and are shallow on AI primitives.
- **Generated from the DSL** — entities → CRUD views; HITL blocks → review inboxes with declared `SHOW` fields + `REQUIRE` options as buttons; policies/metrics → dashboards; the four graphs → their own visualizers. Custom views described in English become versioned view-specs. **Text is canonical; the visual tool is a projection that round-trips back to text** (Terraform + plan-viz, dbt + DAG view — not Scratch).
- **Three modes:** **the floor** (operator queues — SLA-sorted, keyboard-navigable, Linear-adjacent) · **the desk** (ops-lead — metrics, improvement-proposal review, DSL version history) · **the office** (authoring — DSL editor, LLM-assisted generation, compile/validate output).
- **HITL is the underbuilt layer** — coding agents barely need it (read the diff); knowledge work *is* HITL. Work queues, review inboxes, decision workspaces, escalation paths, SLA timers — first-class. **"Agent-error-friendly"** = when unsure, the agent emits a *well-formed review task with evidence attached* — never a hallucinated answer, never a silent block, never a crash.

## 10 · Runtime, security, and the people

- **Three backends, one kernel:** Claude Managed Agents (hosted, production-ready today) · **bare-metal reference** (cron + Postgres + systemd + object storage — the portability guarantee) · a third-vendor adapter (proves no lock-in). Same compiled IR runs on all three.
- **Observability:** every primitive call is an event → JSONL (per-session, full text, replay/debug) **and** OTel (aggregated, queryable) simultaneously; citations/evidence carried in both.
- **Security as a first concern, not a layer** — OAuth + MCP security; **signed, versioned prompts/resources + context hashes** in provenance; needs first-class security engineers from day one.
- **Cognitive fitness = a routing constraint, not a slogan** — the human leg decays if underused, which hollows the authority and review legs. The scheduler carries a *competence-preservation floor*: a fraction of cases routed to humans even when the model could handle them, plus tracking (without overreach) of human cognitive load, role redefinition, and the skills/cost required to review and operate AI work over time. HITL competency is a maintained capability — measured and budgeted, not assumed.
- **Go-to-market = a marketplace of deployment specialists** — mid-career operators with domain + technical fluency who implement workflows on the platform at mid-market prices. A standard substrate makes the skill *portable* — that's the labor thesis, and it only works if the layer is open.

---

## What we're going for, in one line each

- **The triad:** route work across deterministic / non-deterministic / human compute honestly, make the routing legible, keep all three healthy — every line below serves this.
- **Kernel:** thin, stable, backend-agnostic — survives model progress instead of dissolving with it.
- **DSL:** the declarative substrate, authored by domain experts, diffable and verifiable.
- **Knowledge engineering:** the spec is the product — scaffolding, templates, canonical examples, signed managed prompts; the kit that makes the deployment specialist's craft portable.
- **Graphs:** plan it, measure it, attribute the decision, prove the truth — the four accounting structures that make AI work auditable and regulable.
- **UI:** the work is the protagonist — queues, reviews, decision workspaces — the AI is visible in its contributions, not the show.
- **Open:** because the last three platform shifts that ran every industry for decades won by being open — and this one should too.

*Draft for discussion — nothing final until a reference implementation validates or invalidates it. Seeking: technical review, kernel/compiler collaborators, pilot partners in mid-market regulated domains (insurance, health, legal ops).*
