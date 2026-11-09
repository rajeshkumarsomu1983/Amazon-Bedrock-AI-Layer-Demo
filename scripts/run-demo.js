// One-shot demo runner — executes all four use cases in sequence with headers,
// so you can run the entire story with a single `npm run demo` as a backup to
// clicking through the console live.

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { existsSync } from "node:fs";
import { KB_ID } from "../src/config.js";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "..", "src");

function run(label, file, args = []) {
  console.log("\n" + "=".repeat(70));
  console.log(label);
  console.log("=".repeat(70));
  const r = spawnSync("node", [join(src, file), ...args], { stdio: "inherit" });
  if (r.status !== 0) console.log(`(step "${label}" exited with code ${r.status})`);
}

console.log("\nVIRA360 · Amazon Bedrock AI-layer demo");
console.log(KB_ID ? `Mode: managed Knowledge Base (${KB_ID})` : "Mode: local fallback RAG");

run("1/4  Thread summarization", "summarize.js");
run("2/4  Action-item extraction (Basecamp/Salesforce replacement)", "extract.js");

// Steps 3-4 need a retrieval index. In local mode, build it first if missing.
if (!KB_ID && !existsSync(join(src, "data", "embeddings.json"))) {
  run("prep  Building local RAG index", "ingest.js");
}

run("3/4  Semantic search over project history", "search.js",
  ["Which discussion is about coating quality problems on the samples?"]);
run("4/4  Grounded assistant (client status update)", "assistant.js",
  ["Write a short status update for the client's Monday board meeting. Flag anything that still needs approval."]);

console.log("\nDemo complete.\n");
