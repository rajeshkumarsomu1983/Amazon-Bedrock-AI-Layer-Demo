"""Core tool logic shared by the Lambda (Gateway target) and the local fallback tools."""
import json
import os
import re
from pathlib import Path

import boto3

from .prompts import ASSISTANT_PROMPT, EXTRACT_PROMPT, SUMMARIZE_PROMPT  # noqa: F401

REGION = os.environ.get("AWS_REGION", "us-east-1")
KB_ID = os.environ.get("KB_ID", "<KB_ID>")
TEXT_MODEL_ID = os.environ.get("TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "123456789012")
KB_MODEL_ARN = os.environ.get(
    "KB_MODEL_ARN", f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:inference-profile/{TEXT_MODEL_ID}"
)
DOCS_BUCKET = os.environ.get("DOCS_BUCKET", "vira360-demo-kb-123456789012")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_clients = {}


def _client(name):
    if name not in _clients:
        _clients[name] = boto3.client(name, region_name=REGION)
    return _clients[name]


def load_project_text(project_id: str) -> str:
    """'thread' (or empty) -> demo thread; 'proj-*' -> bundled record, S3 docs/<id>.txt fallback."""
    pid = (project_id or "thread").strip()
    if pid == "thread":
        return (DATA_DIR / "thread.txt").read_text().strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", pid):
        raise ValueError(f"invalid project_id: {pid!r}")
    p = DATA_DIR / "docs" / f"{pid}.txt"
    if p.exists():
        return p.read_text().strip()
    try:
        obj = _client("s3").get_object(Bucket=DOCS_BUCKET, Key=f"docs/{pid}.txt")
        return obj["Body"].read().decode("utf-8").strip()
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"unknown project_id: {pid}") from e


def converse(prompt: str, max_tokens: int, temperature: float = 0.2) -> str:
    res = _client("bedrock-runtime").converse(
        modelId=TEXT_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return "".join(b.get("text", "") for b in res["output"]["message"]["content"]).strip()


def search_projects(query: str, k: int = 4) -> dict:
    res = _client("bedrock-agent-runtime").retrieve(
        knowledgeBaseId=KB_ID,
        retrievalQuery={"text": query},
        retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": int(k)}},
    )
    return {
        "results": [
            {
                "source": r.get("location", {}).get("s3Location", {}).get("uri", "kb-passage"),
                "score": round(r.get("score", 0.0), 4),
                "text": r.get("content", {}).get("text", ""),
            }
            for r in res.get("retrievalResults", [])
        ]
    }


def ask_projects(question: str) -> dict:
    res = _client("bedrock-agent-runtime").retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {"knowledgeBaseId": KB_ID, "modelArn": KB_MODEL_ARN},
        },
    )
    sources = []
    for c in res.get("citations", []):
        for r in c.get("retrievedReferences", []):
            uri = r.get("location", {}).get("s3Location", {}).get("uri", "kb-passage")
            if uri not in sources:
                sources.append(uri)
    return {"answer": res["output"]["text"], "citations": sources}


def summarize_project(project_id: str = "thread") -> dict:
    text = load_project_text(project_id)
    return {
        "project_id": project_id or "thread",
        "summary": converse(SUMMARIZE_PROMPT.format(thread=text), 400),
    }


def extract_action_items(project_id: str = "thread") -> dict:
    text = load_project_text(project_id)
    out = converse(EXTRACT_PROMPT.format(thread=text), 600, temperature=0)
    cleaned = re.sub(r"^```json\s*", "", out, flags=re.I)
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return {"project_id": project_id or "thread", "action_items": json.loads(cleaned), "parsed": True}
    except json.JSONDecodeError:
        return {"project_id": project_id or "thread", "raw": out, "parsed": False}


TOOLS = {
    "search_projects": search_projects,
    "ask_projects": ask_projects,
    "summarize_project": summarize_project,
    "extract_action_items": extract_action_items,
}
