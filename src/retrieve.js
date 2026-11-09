// Shared retrieval layer. Picks the managed Bedrock Knowledge Base when KB_ID is set,
// otherwise falls back to the local Titan-embedding index built by ingest.js.
// This is what lets the demo run as FULL managed RAG or with zero infra setup.

import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import {
  BedrockAgentRuntimeClient,
  RetrieveCommand,
} from "@aws-sdk/client-bedrock-agent-runtime";
import { embed, cosineSimilarity } from "./bedrock.js";
import { REGION, KB_ID } from "./config.js";

const here = dirname(fileURLToPath(import.meta.url));
const indexPath = join(here, "data", "embeddings.json");

export function usingManagedKB() {
  return Boolean(KB_ID);
}

/**
 * Returns top-k passages for a query as [{ title, text, score }].
 * Managed KB path uses Bedrock Retrieve; local path uses cosine over Titan vectors.
 */
export async function retrieve(query, k = 3) {
  if (KB_ID) {
    const client = new BedrockAgentRuntimeClient({ region: REGION });
    const res = await client.send(
      new RetrieveCommand({
        knowledgeBaseId: KB_ID,
        retrievalQuery: { text: query },
        retrievalConfiguration: {
          vectorSearchConfiguration: { numberOfResults: k },
        },
      })
    );
    return (res.retrievalResults || []).map((r) => ({
      title: r.location?.s3Location?.uri || "kb-passage",
      text: r.content?.text || "",
      score: r.score ?? null,
    }));
  }

  if (!existsSync(indexPath)) {
    throw new Error(
      "No local RAG index found. Run `npm run ingest` first, or set KB_ID to use a managed Knowledge Base."
    );
  }
  const index = JSON.parse(readFileSync(indexPath, "utf8"));
  const qv = await embed(query);
  return index
    .map((d) => ({ title: d.title, text: d.text, score: cosineSimilarity(qv, d.vector) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}
