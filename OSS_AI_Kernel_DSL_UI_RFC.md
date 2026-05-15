# RFC: An Open Execution Stack for Human-AI Knowledge Work

*Kernel · DSL · Four Graphs · Generated UIs · Durable Typed Pipes*

**Status:** Revised draft for discussion — Rev 2

**Author:** David L. Jones — three decades in tech as developer / analyst / consultant / employee across startups, midsize growth, and Fortune 500. Like many, I have been digging into AI while having the fortune of time to observe the best of the AI/ML industry on X and elsewhere, experiment, learn, and research while off full-time work for over two years.

**Date:** May 2026 (revision of April 2026 draft, incorporating discussion through May 14)

**Companions:** [`Strategy_Sheet_Open_AI_Stack.md`](./Strategy_Sheet_Open_AI_Stack.md) (2-page strategy) · [`Project_EXPLAIN_MVP.md`](./Project_EXPLAIN_MVP.md) (the first concrete artifact)

**Intended audience:** Systems engineers, compiler authors, domain operations leaders, security and audit practitioners, and anyone who has watched the current AI framework churn with skepticism.

**Theses.** Are we at an inflection point in the AI industry where we need an open-source layer above the models that looks like an AI kernel or OS? How do we bring non-developer workers into the human-AI co-work, authoring, and UI design process for the new phase of agents and regulated work — accounting for human, GPU, and CPU components, costs, and knowledge engineering in smart ways? Is it time for open-source AI stack primitives that look like Linux, SQL, and novel generated UIs that fit the domains of the workers? As the AI labor transition emerges, how do we respectfully maintain human cognitive fitness and the skills and knowledge required to review and operate AI and the work it augments and replaces? Many of the venerable foundations of US technology — Linux, SQL, the web — have reliably run disparate industries for decades because they were *open*; this next platform shift deserves the same treatment.

---

## The spine — three compute classes

Everything below serves one idea: **AI knowledge work is the allocation of work across three compute classes — deterministic, non-deterministic, and human — each with its own trust class, cost curve, and role. The hard problem is doing that allocation honestly, making it legible, and keeping all three healthy.**

| Class | What it does | Trust | Cost | Notes |
|---|---|---|---|---|
| **Deterministic** (CPU) | code, math, queries, transactions, conditionals | high — reproducible, self-auditing | low | try this first; the more work lands here, the cheaper and more auditable the system |
| **Non-deterministic** (the model) | judgment, extraction, classification, drafting, summarization | conditional — **not self-certifying** | per-token, per-tier | bounded-error; "citations" are themselves model output, not ground truth |
| **Human** | (1) source of spec/knowledge · (2) authority — the binding decision · (3) reviewer — the calibration check on the model · (4) the leg that must stay competent to do 1–3 | authoritative — legally distinct from what the other two produce | the scarcest and most expensive | **the only class that decays if you underuse it** |

Three consequences shape the whole design:

1. **The boundary holds all the way to the goal evaluator.** "Done" is decided by the right class: deterministic completion criteria where expressible, model-judged only as a *labeled* fallback, human for the authoritative gates. Coding tools today run deterministic everywhere and then quietly route the *acceptance gate* to an LLM judge — that's a triad violation, and it's the one that matters most.
2. **Review is dual-purpose, not overhead.** When the human leg reviews the model leg's output it is simultaneously the quality gate, the calibration signal (the only way `confidence ≥ 0.90` comes to mean anything), and the exercise that keeps the human leg sharp. Three jobs, one act — HITL is not "the slow annoying path."
3. **Atrophy is a routing constraint.** Route 100% of judgment to the model and let humans rubber-stamp, and the human leg's competence decays — hollowing the authority and review legs and collapsing the governance story quietly. So the router carries a *competence-preservation floor*: deliberately send some cases to humans even when the model could handle them. "Cognitive fitness as a primitive" means exactly this — a constraint on the scheduler, not a wellness slogan.

The primitives, the four graphs, the DSL, the runtime, and the UIs below all hang off this: they exist to **route** work across the triad, **account** for all three, and **keep all three healthy**.

---

## Summary

This document proposes a thin, stable execution stack and a declarative DSL for AI-augmented knowledge work, organized around the triad above. The thesis is that the current generation of agent frameworks — LangChain, vendor-specific agent APIs, the various orchestration platforms — are comparable to jQuery before React, or Unix flavors before Linux: useful, ubiquitous, and temporary. The primitives they expose are too coupled to current model behavior and will be subsumed as model capabilities improve.

What is missing is the equivalent of the primitives that survived the last paradigm shift: a thin, composable substrate with clean separation between deterministic operations, non-deterministic model calls, and human authority. Something that domain experts — not engineers — can read and reason about. Something whose value compounds as models improve rather than dissolves with each release.

Six parts:

1. **A small set of kernel primitives** — process manager/scheduler, goals (a small family), loops, sessions, provenance, authority. *The set, not the count* — these are what keep showing up; add or merge as real systems teach us. Backend-agnostic.
2. **An execution model** — a durable-execution engine of typed agentic pipes (process-per-seam, not process-per-step), with shape-contracted messages carrying provenance as payload envelope. The four graphs become views over the durable log, not bolt-ons.
3. **A DSL** that reads at the SQL/Excel-analyst level, compiles to a typed IR, and targets the kernel. Authored by domain experts (with LLM assistance), not engineers. Wraps best-in-class tools (docling/langextract, pydantic, the strongest open eval framework).
4. **A runtime abstraction** that binds the primitives to existing platforms (Claude Managed Agents, the Anthropic Agent SDK, OpenAI Agents) or to a bare-metal implementation using Linux, Postgres, and object storage. Embedded mode → distributed mode is a deployment choice, not a rewrite.
5. **A generated UI layer** derived from DSL declarations — operational interfaces (queues, dashboards, HITL decision workspaces) that domain users actually work in. Prior art: Ruby on Rails generators, Terraform plan visualizers, dbt's DAG view.
6. **Provenance, decision, verification, and execution-plan graphs** — the kernel's accounting structures — emitted to JSONL and OTel.

