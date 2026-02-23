from aidsl import skill, stage, field, api, compute, rule, hitl

# -----------------------------
# Domain Objects
# -----------------------------

ticket = {
    "id": field.text,
    "customer_id": field.text,
    "subject": field.text,
    "body": field.text,
    "channel": field.one_of("email", "chat", "web"),
    "created_at": field.datetime
}

ticket_analysis = {
    "ticket_id": field.text,
    "summary": field.text,
    "severity": field.number,
    "category": field.one_of("billing", "technical", "account", "other"),
    "requires_human": field.boolean
}

customer_profile = {
    "id": field.text,
    "name": field.text,
    "tier": field.one_of("free", "standard", "premium"),
    "open_balance": field.money,
    "risk_score": field.number
}

# -----------------------------
# API
# -----------------------------

customer_api = api(
    base="https://api.example.com/customers",
    auth="env:API_KEY"
)

# -----------------------------
# Stages
# -----------------------------

fetch_customer_profile = (
    stage("fetch_customer_profile")
    .call(customer_api.get("/profile/{ticket.customer_id}"))
    .expect(customer_profile)
)

summarize_ticket = (
    stage("summarize_ticket")
    .extract("summary")
    .from_("ticket")
    .prefer("text_summarizer")
    .fallback("ticket_summarization")
)

classify_ticket = (
    stage("classify_ticket")
    .extract(ticket_analysis)
    .from_("ticket", "summarize_ticket.summary", "fetch_customer_profile")
    .prompt("ticket_classification")
    .examples("ticket_classification_examples")
)

draft_reply = (
    stage("draft_reply")
    .draft("reply")
    .from_("ticket", "ticket_analysis", "fetch_customer_profile")
    .prompt("ticket_reply_generation")
    .route_if("ticket_analysis.requires_human")
        .wait_for(hitl("review_ticket"))
        .use("human_edited_reply")
    .otherwise()
        .use("reply")
)

# -----------------------------
# Rules
# -----------------------------

rules = [
    rule("ticket_analysis.severity > 7").set("ticket_analysis.requires_human", True),
    rule("ticket_analysis.category == 'billing' and fetch_customer_profile.open_balance > 500")
        .set("ticket_analysis.requires_human", True),
    rule("fetch_customer_profile.tier == 'premium'")
        .set("ticket_analysis.requires_human", True)
]

# -----------------------------
# Skill
# -----------------------------

support_triage = (
    skill("support_triage")
    .run(fetch_customer_profile)
    .run(summarize_ticket)
    .run(classify_ticket)
    .run(draft_reply)
    .rules(rules)
    .output("results/support_triage.json")
    .compute(
        compute.default("cpu"),
        compute.gpu_for("classify_ticket"),
        compute.max_cost(2.00)
    )
    .audit(
        plan="logs/plan.json",
        stages="logs/stages.json",
        models="logs/models.json",
        api="logs/api.json",
        hitl="logs/hitl.json"
    )
)
