spec opportunity_pipeline@v1
  parent none
  author "david@local"
  goal "rank today's postings so David sees the 5 worth his time by 9:15am"
  budget tokens 10000 human_minutes 15

knowledge:
  boards @ "fs://examples/ir/postings.jsonl"
  exclusion_rules @ "kv://exclusion-rules"

effects: model.complete, human.review
deny: action.execute

type posting = { title: text, pay: text, employer: text, url: text }
type scored = { title: text, pay: text, employer: text, url: text, score: float, excluded: bool }
type draft = { to: text, subject: text, body: text }

op fetch_boards() -> posting[] effect recorded cap fs.read
op classify_posting(posting) -> scored effect external cap model.complete using prompt "job_fit_v1"
op draft_outreach(scored) -> draft effect external cap model.complete using prompt "outreach_v1"
op send_outreach(draft) -> receipt effect external cap action.execute gate approval

gate approval:
  human decides in [approve, edit, reject]

audit budget_tokens: tokens_used <= 10000 -> suspend

plan daily_scan:
  p = fetch_boards()
  s = classify_posting(p)
  d = draft_outreach(s) when s.score > 0.7 and not s.excluded
  r = send_outreach(d)