This RFC is seeking technical review, collaborators for the kernel and compiler, and pilot partners — initially via a **wedge-zero MVP** that demonstrates the triad and provenance in a single CLI tool (see `Project_EXPLAIN_MVP.md`).

Anthropic's Claude Code, Codex, Cursor, Copilot agent mode, and Aider have, independently, converged on roughly the same primitive set — agent loop, filesystem-as-state, shell exec, MCP, resumable/forkable sessions, sub-agents, permission tiers, project config, hooks, memory, skills. **Fragmentation is everyone shipping a different *spelling* of the same syscalls.** MCP is the one solved layer above the model. Everything else above the model is still vendor-private.

This is a specification under discussion. The first reference artifact (the `explain` MVP) is what validates or invalidates it.

---

## Why now, why this

### The paradigm problem

The current AI application stack is fragmented along lines that will not survive the next 18–24 months of model progress.

- **Orchestration frameworks** that encode specific agent topologies. Better models dissolve them.
- **Retrieval pipelines** with elaborate chunking and reranking. Long-context and native search are eating them.
- **Prompt-engineering frameworks** built around prompt fragility. Models are becoming robust enough that elaborate chains are anti-patterns.
- **Vendor-specific agent APIs** that encode one company's bet on what agents are. OpenAI's Assistants API was abandoned; others will follow.
- **Thick wrapper products** that bolt an AI layer onto existing SaaS. These look good in demos and struggle in production because they cannot surface the AI's work in ways operators can govern.

Enduring software like Linux, React, and SQL won not because it was fastest but because it identified durable primitives — POSIX boundaries, components as functions, a simple grammar that extended the user base beyond engineers. The AI space has not yet found its equivalents, but the shape of them is becoming visible. And in heterogeneous compute + regulated environments, *structure beyond English* is needed for reproducible results and provenance for decisioning records and audits.

### The convergence already happened — we just have not written the spec

Claude Code, Codex CLI, Cursor, Copilot agent mode, Aider, and Grok independently landed on nearly the same shape. The "AI POSIX" surface is already de facto:

| POSIX | AI-stack equivalent | Standardized today? |
|---|---|---|
| process / `fork()` | session, sub-agent, longview run | no |
| `exec()` | tool call / shell exec | de-facto (JSON-schema tools) |
| VFS — "everything is a file" | MCP resources + tools — *"everything is a resource with provenance"* | **yes — MCP** |
| signals | interrupt, preempt, pause-for-human, hooks | no |
| scheduler / `init` / systemd | the loop runner; cron/background tasks; managed-agent runtime | no |
| `ulimit` / cgroups | token / `$` / time / turn budgets | no |
| uid·gid · `chmod` · sudo | authority tiers, permission modes, approval gates | no |
| `syslog` | provenance → JSONL transcript + OTel | partial |
| `/etc`, `.profile` | `CLAUDE.md` / `AGENTS.md` / `.cursorrules` / settings.json | no — the `/etc` wars |

**Framing correction.** The model is the *non-deterministic* part, so it is a **device, not the kernel**. The kernel is the deterministic supervisor that schedules calls to the model the way an OS schedules calls to a GPU — and that is exactly why provenance and authority belong *in* the kernel: you do not trust the device to self-report. We standardize the *interface*, version it, keep it thin — a ratification of what converged, not a clean-room redesign. (POSIX also ossified some 1988 mistakes for 40 years; thin spec, plural implementations is the guardrail.)

**Linux/macOS, not POSIX.** The historical pattern that actually works is *codification after convergence through use* — one implementation gets good enough that ratifying it as the standard becomes obvious. The play is to **be the implementation that wins**, not to write a committee spec first. The "spec" is documentation after the fact.

### The durable primitives, identified

After examining what Claude Code, Claude Managed Agents, and production agent deployments actually do well, the primitives that appear consistently — *regardless of model capability* — are:

