# AI DSL Roadmap — "Do You Speak Bocce?"

One person. No funding. Big vision. This roadmap is constrained to reality.

The dream: AI DSL becomes the lingua franca for agents, robots, smart homes,
compliance, military, whatever domain — the structured layer between English
and execution. The "SQL for AI" that non-engineers can read and machines can
verify. Python and English need a frontman. This is it.

The reality: You're one guy, unknown, eating top ramen in your trunk.
Academic probation from the school of shipping. Four AI tools have said
"great idea, ship it." Zero humans have paid for it.

**Rule: No more ideation sessions until something ships and someone reacts.**

---

## What Exists (v0.1 — Done)

- 3 verbs: EXTRACT, CLASSIFY, DRAFT
- 5 types: TEXT, MONEY, NUMBER, YES/NO, ONE OF
- Nested types, LIST OF
- Sources: CSV, JSON, folders, HTTPS API
- FLAG WHEN (deterministic CPU rules)
- SET block (model, temperature, seed, headers)
- PROMPT and EXAMPLES modifiers
- Python fluent API (SchemaBuilder, Pipeline)
- 165+ tests passing
- README, CONCEPTS, security model WIP
- Business Source License 1.1

This works. It's complete for what it does. Stop touching it until customers
ask for changes.

---

## The Vision Stack (What Was Ideated)

These came from sessions with Gemini, Grok, Copilot, and Claude. All good
ideas. None validated by a paying human.

| Layer | Status | Ship When |
|---|---|---|
| Pydantic validation | Gap — hand-rolled today | First (internal quality) |
| SUMMARIZE verb | Missing — obvious gap | First (small, useful) |
| STAGE (named pipeline steps) | Ideated | When a customer needs multi-step |
| SKILL (composable agent units) | Ideated | When a customer needs agents |
| HITL (human-in-the-loop) | Ideated | When a customer needs approval flows |
| Generated Python API | Ideated (Grok rec) | When maintaining two surfaces hurts |
| Verify Graph (trust metadata) | Ideated — keep simple | Could ship standalone |
| Behavior Trees | Ideated (Grok/robotics) | When a robotics customer appears |
| LTL safety monitors | Ideated (Grok/robotics) | When safety-critical domain appears |
| Domain verb packs | Ideated | When base is stable + adopted |
| Device auto-discovery | Ideated | When IoT customer appears |
| Skill registry / fleet hub | Ideated | When multiple deployments exist |

**The rule: nothing moves from "ideated" to "building" without customer pull
or community signal. The only exceptions are Pydantic and SUMMARIZE, which
are internal quality and obvious gaps.**

---

## Phase 0: Health + Foundation (Now — 2 weeks)

You can't ship if you can't think. Brain health is not optional.

- [ ] Food: Replace ramen with beans/rice/eggs/greens. $30/week. Non-negotiable.
      Your doctor is right. This is a blocker, not a lifestyle choice.
- [ ] Pydantic migration: Replace hand-rolled validator with Pydantic models.
      Internal quality. Makes the Python API credible. ~2-3 sessions.
- [ ] SUMMARIZE verb: Fourth verb. text in -> condensed text out. Temp 0.
      Follows existing EXTRACT pattern. ~1 session. Tests included.
- [ ] Clean up verify graph idea: Strip to minimal JSON schema.
      Not a product yet — just a clean spec in a markdown file. Kill the
      overengineering. It's a JSON object with methods, times, and scores.

---

## Phase 1: Show the Work (Weeks 3-6)

Nobody knows this exists. Fix that. AI tools can help here — this is where
agents earn their keep for a solo founder.

### Content (you + AI assist)

- [ ] Write ONE blog post: "The GPU/CPU Boundary — Why Not Everything Should
      Go to an LLM." This is your best original insight. Post on:
      - Dev.to or Hashnode (SEO, dev audience)
      - r/Python, r/MachineLearning, r/LocalLLaMA (discussion)
      - LinkedIn (professional network)
      - X/Twitter (tag Karpathy thread, Wolf thread — you have the refs)
      Use Claude/Grok to draft, you edit for voice and authenticity.

- [ ] Record ONE demo video (2-3 min): .ai file -> run -> structured output.
      Screen recording, no production. Loom or OBS. Show the execution plan.
      Post on X, LinkedIn, YouTube.

- [ ] Write a Show HN post. Title: "Show HN: AI DSL — structured language
      for AI workflows (SQL for agents)". Link to GitHub. Short, honest
      description. Let HN decide if it's interesting.

### Community signals to watch

- GitHub stars (are people finding it?)
- Comments/replies on posts (what resonates?)
- DMs or emails (anyone reaching out?)
- Forks or issues (anyone trying to use it?)

If none of these move after Phase 1, the market is telling you something.
Listen to it.

