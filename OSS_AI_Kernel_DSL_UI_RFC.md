# RFC: An AI Execution Kernel, DSL and Generated UI System for Human-AI Agent and Knowledge Work

**Status:** Early draft for discussion

**Author:** David L. Jones - I have worked in tech for over 3 decades as an developer / analyst, consultant, employee across a number of industries including startup, midsize growth andd Fortune 500. Like many of us, I have been digging into AI while having the fortune of having time off to observe the best in the AI/ML industry on X and elsewhere, experiment, learn, and research while off full-time work for over 2 years.

**Date:** April 2026

**Intended audience:** Systems engineers, compiler authors, domain operations leaders, and anyone who has watched the current AI framework churn with skepticism.

**Theses** Are we at inflection point in the AI industry where we need to have an open source layer ontop of models that looks like an AI kernel or OS? How do we bring in non-developer workers into the human AI cowork, authoring and UI design prcoess for the new phase of agents and regulated work that accounts for human, GPU and CPU components, costs, and knowledge engineering in smart ways? Is it time for open source AI stack primitives that look like something like Linux, SQL and novel generated UI's that fit the domains of the workers? As the AI labor transition emerges, how do we respectfully maintain human cognitive fitness and the skills and knowlege required to review and operate AI and the work it augments and replaces? As industry leaders have conveyed, the US and China competitive effort may hinge on open source. Many of the venerable foundations of US technology and growth that have reliably and widely ran disparate industries, products and services for decades have stood the test of time bcause they were open.


---

## Summary

This document proposes a small, stable execution kernel and declarative DSL for AI-augmented knowledge work. The thesis is that the current generation of agent frameworks — LangChain, various orchestration platforms, vendor-specific agent APIs — are comparable to jQuery before React or Web Components or UNIX flavors before Linux: useful, ubiquitous, and temporary. The primitives they expose are too coupled to current model behavior and will be subsumed as models capabilities improve.

What's missing is the equivalent of the primitives that survived the last paradigm shift: a thin, composable kernel with clean separation between deterministic operations, non-deterministic model calls, and human authority. Something that domain experts — not engineers — can author against. Something that an ops lead with SQL-level literacy can read and reason about. Something whose value compounds as models improve rather than dissolves.



The proposal has six parts:

1. **An open AI kernel and primitive specification** defining primitives for goals, loops, sessions, provenance, and authority. Current Linux infrastructure could support this with its scheduler, cron or systemd, though this RFC seeks comment on a new implementation in Rust. Backend-agnostic.
2. **A DSL** that reads at the SQL-analyst level, compiles to a typed IR, and targets the kernel. A first iteration could target a fluent Python API that leverages the rich AI/ML library ecosystem and later or safe parts in Rust and MLIR. Notably, the DSL is the declarative infrastructure substrate authored by domain experts, not engineers.
3. **A runtime abstraction** that binds the kernel to existing agent platforms (Claude Managed Agents, OpenAI Agents) or to a bare-metal implementation using Linux, Postgres, and object storage. No vendor lock-in. This more than a harness.
4. **A generated UI layer** derived from DSL declarations, producing operational interfaces (queues, dashboards, HITL decision workspaces) that domain users actually work in. Consider Ruby on Rails or other generative UI frameworks that work from a domain model or tables as prior art.
5. **Provenance graphs** execution plan; compute; verification; and human graphs that track and measure costs, metrics and auditable decisions and target JSON-L and O-Tel.
6. **Cognitive fitness and human skills**: with the human AI cowork transition, it becomes imperative, without overreach, to understand how human work, cognitive load and effects, and how roles may be redefined with the required skills and costs for human review of AI and ongoing maintenance of skills and knowledge competency for workers. Let's consider this important aspect as primitives.

This RFC is seeking: technical review, collaborators for the kernel and compiler implementation, and pilot partners in generalized and regulated mid-market domains (insurance, healthcare, legal operations) where the thesis can be tested.

