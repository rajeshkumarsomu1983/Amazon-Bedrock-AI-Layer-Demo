// Pre-flight: confirm Bedrock model access + credentials in your demo Region BEFORE
// you present. Run: npm run check

import { converse, embed } from "../src/bedrock.js";
import { REGION, TEXT_MODEL_ID, EMBED_MODEL_ID, KB_ID } from "../src/config.js";

console.log(`\nVIRA360 Bedrock demo — pre-flight check`);
console.log(`Region:      ${REGION}`);
console.log(`Text model:  ${TEXT_MODEL_ID}`);
console.log(`Embed model: ${EMBED_MODEL_ID}`);
console.log(`KB mode:     ${KB_ID ? `managed (KB_ID=${KB_ID})` : "local fallback RAG"}\n`);

let ok = true;

try {
  const out = await converse(TEXT_MODEL_ID, "Reply with exactly: OK", { maxTokens: 10 });
  console.log(`[PASS] Converse / text model reachable -> "${out}"`);
} catch (e) {
  ok = false;
  console.log(`[FAIL] Text model: ${e.name} — ${e.message}`);
  console.log("       Fix: Bedrock console -> Model access -> enable the model in this Region.");
}

if (!KB_ID) {
  try {
    const v = await embed("connectivity test");
    console.log(`[PASS] Titan embeddings reachable -> ${v.length}-dim vector`);
  } catch (e) {
    ok = false;
    console.log(`[FAIL] Embeddings: ${e.name} — ${e.message}`);
    console.log("       Fix: enable the Titan embeddings model, or set KB_ID to use a managed KB.");
  }
}

console.log(ok ? "\nAll checks passed — you are demo-ready.\n" : "\nResolve the failures above before presenting.\n");
process.exit(ok ? 0 : 1);