- **Goals with explicit completion conditions** — typed objectives with deterministic, model-judged, or human-authority evaluation.
- **Loops with stagnation detection** — the work loop (pursuing a goal) and the meta-loop (observing the work loop's performance).
- **Sessions** that fork, pause, resume, and compact, with full serialized state.
- **Provenance on every artifact** — who or what produced this, when, from what source, at what cost, in what compute class, with what authority.
- **Authority as a first-class concern** — human approval is not a tool call; it is an authoritative and binding primitive that models cannot replace.
- **A process manager / scheduler** — admits runs, schedules sub-agents, brokers human interaction, enforces budgets as preemption, and applies the competence-preservation floor.

Everything else — retrieval strategies, prompt structures, agent topologies, specific tool integrations, memory layouts, skill packaging — is application-level and will change. The list above is substrate. The *count* is not sacred (the prior draft fetishized "five"); the *set* is what keeps showing up.

### The human-first thesis

Most AI infrastructure assumes the human is a fallback — something to route to when the AI fails. This gets the architecture wrong. In regulated domains the human is not a fallback; the human is the *authority* whose approval is the completion criterion. "The manager approved" and "the model approved" have categorically different legal and epistemic status. Building this distinction into the kernel rather than into application code is what lets the same primitives serve healthcare, legal, insurance, and financial operations without being rebuilt for each.

The corollary: the people authoring agent workflows should be domain experts, not engineers. An analyst who reads SQL and writes Excel formulas should be able to read a workflow file and see what happens when a claim arrives, who reviews it, and how the improvement loop runs. If authoring requires a Python developer, the thing has failed. There is a TAM of tens of millions in the US with SQL- or Excel-level literacy — operators who can work with business concepts in a mental model they understand. Realistically the first workflows are LLM-generated from English and refined by analysts; that is fine, but the artifact still has to be **readable, diffable, and runnable** by the analyst — not "Python this person can't touch."

---

## The primitives (the set, not the count)

The primitives below are what keep showing up in production agent systems. Each is minimal, composable, and backend-agnostic.

**Process manager / scheduler.** Admits runs to a queue; schedules agents and sub-agents and longview sessions; delivers signals; brokers human interaction; **routes each node to a compute class** (`deterministic | model | human`) *subject to a competence-preservation floor* (the atrophy constraint). **HITL pause = a blocking syscall** (run parks → queue item → signed decision unparks). **Budgets are first-class resource limits**; exceeding one *preempts*, never crashes (`SIGXCPU`-style → escalate).

**Goal.** A *predicate over a typed state vector*, not "a prompt." Evaluated **deterministic-first → model-judged → human-authority** (a triad boundary — the acceptance gate belongs to the right class); LLM-as-judge is a labeled fallback, not the default. A small **family by scope/timescale**:

- `RunGoal` — completion ∧ within-budget; knowable now.
- `OperationalGoal` — a rolling-window predicate over quality, rework, override rate; the meta-loop's goal, not the work loop's.
- `BusinessGoal` — lagging, *attributed*, **ingested from external systems** (NPS, new customers, ROAS, cost-to-serve). Business goals ship with **constraints (the box)** + a **human-authority gate on budget moves** + a **measurement method with its own trust class** on the verification graph. *The agent never edits its own goal definition — it proposes; a person signs.*

**Loop.** `work` (operates on domain state) and `meta` (operates on the work loop's metrics). Same primitive, different observation target. Stagnation policy: diagnose · escalate · meta-loop · fail.

**Session.** Fork · pause · resume · compact. Full serialized state, append-only JSONL history. Mirrors what Claude Code and CMA implement today — formalized as first-class operations rather than vendor features.

**Provenance.** On every artifact, *part of the type*: producer · time · sources · confidence · **cost · compute class** · authority level. Not optional, not instrumentation. An extracted field, a model decision, a human approval, a Cypher query result — all carry their origin, evidence, confidence, cost, compute class, and authority.

**Authority.** Legal and epistemic weight an actor has to decide something. A claims analyst has authority to approve up to $2,000. A manager has authority above that. A model has *no* authority in the legal sense but contributes evidence to decisions humans make. Checked by the runtime on every decision that requires it; mismatch = compile-time error where possible, runtime failure otherwise.

### What the kernel deliberately does not specify

- Which LLM to call. Models are pluggable, behind the model gateway.
- How retrieval works. Tool calls return typed results; the kernel does not care whether the backend is a vector store, a graph database, or a keyword search.
- Which orchestration topology. Single-agent is the default; sub-agents are a runtime detail, not a primitive.
- Specific prompt templates. Prompts are signed, versioned data — see *Knowledge engineering*, below.
- UI rendering. The kernel emits events; the UI layer subscribes.

### Discipline on additions

Every additional primitive is a commitment to a worldview that might not survive. Provenance is a bet that auditability will always matter — a safe bet. Authority is a bet that human decisions will remain legally distinct — also safe. Goals and loops are bets about the shape of iterative work — confirmed by two-plus years of production agent use. The process manager and budgets are bets that resource-bounded execution is universal — safe. Everything else is application-level. Skills, memory, knowledge bases, multi-agent coordination — built on top, none in the kernel. If they turn out to be wrong, the kernel survives. If they turn out to be right, they are straightforward to add.

---

## The four graphs (the kernel's accounting structures)

Four distinct graphs because they answer four different questions for four different audiences. They are emitted as views over the durable log, not constructed after the fact.

1. **Execution-plan graph** — `EXPLAIN` for a run, *static, pre-run*: ≈N model calls / ≈M tool calls, est. cost range, critical path, "swap opus→haiku at node 7 saves 60%", which nodes need web/tool access, which nodes are *conditional* on confidence or amount. *Audience: the author.* Claude Code's plugin/cost preview is the embryonic version; SQL `EXPLAIN`, Spark DAG viz, and `terraform plan` are prior art.
2. **Compute graph** — what actually happened: plan-vs-actual, per-node tokens, latency, cost, retries. *Audience: ops.* Rendered as the same graph as the plan so you can diff prediction vs reality.
3. **Decision graph** — provenance of every human and agent decision: who · under what authority · on what evidence · reversible? *Audience: the auditor and the court.* The artifact a regulator subpoenas.
4. **Verification graph** — which claims were grounded against which method, and the **trust class** of each (web search ≠ a Lean proof ≠ a SQL query ≠ a calculator ≠ a human attestation). *Audience: the reviewer — "how do we know this is true."*

> Graphs 3 and 4 are what make the space **regulable**: "AI in a regulated decision must emit a conformant decision graph" becomes a writable rule the moment the format is standard. Today there is no artifact for a regulator to point at.

---

## The execution model — durable typed pipes for agentic work

The kernel-y picture, concretely. *Not* process-per-step (Unix pipes are cheap because text is cheap; agent state isn't) — **process-per-seam**, passing *handles* to context instead of bytes.

### Eight services, narrow interfaces

1. **Supervisor / scheduler** — the loop runner. Owns queue, budgets, routing, preemption, HITL coordination.
2. **Model gateway** — one service handling all API calls: prompt caching, retries, rate limits, cost accounting, vendor swap. Many supervisors share one gateway. *Large efficiency win on its own.*
3. **Context manager** — `pin` / `evict` / `rehydrate` as a service over the three-tier store (hot/warm/cold). Holds the JSONL transcripts. Hands out *handles*, not bytes.
4. **Tool runners** — each tool a worker with a declared shape contract; MCP is the proof this works.
5. **HITL broker** — owns queues, inboxes, signed-decision capture. Exposes "wait for decision X" as a callable — the blocking-syscall implementation.
6. **Memory service** — ontology DB (candidate/asserted tiers) + RSI markdown wiki, behind a typed read/write API.
7. **Provenance sink** — daemon the supervisor + tool runners + HITL broker all write events to. The four graphs are views over the log.
8. **Skill / command registry** — resolves named skills to their signed, versioned content.

### Pipes with shape, not pipes of bytes

Every inter-component message carries the envelope `{payload, schema_ref, provenance, cost, compute_class}`. Composition is *statically checkable* — you cannot feed a `Claim` into a stage expecting a `PolicyRecord`. Provenance is *carried alongside the payload*, not reconstructed afterwards. Prior art to steal from: PowerShell/nushell (typed pipelines), Arrow/Flight (zero-copy typed streams), gRPC + protobuf/Cap'n Proto (schema evolution), Erlang/OTP (supervision trees), Temporal/Restate/Inngest/DBOS (durable execution), Beam/Dagster/Pachyderm (typed dataflow + lineage). None has the *agentic* layer; the combination is the empty cell.

### Agentic commands ≠ Unix commands

Five properties Unix verbs do not carry:

- **Durable.** State checkpoints to the log; workers are fungible; crash → another worker picks up.
- **Longview.** A command can park for hours or days (waiting on a human, an external event, a schedule) without burning a slot.
- **Typed I/O with shape contracts.** Plus a `(confidence, evidence)` return on non-deterministic commands.
- **Compute-class tagged.** `deterministic | model | human` declared, not inferred — so the scheduler can route and the plan graph can be colored.
- **Provenance-emitting.** The envelope is the payload's lineage; composition preserves it automatically.

A real pipeline looks like:

```
load_claim
  | extract  --schema=Claim
  | match    --against=policy_db
  | ground   --claim.description --against=policy.exclusions  --require=evidence
  | compute  --payout="min(claim.amount - policy.deductible, policy.limit)"
  | when     "payout<=2000 ∧ conf>=0.9 ∧ ¬flagged" then auto_approve else manager_review
  | decide   --authority=auto_execute_policy | manager
```

Each `|` is a typed boundary on a durable log. `extract` and `ground` are model-class; `match`, `compute`, `when` are deterministic; `manager_review` and `decide` may park for the human leg. The plan graph *is* the pipeline; the compute graph is the log; the decision graph is the subset of log entries with authority + evidence stamps; the verification graph is the subset showing the grounding method per claim.

### Embedded mode → distributed mode

All eight services run in one binary by default — the *interfaces* are the architecture, not the topology. Split them across processes when scale demands. This dodges the "eight microservices are harder than one binary" failure mode while preserving the design.

### Honest costs

- Latency tax at process boundaries — fine for workflow agents (each step is seconds anyway), painful for coding-IDE agents (each step is sub-second and feel-driven). This is actually a *feature* for our wedge: the architecture is wrong for Cursor and right for claims-triage.
- The supervisor↔context-manager seam must use **handle semantics**. Ship 50k tokens per message and you lose.
- Schema evolution is real ops work (versioned shapes, deprecation windows). Not free; solvable.

> Reframed in industry terms: this is **a durable-execution engine for typed agentic workflows with first-class triad routing and provenance-as-payload**. Temporal-class, Beam-class, and LangGraph-class systems each cover *some* of that cell; none cover the combination. The monolithic agent harnesses (Claude Code, Cowork, Cursor, Codex) explicitly cannot, by construction — which is also why their security model collapses to "trust the whole process."

---

## Context, memory, RSI, and tiered inference

### Context as tiered storage, not a black-box window

Three tiers — **hot** (in-window) · **warm** (retrievable verbatim — files, transcript) · **cold** (compacted, lossy). Not demand-paging: you cannot re-fault a summary back to the original for free. Context tools — `pin`, `evict`, `rehydrate` — are explicit accounted operations, each with visible cost, each logged to the compute graph. A **context budget** + a **pluggable eviction policy** replaces the invisible auto-compaction every vendor does privately.

### Ontology — typed, two-tier, deterministic-inference target

Postgres + pgvector + Apache AGE (default — analysts know SQL, one system covers operational state + vectors + graph) or Neo4j (when multi-hop traversal dominates). DSL `MATCH` compiles to either. The target of *deterministic* inference (traversal, joins, constraint propagation).

**Write path.** LLM extract → pydantic validates shape → provenance stamp → `GROUND` against source → promote.

**Two tiers.** `candidate` (model-extracted, unverified, advisory) vs `asserted` (grounded or human-confirmed). *Deterministic inference runs over `asserted` only*; `candidate` informs routing and drafting but never decides. Pydantic checks "valid date in a valid field," not "the right date" — the GROUND step is what earns promotion.

**Ontology is a projection, not a fork.** If claims live in the carrier's claims system, the ontology is an index/projection — never a competing source of truth. Ingest; do not fork. What the ontology owns is the stuff with no other home: inferred relationships, domain rules, cross-references.

### RSI / experiential layer

Markdown/wiki accumulation — Karpathy-style lessons, Anthropic's memory/dream demos as embryonic versions. Open-ended, narrative, lossy. **Advisory — never decides.** Append-only, every entry stamped with the run(s) that produced it + a staleness signal. **Garbage-collected by the meta-loop** (reconciles contradictions, proposes pruning diffs for human review — same rubber-stamp caveat as every meta-loop write).

The ontology and the RSI layer are kept apart on purpose: facts-about-the-domain (typed, auditable) vs facts-about-doing-the-work (messy, advisory). Different shape, different write path, different trust class.

### Tiered inference

The supervisor routes per-node on `(confidence needed, cost budget, authority required)`:

- **T0** — deterministic over the ontology. No model. Cheapest, most trustworthy, fully auditable. *Try first.*
- **T1** — local / cheap model + retrieval + pydantic validation. Classify, extract, summarize, draft, flag. Bounded non-det with typed output.
- **T2** — frontier model. The hard reasoning, the novel case, the thing T1 flagged low-confidence.
- **T3** — human authority. The decision the model has no standing to make.

The execution-plan graph colors each node by tier. Local models earn their keep on high-volume bounded ops + on-prem data; the win is the *routing*, not the model.

---

## The DSL

### Design goals

- **Readable** by someone whose technical background is SQL and Excel.
- **Writable** by the same person, possibly with LLM assistance — realistically the first pass is LLM-generated from English and refined by analysts.
- **Declarative** — describes what the workflow is, not how it runs.
- **Diffable** — every change is a readable diff, version-controlled, reviewable.
- **Not Python.** Python fails analyst-readability *and* you cannot statically verify a Turing-complete language (no `EXPLAIN` graph for arbitrary code). Wrapping best-in-class Python tools is fine; making the substrate Python is not.
- **Not Zapier/n8n.** Visual flow-builders are not diffable or version-controllable and are shallow on AI primitives. **Text is canonical; the visual is a projection that round-trips back to text** — Terraform + plan visualizer, dbt + DAG view. Not Scratch.

### Example (abridged)

A claims-processing workflow:

```
SET MODEL        claude-opus-4.7
SET TEMPERATURE  0

PROFILE "MIDMARKET_CARRIER":
    LINES_OF_BUSINESS [commercial_auto, fleet]
    AUTHORITY_TIERS   [analyst, manager, fraud_specialist]

POLICY auto_execute:
    ALLOW auto_execute WHEN
        decision.confidence >= 0.90
        AND decision.amount <= 2000
        AND NOT claim.flagged_fraud

ENTITY Claim:
    claim_id       TEXT PRIMARY
    description    TEXT
    claim_type     ONE OF [collision, theft, glass, liability]
                   EXTRACTED
    amount_claimed MONEY EXTRACTED

STAGE evaluate_coverage:
    FROM claim WITH policy
    GROUND claim.description AGAINST policy.exclusions
           REQUIRE EVIDENCE FOR EVERY exclusion_hit
    IF coverage.covered == NO:
        DECIDE decline WITH reasoning = coverage.exclusions_hit
    ELSE:
        COMPUTE amount = MIN(claim.amount_claimed - policy.deductible,
                             policy.coverage_limit)
        DECIDE approve WITH amount

HITL manager_review:
    WHEN claim FLAGGED manager_queue
    AUTHORITY  manager
    SHOW       claim, policy, decision, decision.evidence
    ASK        "This claim exceeds $2,000. Approve, decline, or modify."
    REQUIRE    ONE OF [approve_as_is, modify_amount, decline, escalate]
    CAPTURE    reasoning AS text

SKILL claims_processor:
    RUN CONTINUOUS:
        intake, enrich, evaluate_coverage, route_decision, auto_execute
    ENABLE:
        manager_review, analyst_review, fraud_review
```

A domain expert should be able to read this and tell you what happens when a claim arrives. That is the test — and it must be validated by *actual* analysts modifying actual workflows, not asserted by the language designer.

### Verbs

The DSL compiles to a small set of kernel operations. In the DSL they look like SQL grammar; in the lowered IR they target the typed agentic-pipe substrate described above.

**Configuration:** `SET` (model, temperature, working folders).

**Entity / ontology:** `DEFINE` (typed objects, ontology classes) · `STRUCTURE` (project knowledge-base conventions — `build / list / add / remove / append / cascade`; markdown specs by default; Karpathy-append supported).

**Retrieval (deterministic):** `FIND` (locate documents/records — grep for the org) · `FETCH` (pull by id — curl for the org) · `VERIFY` (check a claim against authoritative sources).

**Provenance:** `LOG` (cost, compute class, tokens in/out, who/what, confidence, metrics — JSONL + OTel).

**Transformation (non-det but bounded — typed output, `(confidence, evidence)` return):** `EXTRACT` (pydantic-validated) · `SUMMARIZE` · `CLASSIFY` · `CONVERT` · `DIFF` · `DRAFT` · `PROMPT` + `WITH` (signed, versioned templates).

**Deterministic:** `COMPUTE` (run external code safely) · `MATCH` (transpiles to Cypher / SQL) · `WHEN` / `FLAG` (conditional logic — *never runs in the model*) · `SKILL` (make a DSL block a skill) · `EVAL` (run regression evals against the strongest open framework).

**Decision and state:** `DECIDE` (record a decision with full provenance) · `SEND` / `RECORD` / `UPDATE` / `ATTACH` (state operations — transactional, logged).

**Human-leg:** `HITL` block (declares authority, what to show, what to require, what to capture).

### Compilation path

DSL files lower through MLIR-style dialects:

1. **Surface syntax** — what the author writes.
2. **Typed execution graph** — nodes are primitive calls, edges are data flow, every node carries its provenance contract and compute-class tag.
3. **Target code** — orchestration for the supervisor, Cypher for graph queries, SQL for operational state, prompt templates for model calls, command wiring for tool runners.

Each lowering has a **verifier**. Missing evidence requirements on `GROUND`, missing authority on `HITL`, type mismatches between stages, an unsigned `PROMPT` in a regulated stage — caught at compile time.

---

## Knowledge engineering — the spec layer (why FDEs exist)

The layer the models do not subsume.

- **Spec quality is the new bottleneck.** Agents underperform because the spec is thin, not because the model is weak. The hard, high-leverage work moved from writing code to *eliciting and formalizing tacit domain knowledge* — which is why FDEs and "software-factory" shops (Palantir's FDE model, 8090.ai, et al.) exist. Better models raise the leverage on that role; they do not remove it. *The OS cannot automate tacit-knowledge extraction — it supports it.*
- **Specs are source, not documentation.** Spec + ontology + DSL workflows + prompts + canonical examples + evals all live in **one versioned repo** — diffable, reviewable, branchable ("try this policy change on a branch"). Markdown hierarchy, Karpathy-append style — *executable and incremental*, refined against the four graphs, not a 200-page upfront document.
- **Managed prompts = signed, versioned units, not strings.** A prompt is `{template, contract (inputs/outputs/required citations), test set (canonical examples it must pass), version, signature}`. Git gives the versioning, blame, and signed commits/tags; "managed" adds the contract + test set + a provenance stamp (prompt id + hash) in every artifact it produces — exactly what the verification graph and the signed-resources security requirement consume. Honest scope: signing buys *integrity and attribution* ("this is what was approved, unmodified"), like signed releases — not correctness; do not oversell it.
- **The OS ships the kit.** Project scaffolding (`STRUCTURE build`), per-domain starter templates (claims processing, prior-auth, contract review, KYC, intake forms…), and **canonical examples** — golden input → output pairs that double as documentation *and* eval fixtures. The Rails-generators / cookiecutter move: encode the conventions, make the good path the easy path. Skip it and every deployment reinvents structure — the standardization benefit evaporates.
- **The spec is in the improvement loop.** High override / rework on a stage is usually an *underspecified spec*, not a model failure — the meta-loop surfaces it and routes a **spec-revision task** to a human (FDE / ops lead), failing cases attached. The spec evolves with the deployment.
- **This is the deployment-specialist's kit — and what makes the labor portable.** A marketplace of deployment specialists is really a marketplace of *knowledge engineers*: elicitation + formalization + iteration. The kit — spec format, scaffolding, templates, example library, prompt discipline, eval harness, the ontology as the place to put what you extract — is what turns "I deploy agent workflows" into a portable trade, the way "I know SQL" is.

> Three places now touch "human knowledge" in this document — knowledge engineering (getting domain knowledge *in*), the RSI layer (the system accumulating operating knowledge), and the cognitive-fitness routing constraint (keeping humans *competent* to review it). They are distinct on purpose.

---

## The runtime

### Three backends, one set of primitives

The same compiled IR runs on:

1. **Claude Managed Agents / the Anthropic Agent SDK** — the hosted runtime. Production-ready today. Fastest path for teams already on Anthropic.
2. **Bare-metal reference** — cron + Postgres + systemd + object storage, with the embedded-mode binary running all eight services in one process by default. Proof the primitives can run on Linux alone. *Most important of the three — the portability guarantee.*
3. **A second-vendor adapter** (OpenAI Agents SDK or Grok) — proves the primitives are not secretly coupled to one vendor.

### Observability

Every primitive call is an event, emitted to two sinks simultaneously:

- **JSONL** — per-session, complete, human-readable. The replay/debug log; grep-able.
- **OTel** — aggregated, queryable, standard observability stack.

Citations and evidence are carried in both; JSONL has full text, OTel has attributes and cardinality-safe tags.

### Security

- First-class concern from day one, not a layer. Needs first-class security engineers, not the leftover.
- OAuth + MCP security; **signed, versioned prompts and resources + context hashes** in provenance.
- The decomposed-services architecture is itself a security feature — single-blob agent harnesses (see Cowork's published exfiltration write-ups) collapse to "trust the whole process." Typed pipes + per-message provenance + per-tool allowlists make exfiltration structurally visible.

---

## The UI layer

### Generated from the DSL

Entity declarations generate CRUD views. HITL blocks generate inboxes with the declared `SHOW` fields visible and `REQUIRE` options as buttons. `POLICY` and metric declarations generate dashboards. The four graphs each get their own visualizer. The generator uses an LLM against a typed component library — similar in spirit to v0, but driven by DSL declarations rather than free-text prompts, so output is consistent and bound to the data model. Analysts who want a custom view describe it in English; the generator reads the entity and queue declarations, produces a view spec, which becomes part of the DSL and is versioned.

**Text is canonical; the visual is a projection that round-trips back to text.** Terraform + plan-viz; dbt + DAG view.

### Three modes

- **The floor** — operator queues where work gets done. SLA-sorted, filtered by status, keyboard-navigable. Linear-adjacent in sensibility.
- **The desk** — ops-lead view. Metrics dashboards. Improvement-proposal review. DSL version history.
- **The office** — authoring view. DSL editor. LLM-assisted generation. Validation and compile output. The four-graph visualizer.

### HITL as the underbuilt layer

Coding agents barely need HITL — read the diff. Knowledge work *is* HITL. Work queues, review inboxes, decision workspaces, escalation paths, SLA timers — first-class. **"Agent-error-friendly"** means: when unsure, the agent emits a *well-formed review task with evidence attached* — never a hallucinated answer, never a silent block, never a crash.

### What the UI deliberately avoids

No chat box as primary surface. No agent-thinking animations as the default. No raw execution trace in the main view. No notifications for routine activity. **The work — the claim, the decision, the person waiting — is the center of the UI; the AI is a tool visible in its contributions, not the protagonist.**

---

## What's uncertain

Honest list, because serious reviewers care about this more than marketing.

1. **Whether the primitive set is right.** Provenance and authority feel unambiguously right. Goals and loops are well-established. Compaction might turn out to be implementation-level rather than kernel-level if context windows keep growing. Worth challenging.
2. **Calibration is unsolved and load-bearing.** `POLICY auto_execute WHEN confidence >= 0.90` and "when unsure, the agent emits a review task" both assume a calibrated confidence signal that mostly does not exist. Models are bad at knowing when they are wrong, especially on the cases that matter (confidently wrong). The strategy is: treat per-stage calibration as a first-class measurement, default conservative, *earn* auto-execute thresholds per-deployment from observed override rates rather than declaring them — but this is honest mitigation, not a solution.
3. **Whether Postgres + AGE or Neo4j is the right ontology backend.** Postgres + pgvector + AGE handles 80% of graph semantics and analysts already know SQL. Neo4j is more elegant for multi-hop queries but adds operational complexity. The DSL's `MATCH` compiles to either; undecided which becomes default.
4. **Whether generated UIs reach the quality bar.** The architecture promises DSL → generated UI. Getting from scaffolded views to "this doesn't feel like enterprise SaaS" is real design work that generation alone will not produce. Honest version: DSL gets 80% of layout; the final 20% is hand-tuned per domain.
5. **Whether "analysts author workflows" holds.** Reading and writing are different skills. First workflows will be LLM-generated and analyst-refined. If we cannot make the *refining* analyst-accessible, the thesis regresses to "yet another thing that needs engineers" and the marketing has to change accordingly.
6. **Whether the improvement-loop pattern is safe at scale.** Meta-loops that propose DSL changes create a new class of drift. The HITL review gate is the intended safeguard but also the most likely point of rubber-stamping. Needs more thought on guardrails, audit tracks, and rollback mechanics.
7. **Whether the substrate itself gets subsumed.** If models get dramatically better, some DSL constructs (extraction, grounding) may collapse into single model calls. The substrate is designed to degrade gracefully but the DSL's surface could become over-specified. Worth watching.
8. **Provenance has a known weak link.** A `Provenance` type is only as strong as its weakest link that doesn't carry it — and the LLM call is exactly that link (the model does not reliably report which context tokens drove its output; "citations" are themselves model output). The verification graph helps at the edges but for the *reasoning itself* a type declaration does not solve it. The trustworthy part is still the deterministic part.
9. **Governance and sustainability.** "Volunteer contributors in a timeboxed window" is how ambitious OSS specs die. Linux had Linus full-time + corporate backing within years. The honest version: this needs an institutional home eventually, and the "not asking for funding" stance is principled but probably has a half-life.

---

## The first concrete artifact — `explain` MVP

The doc is currently all synthesis. A better RFC does not recruit; a working slice does.

The smallest buildable thing that demonstrates the core: a CLI tool, `explain`, that takes a tiny workflow definition and:

- `explain plan <workflow> <input>` — prints the execution-plan graph: every node tagged `deterministic | model | human`, est. tokens/$/latency, dependencies, critical path, total cost range, and *which inputs require a human and why* — `EXPLAIN` for an agent run, before it runs.
- `explain run <workflow> <input>` — executes it: deterministic nodes run real Python, non-det nodes call Claude with prompt caching (record/replay supported), human nodes prompt in the terminal and capture a signed decision. Emits an append-only `events.jsonl` and writes `decision.provenance.json`.
- `explain compare <run-dir>` — plan-vs-actual.

Scope: ~1–2 weekends, one person, ~600–1000 LOC Python. Two fixtures (one auto-approves, one escalates to a human) so the **two `decision.provenance.json` files side by side are the pitch**. The MVP is a single-process simulation of the eight-service architecture; the growth path is literal, not a rewrite.

Full spec in `Project_EXPLAIN_MVP.md`. *This is what we point reviewers and prospective collaborators at, not the RFC alone.*

---

## What this RFC is asking for

### From systems engineers

Review the primitive set. Challenge it. The set matters; the count does not. Specific critiques of the durable-typed-pipes execution model, the session model, the provenance envelope, the budget/preemption semantics, or the authority primitive are especially valuable. If you would contribute to a reference implementation, say so — this is the Torvalds role (memory layouts, scheduler semantics, lock-free data structures). The kernel implementation requires a different cognitive profile than the DSL design.

### From compiler and DSL authors

The MLIR-style lowering path is a commitment; alternatives (single-pass compilation, interpreter-only, different IR shapes) are worth arguing about. The DSL syntax is drafted, not finalized — *specific* feedback on readability at the analyst level (ideally from analyst trials, not vibes) is worth more than general architecture comments.

### From domain operations leaders

If you have managed claims operations, customer service at scale, legal ops, medical prior authorization, or similar workflows — does the claims example read right? Does it describe the real shape of your work or oversimplify? Where would it fail in your environment? *If your organization would pilot a workflow on this, that is the validation that matters.* Pilot partners in mid-market regulated domains are the signal that turns specification into reality — though we know that is the hardest possible go-to-market for a pre-1.0 OSS effort, and we are open to lower-friction validation paths (internal-ops tooling, personal-knowledge-system variant, single-team deployments).

### From security and audit practitioners

The provenance / decision / verification graphs aspire to be the artifact a regulator or auditor can read. Tell us where they fall short of that bar. Signed, versioned prompts and resources — what is the right cryptographic model? What does "context hash" mean operationally? What is being implemented well in current US AI deployments, and what is missing?

### From people working on AI labor displacement

The labor thesis — a marketplace of deployment specialists, mid-career operators with domain + technical fluency, delivering workflows on this substrate at mid-market prices — is discussed elsewhere and not the core of this RFC. If it is interesting to you, the conversation is open.

### What the project is not asking for, yet

Funding. Partnerships with specific vendors. Formal foundation structure. Incorporation. All downstream of the technical work being validated by a reference artifact.

---

## Prior art and honest comparisons

- **LangChain, LlamaIndex, similar orchestration frameworks** — prove the demand. Fail the durability test: too coupled to current model behavior, framework-heavy, wrong audience (engineers, not domain experts).
- **Claude Code, Claude Cowork, Cursor, Copilot agent mode, Codex CLI, Aider, Grok agent** — production-quality monolithic harnesses with the right low-level instincts (sessions, fork, resume, compact). Vendor-coupled, single-process, no typed pipes, no provenance graph. *Cowork is Anthropic walking explicitly toward the knowledge-worker territory this RFC describes — the closed, single-vendor, no-DSL, no-provenance-graph version. Its published prompt-injection / file-exfiltration write-ups are an argument for the typed-pipe + signed-resource + verification-graph approach, not optional features.*
- **Claude Managed Agents, Anthropic Agent SDK, OpenAI Agents SDK** — production runtimes with clean primitive sets. Vendor-coupled. This project's primitives sit above them and make the DSL portable.
- **MCP (Model Context Protocol)** — right shape. Tool interface as protocol, not framework. The substrate assumes MCP or equivalent for tool calls.
- **Temporal, Restate, Inngest, DBOS** — durable-execution engines. Mature workflow primitives, no agentic vocabulary or triad routing. Steal the durability patterns.
- **Apache Beam, Flink, Dagster, Prefect, Pachyderm** — typed dataflow with lineage. Batch-shaped, no agentic vocabulary. Steal the lineage patterns.
- **Ray** — distributed compute. Overkill for most domain agent work; reference architecture uses simpler primitives.
- **Palantir Foundry** — the closest commercial analog in spirit: ontology + workflow + deployment expertise. Closed, expensive, enterprise-only. The moat is the FDEs and the deployment patterns, not the software. This project is the open-source reading of similar ideas for mid-market — and is in honest tension with the "deployment-services business" angle: open primitives commoditize what services businesses sell.
- **8090.ai-style "software factory" shops** — bet on FDEs + AI making custom-software delivery faster. Adjacent and complementary; the kit this RFC describes is what raises FDE leverage.
- **Retool, n8n, Zapier** — workflow tools for non-engineers. Too shallow on AI primitives; too tied to visual editing rather than versionable declarative files.
- **PowerShell, nushell** — typed pipelines as day-to-day tools. Proof the model is usable; this project's "shape" envelope steals directly.
- **SQL, Excel** — proof that the right grammar expanded the data-literate TAM from engineers to operators by orders of magnitude.
- **Ruby on Rails, cookiecutter, create-react-app** — scaffolding + generators + conventions as the on-ramp. The kit this RFC ships borrows their move.
- **PHP, ColdFusion (Web 1.0 era)** — high-level server-side abstractions that expanded developer bases over CGI/C/C++/Perl. The equivalent expansion is what is on offer here.

The differentiator is not any single feature. It is the **combination**: thin set of primitives, durable typed-pipe execution model, analyst-readable DSL, backend-agnostic runtime, generated UIs, human authority as a first-class compute class, four-graph accounting, knowledge-engineering kit, improvement loops as first-class, open source.

---

## Timeline, loosely (and honestly)

A small group with AI coding agents in a timeboxed window can produce high-quality spec artifacts. Executing on adoption-grade open primitives — the AI Linux, SQL, or Terraform — is a multi-year commitment that needs an institutional home.

- **Sprint 1.** RFC review and revision; identify 1–2 technical collaborators; ship `explain` MVP (the wedge).
- **Sprint 2.** Primitive set finalized; reference implementation begins (in-process embedded mode); shape registry + provenance sink real.
- **Sprint 3.** DSL grammar and compiler proof-of-concept. Runs a non-trivial workflow against CMA backend.
- **Sprint 4.** Bare-metal runtime reference implementation. Memory service real. First pilot deployment attempted (or personal-knowledge-system variant for faster validation).
- **Sprint 5.** Generated UI layer (the four-graph visualizers + the floor/desk/office). Second pilot. Public release v0.1.

This is conservative *given two senior engineers full-time plus the author*. It is not conservative as a volunteer effort. It will slip. The goal is to establish the work is buildable with a small team, not to promise dates. The previous draft's "5 sprints, 2 senior engineers + author" framing was off by an order of magnitude for the full scope; **the wedge (the `explain` MVP and the embedded-mode reference) is buildable in roughly that window. The rest is multi-year.**

---

## How to respond

Technical review, critique, and interest in contributing: [contact method].

Specifically valuable:

- "Here is why primitive X is wrong" + proposed alternative.
- "I would contribute to [specific component] — kernel / DSL compiler / memory service / HITL broker / UI generator / provenance graphs / shape registry."
- "My organization would pilot a workflow for [specific use case]."
- "Here is what your durable-execution model gets wrong; here is what Temporal/Restate/Beam already solved."
- "Your DSL syntax fails analyst-readability — here is what I tried with three actual analysts."

Less valuable but welcome:

- General enthusiasm.
- Suggestions to pivot to a different problem.
- Offers that assume this is a funded startup rather than a specification under review.

---

*This document will be revised based on feedback. Revision history maintained in the repository. The current version is a draft for discussion; nothing in the specification is final until the first reference implementation — the `explain` MVP — validates or invalidates it.*

*Revision 2 (May 2026) incorporates the triad reframe, the durable typed-pipes execution model, the four graphs as a peer to the primitives, the knowledge-engineering / managed-prompts layer, the ontology two-tier + RSI split, the calibration honesty, the Linux/macOS-rather-than-POSIX framing, and the `explain` MVP as the first concrete artifact. Original Revision 1 (April 2026) is preserved in repository history.*
