# VIRA360 · Amazon Bedrock AI-Layer Demo

A small, runnable repo that shows how **Amazon Bedrock powers the AI layer** of the VIRA360
collaboration / project-management platform. Four standalone use cases, all calling Bedrock
the same server-side way the VIRA360 BFF / realtime-gateway would (over a VPC endpoint in prod):

| Script | Use case | Bedrock surface |
|---|---|---|
| `npm run summarize` | Summarize a long project thread into a 3-bullet brief | Converse API |
| `npm run extract` | Pull structured action items (owner/due/approval) as JSON | Converse API |
| `npm run search` | Semantic search over project history (by meaning) | Retrieve (KB) **or** Titan embeddings |
| `npm run assistant` | Grounded assistant — answers only from project records | RetrieveAndGenerate (KB) **or** local RAG |

The retrieval use cases run against a **managed Bedrock Knowledge Base** when `KB_ID` is set
(recommended for the demo — see `KNOWLEDGE_BASE_SETUP.md`), or a **local Titan-embedding
fallback** with zero infra when it isn't.

> This is demo/enablement code, not production code: credentials come from the default AWS
> chain, retrieval context is seeded, and there's no auth/rate-limiting. The *call patterns*
> (Converse, Retrieve, RetrieveAndGenerate, Guardrails) are the real production shapes.

## Prerequisites
- Node.js 18+ (uses built-in `fetch`/ESM; no build step).
- AWS credentials in your shell (`aws sso login` / `aws configure`) with Bedrock access.
- **Bedrock model access** granted in your demo Region for: Claude Sonnet 4.5, Claude Haiku 4.5,
  and Titan Text Embeddings V2. (Bedrock console → Model access.)

## Quick start
```bash
npm install
export AWS_REGION=us-east-1          # pick ONE Region, stay in it

npm run check                        # pre-flight: verifies model access + creds

# Use cases 1 & 2 (no setup):
npm run summarize
npm run extract

# Use cases 3 & 4 — pick a mode:
#  (A) managed KB  — see KNOWLEDGE_BASE_SETUP.md, then: export KB_ID=XXXX
#  (B) local RAG   — npm run ingest   (embeds seed docs once)
npm run search     "coating quality problems on the samples"
npm run assistant  "status update for the client's Monday board meeting"

# Or run the whole story end-to-end:
npm run demo
```

## Configuration (env vars)
| Var | Default | Purpose |
|---|---|---|
| `AWS_REGION` | `us-east-1` | Demo Region |
| `BEDROCK_TEXT_MODEL` | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` | Summaries, extraction, assistant |
| `BEDROCK_FAST_MODEL` | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | High-volume features |
| `BEDROCK_EMBED_MODEL` | `amazon.titan-embed-text-v2:0` | Local RAG embeddings |
| `KB_ID` | _(empty)_ | Set to use a managed Knowledge Base instead of local RAG |
| `KB_MODEL_ARN` | Claude 3.5 Sonnet ARN | Model the managed KB uses to generate |

Model IDs default to **geography-scoped** (`us.`) cross-region inference profiles — keep them
geography-scoped if any data-residency rule applies (relevant for VIRA360's US + China footprint).
China Regions are a separate partition; model availability there is its own conversation.

## How this maps to the VIRA360 architecture
- **Invocation**: all Bedrock calls are server-side (as in `src/bedrock.js` / `src/retrieve.js`) —
  in production these live in the NestJS BFF / realtime-gateway, reached over a Bedrock VPC
  endpoint (PrivateLink). No browser-side model calls.
- **Data**: Aurora Postgres holds project/chat text; a vector store (Aurora pgvector or the KB's
  OpenSearch Serverless) holds embeddings; Valkey caches responses/embeddings.
- **Governance**: add a Bedrock **Guardrail** (PII redaction + content filters) on the Converse
  calls — the enforcement point for the NorthBay / PIPL data-handling requirements.

## AgentCore agent (Runtime + Gateway + Memory)

The same four capabilities (summarize, extract action items, semantic search, grounded Q&A) are also packaged as a
Python Strands agent on Amazon Bedrock AgentCore: tools are served by an AgentCore Gateway (MCP, IAM auth, Lambda target),
conversation context is kept in AgentCore Memory, and the agent runs on AgentCore Runtime (Claude Sonnet 4.5).

```bash
npm run agent -- "Which discussion is about coating quality problems on the samples?"
npm run agent -- "What is the status of the end-cap hardware material decision?" --session-id my-demo-session-0000000000000001
npm run agent -- "Who needs to approve that, and by when?" --session-id my-demo-session-0000000000000001   # memory resolves "that"
```

Needs `AWS_PROFILE`/credentials for account 123456789012 and the gitignored `agent/config.local.json` (or `AGENT_RUNTIME_ARN`).
Details: `agent/README.md`; created resources: `agent/RESOURCES.md`; cleanup: `agent/teardown.py`.

## Files
```
src/config.js            # Region, model IDs, KB settings (env-overridable)
src/bedrock.js           # Converse + Titan embed + cosine helpers
src/retrieve.js          # managed-KB-or-local retrieval switch
src/summarize.js         # use case 1
src/extract.js           # use case 2
src/search.js            # use case 3
src/assistant.js         # use case 4
src/ingest.js            # build local RAG index (Titan)
src/data/project-docs.js # seeded VIRA360 thread + project corpus
scripts/check-access.js  # pre-flight
scripts/run-demo.js      # run all four in sequence
scripts/export-docs.js   # export corpus to ./kb-corpus for S3 upload
agent/                   # AgentCore agent (Runtime/Gateway/Memory) - see agent/README.md
KNOWLEDGE_BASE_SETUP.md  # stand up the managed KB
DEMO_SCRIPT.md           # minute-by-minute talk track
```