While not open source, Anthropic's Claude for Managed Agents is a leading eovlution of this moving in the right direction. **It's strength lies in separating the hands (tools/skills/harness) from the brain (model), and optimizing deterministic (LLM on GPU's) and proven non-deterministic components (CPU based).** We see it leveraging bash, git, file operations and concepts of sandboxd, resumable, longview sessions and environments as a lean set of primitives coupled with MCP, skills, web search, browser and compute use, and  context and tools alongside Markdown specs in a hierarchical system.

This is a specification seeking contributors and critique.

---

## Why now, why this

### The paradigm problem

The current AI application stack is fragmented along lines that will not survive the next 18-24 months of model progress. In addition, we should look this initiative as competitive in US interests versus China as open source leadership and innovation. 

- **Orchestration frameworks** that encode specific agent topologies. Better models will dissolve them.
- **Retrieval pipelines** with elaborate chunking and reranking. Long-context and native search capabilities are eating these.
- **Prompt engineering frameworks** building around prompt fragility. Models are becoming robust enough that elaborate chains are becoming anti-patterns.
- **Vendor-specific agent APIs** that encode one company's bet on what agents are. OpenAI's Assistants API was abandoned; others will follow.
- **Thick wrapper products** that bolt an AI layer onto existing SaaS. These look good in demos and struggle in production because they can't surface the AI's work in ways operators can govern.

Enduring software like Linux, React and SQL and its descendants won not because they were fastest but because they identified durable primitives — POSIX standards, components as functions and a simple grammar that extends the user base beyond engineers. The AI space has not yet found its equivalents, but the shape of them is becoming visible. Additionally, heterogenuous compute and regulated environments do have cases where structure beyond English is needed for reproducable results and provenance for decisioning records and audits.

### The durable primitives, identified

After examining what Claude Code, Claude Managed Agents, and production agent deployments actually do well, five primitives appear consistently as the things that matter regardless of model capability:

1. **Goals** with explicit completion conditions — not "prompts," but typed objectives with deterministic or non-deterministic evaluation.
2. **Loops** with stagnation detection — the work loop (pursuing a goal) and the meta-loop (observing the work loop's performance).
3. **Provenance** on every artifact — who or what produced this, when, from what source, with what confidence. Separating GPU and CPU compute and human deicisioning provides a pathway to track costs and human skills and cognitive fitness and capability required for work.
4. **Authority** as a first-class concern — human approval is not a tool call; it is an authoritative and binding primitive that models cannot replace.
5. **Compaction** of state — summarization and rewinding as kernel operations, not add-ons.

Everything else — retrieval strategies, prompt structures, agent topologies, specific tool integrations — is application-level and will change. These five are substrate. They are the shape of the problem, not the shape of a current solution.

### The human-first thesis

Most AI infrastructure assumes the human is a fallback — something to route to when the AI fails. This gets the architecture wrong. In regulated domains, the human is not a fallback; the human is the authority whose approval is the completion criterion. "The manager approved" and "the model approved" have categorically different legal and epistemic status. Building this distinction into the kernel rather than into application code is what lets the same primitives serve healthcare, legal, insurance, and financial operations without being rebuilt for each.

The corollary: the people authoring agent workflows should be domain experts, not engineers. An analyst who reads SQL and writes Excel formulas should be able to read a workflow file and see what happens when a claim arrives, who reviews it, and how the improvement loop runs. If authoring requires a Python developer, the thing has failed. Most current frameworks fail this test. There is a TAM estimated at up to 50 million or more users in the United States that has SQL or Excel level skills, meaning they can work with business concepts and technical capability to operate and faciliate work in a mental model they understand.

---

## The kernel specification

### Primitives

The kernel defines the following typed primitives. Each is minimal. Each is composable. Each is backend-agnostic.

**Goal**
```
Goal {
  completion_type:  composite_and | composite_or | single
  conditions:       [Condition]
  eval_method:      deterministic | model | human_authority
  max_iterations:   int
  stagnation_policy: diagnose | escalate | meta_loop | fail
}
```

A goal declares what "done" means. Evaluation is explicit: deterministic conditions are checked by the runtime, model conditions by an LLM call, human authority conditions by a signed decision from an authorized person.

**Loop**
```
Loop {
  kind:           work | meta
  goal:           Goal
  observe:        [StateRef]
  act:            [PrimitiveCall]
  on_stagnation:  StagnationPolicy
}
```

A loop pursues a goal. The work loop operates on domain state (claims, documents, conversations). The meta-loop operates on the work loop's performance (metrics, human or LLM judge override rates, drift, turns). Same primitive, different observation target. Meta-ness is not a separate construct. OODA loops have been referenced in recent AI discussion circles. This presents features of RSI or improvement that could be kernel levels features or constructs alongside an application or organizations knowledge system.

**Session**
```
Session {
  id:          SessionId
  state:       SerializedState
  history:     JSONL append-only log
  can_fork:    bool
  can_resume:  bool
  can_pause:   bool   // for human authority
  can_compact: bool
}
```

A session is an instance of a loop pursuing a goal, with full serialized state. Sessions can fork (explore alternatives), pause (await human authority), resume (after compaction or human input), and compact (summarize history when context pressure builds). These capabilities mirror what Claude Code and CMA implement today — the kernel formalizes them as first-class operations rather than vendor features.

**Provenance**
```
Provenance {
  producer:       Actor           // model_id | human_id | tool_id
  produced_at:    timestamp
  sources:        [SourceSpan]    // citations, evidence
  confidence:     float | null    // null for deterministic
  authority:      AuthorityLevel  // legal/epistemic weight
}
```

Every artifact the kernel produces carries provenance. This is not optional. Not instrumentation. Part of the type. An extracted field, a model decision, a human approval, a Cypher query result — all carry their origin, their evidence, their confidence, cost, compute class, and their authority level.

**Authority**
```
Authority {
  level:      tier_name
  held_by:    PersonRef | RoleRef
  delegation: [AuthorityRule]
}
```

Authority is the legal and epistemic weight an actor has to decide something. A claims analyst has authority to approve up to $2,000. A manager has authority above that. A model has no authority in the legal sense but contributes evidence to decisions humans make. Authority is checked by the runtime on every decision that requires it; mismatches are compile-time errors when possible and runtime failures when not.

### What the kernel deliberately does not specify

- Which LLM to call. Models are pluggable.
- How retrieval works. Tool calls return typed results; the kernel doesn't care whether the backend is a vector store, a graph database, or a keyword search.
- Which orchestration topology to use. Single-agent is the default; sub-agents are a runtime detail, not a primitive.
- Specific prompt templates. Prompts are data, versioned alongside DSL files. Examples are related artificats with the same attributes.
- UI rendering. The kernel emits events; the UI layer subscribes.

### Why five primitives and not more

Discipline. Every additional primitive is a commitment to a worldview that might not survive. Provenance is a bet that auditability will always matter — a safe bet. Authority is a bet that human decisions will remain legally distinct — also safe. Goals and loops are bets about the shape of iterative work — confirmed by two years of production agent use. Compaction is a bet that context will always be budgeted — safe given current architectures, and trivially reducible to a no-op if it isn't.

Everything else is application-level. Skills, memory, knowledge bases, multi-agent coordination — all built on top, none in the kernel. If they turn out to be wrong, the kernel survives. If they turn out to be right, they're straightforward to add.

---

## The DSL

### Design goals

- Readable by someone whose technical background is SQL and Excel.
- Writable by the same person, possibly with LLM assistance.
- Declarative: the file describes what the workflow is, not how it runs.
- Diffable: every change is a readable diff, version-controlled, reviewable.
- Separable: ontology, workflow, policy, and UI hints can live in one file or be split as the project grows.

### Example (abridged)

A claims processing workflow:

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

A domain expert can read this and tell you exactly what happens when a claim arrives. That is the test.

### Primitive verbs

The DSL compiles to a small set of kernel operations. In the DSL these look like SQL grammar, but when transpiled to IR, Python or Rust kernel they run library or are equivalnet of new composable bash shell equivalents that have API's.

Unix commands succeeded because they were:
1. Small, do one thing
2. Composable via pipes (text in, text out)
3. Deterministic and predictable
4. Invocable by name with simple arguments

The AI-native equivalent needs those properties but for work that's not file-oriented. Let me take a pass at what the core set might be. These aren't tools in the Claude Code sense — they're primitive operations that show up again and again in general knowledge work, like grep shows up again and again in text processing.

**Configuration**
- `SET` - model, temperature, top_p, working folders

**Entity/ontology**
- `DEFINE` - build a definition w/ types. generates a class / domain objects. maybe graph / neo4j
- relations - 
- `STRUCTURE` - knowledge base / spec structure. Sets up conventions for project folder structure organized in a logical way reflect or use or organization. Switches: build, list, add, remove, append to, or cascade a knowledge structure. File system .md's with specs default. Append supports Karpathy style improvement.
- neo4j, PostGres and the create-context-graph and other sources?

**Retrieval primitives** (deterministic):
- `FIND` — locate documents/records matching criteria. Grep for the org, essentially. Takes a query, returns matches with citations. Does not interpret. Linux has find. Run against kb, onotology and other sources?
- `FETCH` — pull a specific document/record by id. Like curl for the org.
- `VERIFY` — verify a claim against authoritative sources. Takes a claim and sources, returns pass/fail with evidence.

- `MEMORY`
- `CONTEXT`
- `TOOLS: MCP, os, det, nondet`
- `SECURITY: oauth` - this part is big. We'll need first class security engineers.

**Provenance**
- `LOG` - costs, compute class, tokens count i/o. who/what. confidence? metrics. jsonl otel 
- Graphs: execution plan, compute, verify, human

**Transformation primitives** (non-det but bounded):
- `SUMMARIZE` - compress content to a target length or target schema. Parameterized by audience and depth. default, verbose, succint
- `EXTRACT` - pull structured data out of unstructured content into a schema. Verifies with pyndantic. Uses parses like docling or google langextract
- `CLASSIFY` - assign a record to categories with confidence.
- `CONVERT` - not just language; translate between formats, audiences, or levels of abstraction (technical → executive).
- `DIFF` - explain what changed between two versions in terms the user can act on. Not line-by-line — meaning-by-meaning.
- `DRAFT` - draft
- `PROMPT` + `WITH` - prompt templates in file system preferred, though inline support. Can add with system, examples. Intended to support signed prompts and work with git as version control.  
- 'EVAL' - how do we author, run and regress evals for a wide variety of domains, and use the best open source tool for this? This will work alongside pydantic. 

Deterministic:
- `SKILL` - Make a DSL block a skill
- `COMPUTE` - Run external code safely and get return value. Defaults to python
- `WHEN` `FLAG` - Simple conditional logic. This should not run in the model.

**Human Cognitive Fitness, Human Skill Assessment and Maintenance**
- For human AI cowork, this is very important for HITL and ongoing maintenance and competency of human knowledge and skills that AI performs.

NOTE: we should see words GOAL, METRIC, LOOP in here. Need do: while, until and conditions met concepts. Concepts of cost and time.

**Meta-loop primitives** (deterministic wrapping non-det):
- `MEASURE` - compute a metric over a history.
- `DETECT-DRIFT` - flag when a metric trends unfavorably.
- `IMPROVE` - trigger a meta-loop that proposes changes to the work loop. Karapthy style auto research RSI or org wide version against kb.
- `PROPOSE-CHANGE` - non-det suggestion with deterministic diff output.

- metrics; logging; costs; human labor skills and competency: test, maintain and improve, cognitive fitness

Consider reducing these to a smaller set:

- **EXTRACT** — structured data from unstructured input (non-det; returns confidence + evidence)
- **MATCH** — query the ontology (deterministic; transpiles to Cypher or SQL)
- **GROUND** — check a claim against source material (non-det; requires evidence)
- **COMPUTE** — deterministic math or logic
- **DECIDE** — record a decision with full provenance
- **COMPOSE** — generate output text (non-det; can require evidence)
- **SEND / RECORD / UPDATE / ATTACH** — state operations (deterministic, transactional, logged)

Seven model-touching or state-changing verbs. Everything else is structural. One possibility is these could map to Linux bash commands and allow for composition similar to the existing I/O of the pipe system.

**Security**

- This needs to be done right as first concern with best resources. 
- Include OAUTH and MCP security
- Provenance should include support for versioned and signed prompts and other resources and also context hashes. Is this being implemented well in US AI stack right now? 
- What is important this is missing or needs to be done better?

### Compilation path

DSL files lower through MLIR-style dialects:

1. **Surface syntax** — what the author writes.
2. **Typed execution graph** — nodes are primitive calls, edges are data flow, every node has its provenance contract.
3. **Target code** — Python for session orchestration, Cypher for graph queries, SQL for operational state, prompt templates for model calls.

Each lowering has a verifier. Missing evidence requirements on GROUND calls, missing authority declarations on HITL blocks, type mismatches between stages — all caught at compile time.

---

## The runtime

### Three backends, one kernel

The same compiled IR runs on:

1. **Claude Managed Agents** — the hosted runtime. Production-ready today. Fastest path for teams already on Anthropic.
2. **Bare-metal** — cron + Postgres + systemd + object storage. The reference implementation. Proof the kernel can run on Linux primitives alone.
3. **Grok API** — adapter. Proof the kernel isn't secretly coupled to one vendor.

The bare-metal implementation is the most important of the three because it's the portability guarantee. If the kernel works there, it works anywhere.

### The bare-metal architecture

Session state serializes to JSONL in object storage, one file per session, append-only. Every primitive call is an event; every event is logged. This is the same pattern Claude Code uses locally — it works at scale, it's grep-able for debugging, and it supports fork/resume/compact with no special infrastructure.

Postgres holds operational state: queues, decisions, metrics, schedule. Neo4j (or any graph backend) holds the ontology when graph traversals matter; Postgres tables with an edges table work for simpler cases. A systemd worker pool picks up tasks from a Postgres queue, runs sessions, handles pause/resume via webhook or polling. Cron fires the meta-loop stages daily.

This is all boring proven infrastructure. That's the point.

### Observability

Events emit to two sinks simultaneously: JSONL (per-session, complete, human-readable) and OTel (aggregated, queryable, standard observability stack). JSONL is for replay and debugging. OTel is for cross-session analytics. Citations and evidence are carried in both; the JSONL has full text, OTel has attributes and cardinality-safe tags.

---

## The UI layer

### Generated from the DSL

Entity declarations generate CRUD views. HITL blocks generate inboxes with the declared SHOW fields visible and REQUIRE options as buttons. POLICY and metric declarations generate dashboards. DESTINATION declarations generate output panels.

The generator uses an LLM against a typed component library — similar in spirit to tools like v0 but driven by DSL declarations rather than free-text prompts, so output is consistent and bound to the data model. Analysts who want a custom view describe it in English; the generator reads the entity and queue declarations, produces a view spec, which becomes part of the DSL and is versioned.

### Three modes

- **The floor** — queue views where operators work. Sorted by SLA, filtered by status, keyboard-navigable. Linear-adjacent in sensibility.
- **The desk** — operations lead view. Metrics dashboards. Improvement proposal review. DSL version history.
- **The office** — authoring view. Workflow file editor. LLM-assisted DSL generation. Validation and compile output.

Each mode is generated from the same DSL declarations, projecting them differently for different audiences.

We're going "workers" view over just chatbot, CLI or these bolted onto existing UI's.

### What the UI deliberately avoids

No chat box as the primary surface. No agent-thinking animations as the default. No raw execution trace in the main view. No notifications for routine activity. The work (the claim, the decision, the person waiting) is the center of the UI; the AI is a tool visible in its contributions, not the protagonist.

---

## What's uncertain

Honest list, because serious reviewers care about this more than marketing.

**1. Whether the primitives are actually the right five.** Provenance and authority feel unambiguously right. Goals and loops are well-established. Compaction might turn out to be implementation-level rather than kernel-level if context windows keep growing. Worth challenging.

**2. Whether Neo4j is the right ontology backend.** Postgres with an edges table handles 80% of graph semantics and analysts already know SQL. Neo4j is more elegant for multi-hop queries but adds operational complexity. Undecided; the DSL's MATCH clauses should compile to either.

**3. Whether generated UIs can reach the quality bar.** The architecture promises DSL → generated UI. Getting from scaffolded views to "this doesn't feel like enterprise SaaS" requires real design work that generation alone won't produce. The honest version: DSL gets you 80% of layout; the final 20% is hand-tuned per domain.

**4. Whether "analysts author workflows" holds in practice.** Reading SQL and writing SQL are different skills. First workflows will likely be LLM-generated from English and refined by analysts. The authoring experience matters as much as the runtime. If we can't make this work, the thesis regresses to "yet another thing that needs engineers."

**5. Whether the improvement-loop pattern is safe at scale.** Meta-loops that propose DSL changes create a new class of drift. The HITL review gate is the intended safeguard but it's also the most likely point of rubber-stamping. Needs more thought on guardrails, audit tracks, and rollback mechanics.

**6. Whether subsumption hits the DSL itself.** If models get dramatically better, some DSL constructs (extraction, grounding) may collapse into single model calls. The kernel is designed to degrade gracefully but the DSL's surface could become over-specified. Worth watching.

---

## What this RFC is asking for

### From systems engineers

Review the kernel specification. Challenge the primitive set. The right five primitives are the foundation of everything else. If there are four, or six, or a different five, better to find out now than after the implementation is committed. Specific critiques of the Rust implementation approach, the session model, the provenance type, or the authority primitive are especially valuable.

If you'd contribute to a reference implementation, say so. This is the Torvalds role — someone who thinks in memory layouts, scheduler semantics, and lock-free data structures. The kernel implementation requires a different cognitive profile than the DSL design.

### From compiler and DSL authors

The MLIR-style lowering path is a commitment. Alternatives (single-pass compilation, interpreter-only, different IR shapes) are worth arguing about. The DSL syntax itself is drafted but not finalized; specific feedback on readability at the analyst level is worth more than general architecture comments.

### From domain operations leaders

If you've managed claims operations, customer service at scale, legal ops, medical prior authorization, or similar workflows — does the claims example read right? Does it describe the real shape of your work or does it oversimplify? Where would it fail in your environment?

If your organization would consider piloting a workflow built on this, that signal is what transitions the work from specification to real. Pilot partners in mid-market regulated domains are the validation that matters.

### From people working on AI labor displacement

The project's go-to-market involves a marketplace of deployment specialists — mid-career operators, recently displaced, with domain plus technical fluency, who can deliver workflow implementations on this platform at costs mid-market customers can afford. This is discussed elsewhere and not in this RFC, but if the labor thesis is interesting to you, the conversation is open.

### What the project is not asking for, yet

Funding. Partnerships with specific vendors. Formal foundation structure. Incorporation. All of these are downstream of the technical work being validated.

---

## Prior art and honest comparisons

- **LangChain, LlamaIndex, similar orchestration frameworks**: These prove the demand. They fail the durability test — too coupled to current model behavior, too framework-heavy, wrong audience (engineers, not domain experts).
- **Claude Managed Agents, OpenAI Agents SDK**: Production-quality runtimes with the right low-level instincts (sessions, fork, resume, compact). Vendor-coupled. This project's kernel is what sits above them and makes the DSL portable.
- **MCP (Model Context Protocol)**: Right shape. Tool interface as protocol, not framework. The kernel assumes MCP or equivalent for tool calls.
- **Temporal, Ray**: Mature workflow and distributed compute systems. Overkill for most domain agent work. The bare-metal runtime deliberately uses simpler primitives.
- **Palantir's Foundry**: The closest commercial analog in spirit — ontology plus workflow plus deployment expertise. Closed, expensive, enterprise-only. This project is the open-source reading of similar ideas for mid-market.
- **Retool, n8n, Zapier**: Workflow tools for non-engineers. Too shallow on AI primitives; too tied to visual editing rather than versionable declarative files.
- **SQL, Excel**: These skills greatly expanded access to data, reporting, and business intelligence to a wide range and TAM of users that are domain experts and everyday, valuable contributors. These and users of other business software have a level of technical skills that should be involved in wide range of AI human cowork solutions that do not require highly skilled software and AI/ML engineers.
- **PHP, ColdFusion**: In the Web 1.0 era, these were high level server-side programming abstrations that enabled rapid development and expanded developer bases over more skilled CGI, C/C++, Perl and other original paradigms.
- **Ruby on Rails**: The ability to generate a working CRUD UI from a domain model and DB tables along with opinioned conventions enabled iterative development and proving of ideas.

The differentiator is not any single feature. It is the specific combination: thin kernel, analyst-readable DSL, backend-agnostic runtime, generated UIs, human-authority as primitive, improvement loops as first-class, open source.

---

## Timeline, loosely

Looking to put together a group of contributors that wants to approach this with AI coding agents and high quality spec production in a timeboxed window. While execution and collaboration and what is possible with today's tools is desired, building an reusable, adoptable open source primitives that could be the AI Linux, SQL or Terraform is imporant.

- **Sprint 1**: RFC review, feedback, revision. Identify 1-2 technical collaborators.
- **Sprint 2**: Kernel specification finalized. Rust implementation begins on core primitives (goal, loop, session, provenance).
- **Sprint 3**: DSL grammar and compiler proof-of-concept. Runs a simple workflow against CMA backend.
- **Sprint 4**: Bare-metal runtime reference implementation. Neo4j/Postgres integration. First pilot deployment attempted.
- **Sprint 5**: Generated UI layer. Second pilot. Public release of kernel and DSL v0.1.

This is conservative. It assumes two senior engineers plus the author working substantially on the project. It assumes pilot partners cooperate on a timeline appropriate to them, not the project. It will slip. The goal of the timeline is to establish that this is buildable with a small team, not to promise delivery dates.

---

## How to respond

Technical review, critique, and interest in contributing: [contact method].

Specifically valuable:
- "Here is why primitive X is wrong" + proposed alternative.
- "I would contribute to [specific component]."
- "My organization would pilot a workflow for [specific use case]."
- "This is Knockout.js or Underscore before React, Angular and Web Components; here's what you should steal from [specific prior work]."

Less valuable but welcome:
- General enthusiasm.
- Suggestions to pivot to a different problem.
- Offers that assume this is a funded startup rather than a specification under review.

---

*This document will be revised based on feedback. Revision history maintained in the repository. The current version is a draft; the thesis is serious but nothing in the specification is final until the first reference implementation validates or invalidates it.*
