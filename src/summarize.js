// USE CASE 1 — Project thread summarization.
// Turns a long VIRA360 project thread into a 3-bullet brief for a lead who missed it.

import { converse } from "./bedrock.js";
import { TEXT_MODEL_ID } from "./config.js";
import { thread } from "./data/project-docs.js";

const prompt = `You are the AI assistant inside VIRA360, a project-management platform for a
retail-fixture manufacturer. Summarize this project thread in exactly 3 bullets for a
project lead who missed the conversation. Be factual and specific — names, numbers, dates.

THREAD:
${thread}`;

const out = await converse(TEXT_MODEL_ID, prompt, { maxTokens: 400 });
console.log("\n=== VIRA360 · Thread Summary ===\n");
console.log(out);
console.log("");
