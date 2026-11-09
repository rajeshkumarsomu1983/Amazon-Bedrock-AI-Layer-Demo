// Thin wrappers over the Bedrock Runtime so every demo script shares one code path.
// In production this logic lives server-side in the BFF / realtime-gateway and
// talks to Bedrock over a VPC endpoint (PrivateLink).

import {
  BedrockRuntimeClient,
  ConverseCommand,
  InvokeModelCommand,
} from "@aws-sdk/client-bedrock-runtime";
import { REGION, EMBED_MODEL_ID } from "./config.js";

const client = new BedrockRuntimeClient({ region: REGION });

/**
 * One API across Claude / Nova / Llama / Titan. Swap modelId, nothing else changes.
 */
export async function converse(modelId, prompt, { maxTokens = 512, temperature = 0.2 } = {}) {
  const res = await client.send(
    new ConverseCommand({
      modelId,
      messages: [{ role: "user", content: [{ text: prompt }] }],
      inferenceConfig: { maxTokens, temperature },
    })
  );
  return res.output.message.content[0].text.trim();
}

/** Titan text embedding — used by the local fallback RAG path. */
export async function embed(text) {
  const res = await client.send(
    new InvokeModelCommand({
      modelId: EMBED_MODEL_ID,
      contentType: "application/json",
      accept: "application/json",
      body: JSON.stringify({ inputText: text }),
    })
  );
  const parsed = JSON.parse(new TextDecoder().decode(res.body));
  return parsed.embedding;
}

export function cosineSimilarity(a, b) {
  let dot = 0;
  let na = 0;
  let nb = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    na += a[i] * a[i];
    nb += b[i] * b[i];
  }
  return dot / (Math.sqrt(na) * Math.sqrt(nb));
}