### AI-assisted outreach (ethical, not spam)

- Use AI to find relevant conversations on X/Reddit about:
  "structured output" + "LLM", "agent frameworks" + "too complex",
  "prompt engineering" + "consistency problems"
- Reply genuinely with your perspective + link when relevant
- Don't spam. Add value or don't post.

---

## Phase 2: First Conversations (Weeks 7-10)

**Goal: 5 real conversations with people who have budget and a manual
workflow they hate.** This is from your own lessons_learned.md. Do it.

### Where to find them

- LinkedIn: Search for "AI automation", "document processing", "compliance
  automation" in titles. Connect. Ask what they struggle with.
- IndieHackers: Post in "What are you working on?" with honest status.
- Local meetups: AI/ML meetups in your area. Show the demo. Ask questions.
- Upwork/freelance: Search for AI workflow projects. Bid using the DSL as
  your internal tooling. Get paid to validate.

### What to learn from conversations

- What workflow do they do manually today?
- How much time/money does it cost them?
- Would they pay $200-400/hr for someone to automate it?
- Does the .ai file concept make sense to them?

### Vertical candidates (pick ONE to pursue)

| Vertical | Why | Risk |
|---|---|---|
| Support desk triage | Closest to current DSL | Crowded (Zendesk, Intercom) |
| Insurance/claims processing | Regulated, needs audit trails | Long sales cycles |
| Compliance monitoring (SEC, etc.) | High value, audit = differentiator | Enterprise only |
| Document extraction (invoices, receipts) | Obvious use case | Commoditized (Reducto etc.) |
| Consulting (AI workflow structuring) | Sell your skill, not the tool | Not scalable |

**Recommendation: Start with consulting. Get paid to learn what customers
actually need. Use the DSL as your internal accelerator. Let client needs
drive what gets built next.** This is what your lessons_learned.md already
concluded. Trust your own analysis.

---

## Phase 3: Build What's Pulled (Weeks 11+)

Only enter this phase if Phase 2 produced signal. Build what customers asked
for, not what AI tools suggested.

Likely candidates based on the vertical:
- STAGE + simple HITL (if support/compliance vertical)
- Pydantic output + verify graph metadata (if audit/regulated vertical)
- PDF/image ingestion (if document extraction vertical — PBI-PDF-IMAGE)
- Generated Python API (if developer adoption is the signal)

---

## What NOT to Do

- No more ideation sessions with AI tools until Phase 1 ships
- No robotics/BT/LTL work until a robotics customer exists
- No domain packs until the base language is adopted
- No skill registry until multiple users need to share skills
- No fleet hub until multiple deployments exist
- No Rust rewrite
- No formal verification (Lean/Coq)
- No device auto-discovery
- No app store

These are all good ideas filed in `future_state/`. They stay there.

---

## AI as Force Multiplier (What Tools CAN Do For You)

You asked if AI can help you market, build community, and sell. Yes, but
specifically:

| Task | How AI Helps | How It Doesn't |
|---|---|---|
| Blog post drafting | Draft from bullet points, you edit | Can't be your authentic voice |
| Social media posts | Generate variations, hashtags | Can't build real relationships |
| Demo script | Outline what to show | Can't record the video |
| Outreach research | Find relevant conversations | Can't replace genuine engagement |
| Code generation | Ship features faster | Can't decide what to build |
| Issue triage | Classify feedback | Can't talk to customers for you |
| Docs/README | Generate from code | Can't validate product-market fit |

**The one thing AI cannot do: tell you whether anyone will pay for this.**
Only humans can do that. Go talk to them.

---

## The Uncle Owen Test

> "Do you speak Bocce?"

The vision: every agent, robot, smart home, compliance system, and
autonomous vehicle speaks Bocce — a common structured language that bridges
English intent and machine execution. Domain packs extend the vocabulary.
The compiler produces verified, auditable execution plans. Non-engineers
write it. Engineers trust it.

That's a real vision. It's also a 10-year vision for a funded team.

For one guy right now, the test is simpler:

**Can you find ONE person who will pay you to solve their problem using
this tool?**

Everything else follows from that. The DSL is the engine, not the car.
Find someone who needs a ride.

---

## Files in This Repo

| File | Purpose |
|---|---|
| ROADMAP.md | This file. The plan. |
| CLAUDE.md | Dev conventions and architecture |
| CONCEPTS.md | Language vocabulary and design principles |
| AGENTS.md | Guidelines for AI-assisted development |
| TASKS.md | Sprint tasks and product backlog |
| lessons_learned.md | Market research and strategic notes |
| security_wip.md | Security model (5-layer defense) |
| future_state/ | Vision files from ideation sessions (parked) |

---

*Last updated: 2026-03-07*
*Status: Phase 0. Ship something. Talk to humans. Eat real food.*
