// Local fallback RAG — embeds the seeded VIRA360 project docs with Titan and caches
// the vectors to disk. Run once before `search`/`assistant` when NOT using a managed KB.
// (With a managed Bedrock Knowledge Base set via KB_ID, you do NOT need this.)

import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { embed } from "./bedrock.js";
import { docs } from "./data/project-docs.js";

const here = dirname(fileURLToPath(import.meta.url));
const outPath = join(here, "data", "embeddings.json");

console.log(`Embedding ${docs.length} VIRA360 project docs with Titan...`);
const indexed = [];
for (const d of docs) {
  const vector = await embed(`${d.title}\n${d.text}`);
  indexed.push({ ...d, vector });
  console.log(`  embedded ${d.id} (${vector.length}-dim)`);
}

writeFileSync(outPath, JSON.stringify(indexed));
console.log(`\nWrote ${indexed.length} vectors to ${outPath}`);
console.log("Local RAG index ready. Now run: npm run search  /  npm run assistant\n");
