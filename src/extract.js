// USE CASE 2 — Action-item extraction (the Basecamp/Salesforce task-capture replacement).
// Produces structured JSON ready to write straight into Aurora as VIRA360 tasks.

import { converse } from "./bedrock.js";
import { TEXT_MODEL_ID } from "./config.js";
import { thread } from "./data/project-docs.js";

const prompt = `Extract every action item from this VIRA360 project thread as JSON.
Schema: [{ "task": string, "owner": string|null, "due": string|null, "needs_approval": boolean }]
If a field is unknown, use null. Return ONLY the JSON array, no prose.

THREAD:
${thread}`;

const out = await converse(TEXT_MODEL_ID, prompt, { maxTokens: 600, temperature: 0 });

console.log("\n=== VIRA360 · Extracted Action Items ===\n");
// Validate it parses so the demo fails loudly rather than showing malformed JSON.
try {
  const cleaned = out.replace(/^```json\s*/i, "").replace(/```$/i, "").trim();
  const items = JSON.parse(cleaned);
  console.log(JSON.stringify(items, null, 2));
  console.log(`\n${items.length} action items — ready to INSERT into the VIRA360 tasks table.\n`);
} catch {
  console.log(out);
  console.log("\n(Model returned non-JSON; shown raw above.)\n");
}
