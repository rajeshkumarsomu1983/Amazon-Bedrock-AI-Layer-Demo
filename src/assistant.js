// USE CASE 4 — Context-grounded assistant (RAG).
// Answers ONLY from VIRA360's own project records — retrieve, then generate.
// Managed-KB mode uses RetrieveAndGenerate (one call); local mode retrieves then
// calls Converse with the retrieved passages as grounding context.
// Usage: node src/assistant.js "your question"

import {
  BedrockAgentRuntimeClient,
  RetrieveAndGenerateCommand,
} from "@aws-sdk/client-bedrock-agent-runtime";
import { retrieve, usingManagedKB } from "./retrieve.js";
import { converse } from "./bedrock.js";
import { REGION, KB_ID, KB_MODEL_ARN, TEXT_MODEL_ID } from "./config.js";

const query = process.argv.slice(2).join(" ") ||
  "Write a short status update for the client's Monday board meeting. Flag anything that still needs approval.";

console.log(`\n=== VIRA360 · Grounded Assistant (${usingManagedKB() ? "managed KB" : "local RAG"}) ===`);
console.log(`Question: "${query}"\n`);

if (KB_ID) {
  // Managed path: Bedrock retrieves + generates a cited answer in one call.
  const client = new BedrockAgentRuntimeClient({ region: REGION });
  const res = await client.send(
    new RetrieveAndGenerateCommand({
      input: { text: query },
      retrieveAndGenerateConfiguration: {
        type: "KNOWLEDGE_BASE",
        knowledgeBaseConfiguration: { knowledgeBaseId: KB_ID, modelArn: KB_MODEL_ARN },
      },
    })
  );
  console.log(res.output.text, "\n");
  const cites = res.citations?.flatMap((c) => c.retrievedReferences || []) || [];
  if (cites.length) {
    console.log("Grounded in:");
    cites.forEach((r) => console.log(`  - ${r.location?.s3Location?.uri || "kb-passage"}`));
    console.log("");
  }
} else {
  // Local path: retrieve passages, then generate grounded strictly in them.
  const hits = await retrieve(query, 4);
  const context = hits.map((h, i) => `[${i + 1}] ${h.title}: ${h.text}`).join("\n");
  const prompt = `You are the VIRA360 in-app assistant. Answer the user's request using ONLY the
project records below. If the records do not contain the answer, say so. Be concise.

PROJECT RECORDS:
${context}

USER REQUEST: ${query}`;
  const out = await converse(TEXT_MODEL_ID, prompt, { maxTokens: 500 });
  console.log(out, "\n");
  console.log("Grounded in:");
  hits.forEach((h) => console.log(`  - ${h.title}`));
  console.log("");
}
