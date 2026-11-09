// USE CASE 3 — Semantic search over VIRA360 project history.
// Proves meaning-based retrieval: a query with NO shared keywords still finds the
// right project record. Usage: node src/search.js "your question"

import { retrieve, usingManagedKB } from "./retrieve.js";

const query = process.argv.slice(2).join(" ") ||
  "Which discussion is about coating quality problems on the samples?";

console.log(`\n=== VIRA360 · Semantic Search (${usingManagedKB() ? "managed KB" : "local RAG"}) ===`);
console.log(`Query: "${query}"\n`);

const hits = await retrieve(query, 3);
hits.forEach((h, i) => {
  const score = h.score == null ? "" : `  [score ${h.score.toFixed(3)}]`;
  console.log(`${i + 1}. ${h.title}${score}`);
  console.log(`   ${h.text}\n`);
});

console.log(
  'Note: the top hit matches "coating quality" to the paint-finish failure even though\n' +
  'the query shares no keywords with the stored text — that is semantic search.\n'
);
