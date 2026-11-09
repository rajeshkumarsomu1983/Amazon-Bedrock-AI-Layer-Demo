// Writes the seeded VIRA360 project docs to ./kb-corpus/*.txt so you can upload them
// to S3 as the managed Knowledge Base data source. Run: node scripts/export-docs.js

import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { docs } from "../src/data/project-docs.js";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, "..", "kb-corpus");
mkdirSync(outDir, { recursive: true });

for (const d of docs) {
  const file = join(outDir, `${d.id}.txt`);
  writeFileSync(file, `${d.title}\n\n${d.text}\n`);
  console.log(`wrote ${file}`);
}
console.log(`\n${docs.length} docs written to ${outDir}`);
console.log("Upload this folder to your KB's S3 bucket, then Sync the data source.\n");
