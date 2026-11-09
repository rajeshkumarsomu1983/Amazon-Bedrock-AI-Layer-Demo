# Setting up the managed Bedrock Knowledge Base (RAG)

The demo runs in **two modes**:

- **Local fallback RAG** (zero infra): `npm run ingest` embeds the seeded project docs with
  Titan and searches them in-memory. Good enough to tell the whole story if you don't want
  to stand anything up. This is the default when `KB_ID` is unset.
- **Managed Knowledge Base** (the real production shape): set `KB_ID` and the demo uses the
  Bedrock `Retrieve` and `RetrieveAndGenerate` APIs. **This is the recommended way to present**,
  because it's exactly what VIRA360 would wire into the BFF.

Pre-build the managed KB once, the day before, so Steps 3–4 run as true managed RAG.

## Option A — Console (fastest, ~10 min)

1. Put the seed corpus in S3:
   - Create a bucket, e.g. `vira360-demo-kb-<acct>`.
   - Upload the 6 project records. Easiest: run `node scripts/export-docs.js` to write them to
     `./kb-corpus/*.txt`, then upload that folder to the bucket.
2. **Bedrock console → Knowledge Bases → Create**:
   - Data source: the S3 bucket/prefix above.
   - Embeddings model: **Titan Text Embeddings V2**.
   - Vector store: **Quick create (Amazon OpenSearch Serverless)** — Bedrock provisions it for you.
3. After it's created, open the KB and click **Sync** on the data source.
4. Copy the **Knowledge base ID** and export it:
   ```bash
   export KB_ID=XXXXXXXXXX
   export AWS_REGION=us-east-1
   ```
5. `npm run check` → should report `KB mode: managed`. Then `npm run search` / `npm run assistant`
   hit the managed KB.

## Option A2 — Script (S3 Vectors, no OpenSearch cost floor)

```bash
node scripts/export-docs.js
python3 scripts/create-kb.py        # prints KB_ID
export KB_ID=<printed id>
export AWS_ACCOUNT_ID=<your account id>   # Sonnet 4.5 needs an inference-profile ARN
```

## Option B — Keep it local (no KB)

```bash
export AWS_REGION=us-east-1
npm run ingest     # builds src/data/embeddings.json with Titan
npm run search
npm run assistant
```

## Notes
- **Region**: use ONE Region for the whole demo and confirm model access there first (`npm run check`).
- **Residency**: the model IDs default to geography-scoped `us.` inference profiles. If a
  residency rule applies (relevant for the US + China footprint), keep it geography-scoped —
  do not switch to a `global.` profile.
- **Cost**: OpenSearch Serverless for the KB has an hourly floor while it exists. If this is a
  throwaway demo, tear the KB + collection down afterward, or just use local mode.
