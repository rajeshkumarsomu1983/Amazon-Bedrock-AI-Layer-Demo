// Shared configuration for the VIRA360 Bedrock demo.
// Everything is overridable via environment variables so you can point the demo
// at the right Region, models, and (optionally) a managed Bedrock Knowledge Base.

export const REGION = process.env.AWS_REGION || "us-east-1";

// Geography-scoped cross-region inference profile (NOT a global profile) — matters
// for VIRA360's US + China footprint if any data-residency rule applies.
export const TEXT_MODEL_ID =
  process.env.BEDROCK_TEXT_MODEL || "us.anthropic.claude-sonnet-4-5-20250929-v1:0";

// A cheaper/faster model for high-volume features (classification, smart replies).
export const FAST_MODEL_ID =
  process.env.BEDROCK_FAST_MODEL || "us.anthropic.claude-haiku-4-5-20251001-v1:0";

// Titan embeddings for the local fallback RAG path.
export const EMBED_MODEL_ID =
  process.env.BEDROCK_EMBED_MODEL || "amazon.titan-embed-text-v2:0";

// If set, the assistant/search use a MANAGED Bedrock Knowledge Base (RetrieveAndGenerate).
// If empty, they fall back to local Titan-embedding RAG over src/data/project-docs.js.
export const KB_ID = process.env.KB_ID || "";

// Model ARN the managed KB uses to generate the grounded answer.
export const KB_MODEL_ARN =
  process.env.KB_MODEL_ARN ||
  `arn:aws:bedrock:${REGION}:${process.env.AWS_ACCOUNT_ID || "<ACCOUNT_ID>"}:inference-profile/${TEXT_MODEL_ID}`;
