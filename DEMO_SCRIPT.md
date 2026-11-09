# VIRA360 Bedrock Demo — Minute-by-Minute Script (~15 min)

**Setup before you present (day before):**
1. `npm install`, `export AWS_REGION=us-east-1`, `npm run check` → all PASS.
2. Stand up the managed Knowledge Base (`KNOWLEDGE_BASE_SETUP.md`) and `export KB_ID=…`.
   - If you're short on time, skip the KB and run `npm run ingest` for local RAG — the story is identical.
3. Do ONE full `npm run demo` dry run so there are no surprises live.

Have two things on screen: the **Bedrock console** (for the visual "this is a managed service"
moment) and a **terminal** in this repo (for the running features).

---

### 0 · Frame (1 min)
> "VIRA360 already captures everything the US and China teams say and do — threads, tasks, specs.
> Today I'll show four things Bedrock adds as the platform's **AI layer**: it summarizes, it turns
> conversation into tasks, it searches by meaning, and it answers questions from your own project
> records. Same server-side call pattern for all four — exactly how it'd sit behind your BFF."

### 1 · Thread summarization (2–3 min)
- Terminal: `npm run summarize`
- Show the 3-bullet brief of the fixture-project thread.
> "A lead who missed this thread gets the state of play in three bullets. That's one status
> meeting you don't hold. One Converse API call from the gateway."

### 2 · Action-item extraction — the Basecamp/Salesforce replacement (3 min)
- Terminal: `npm run extract`
- Show the structured JSON (task / owner / due / needs_approval).
> "Same thread, different prompt — now it's structured JSON. This writes straight into Aurora as
> VIRA360 tasks. This is your task capture, automated from the conversation. This is where you
> start replacing manual Basecamp/Salesforce entry."

### 3 · Semantic search (3 min)
- Terminal: `npm run search "coating quality problems on the samples"`
- Point at the top hit: the **paint-finish failure** record — which never says "coating quality."
> "Keyword search finds the word you typed. Semantic search finds the discussion you *meant*,
> across every project VIRA360 has stored. This is running against a managed Bedrock Knowledge
> Base" (or "a Titan-embedding index" in local mode).
- Console beat: open **Bedrock → Knowledge Bases → your KB** so they see it's a managed service, not a science project.

### 4 · Grounded assistant (3 min)
- Terminal: `npm run assistant "Write a short status update for the client's Monday board meeting. Flag anything that still needs approval."`
- Show the generated status update + the "Grounded in:" record list.
> "This is the in-app assistant. It answered **only** from your project records — notice the
> sources it used. That grounding via a Knowledge Base is what makes it trustworthy enough to
> ship: it can't make things up about your projects."

### 5 · Governance (2 min, console)
- Console: **Bedrock → Guardrails** — show Sensitive information filters (PII) + content filters.
> "Before any message reaches the model, a Guardrail redacts PII and filters content. This is
> your enforcement point for the data-handling requirements NorthBay raised — and invocation
> logging to S3/CloudWatch gives you the audit trail."

### 6 · Close (1 min)
> "Four features, one API, all server-side behind your gateway over a private endpoint — governed
> by Guardrails, grounded by a Knowledge Base, cached in Valkey. I'd start with **action-item
> extraction**: it's the most visible win and the clearest step in replacing Basecamp/Salesforce.
> Let's scope a short build on your real thread data."

---

**If something fails live:** fall back to `npm run demo` (runs all four in sequence), or the
screenshots you captured during the dry run. Never debug credentials in front of the customer —
that's what `npm run check` the day before is for.
