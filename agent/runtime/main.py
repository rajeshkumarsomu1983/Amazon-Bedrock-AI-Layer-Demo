"""VIRA360 AgentCore Runtime entrypoint: Strands agent + Gateway (MCP) tools + AgentCore Memory."""
import json
import logging
import os
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Deployed zip: common/ and data/ sit next to main.py. Local checkout: they sit in agent/.
for p in (HERE, HERE.parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

# Local runs: fall back to the gitignored config written by infra scripts (not shipped in the zip).
_local_cfg = HERE.parent / "config.local.json"
if _local_cfg.exists():
    _c = json.loads(_local_cfg.read_text())
    for env, key in (("MEMORY_ID", "memory_id"), ("GATEWAY_URL", "gateway_url")):
        if key in _c:
            os.environ.setdefault(env, _c[key])
    if "memory_strategies" in _c:
        os.environ.setdefault("MEMORY_STRATEGY_IDS", json.dumps([x["id"] for x in _c["memory_strategies"]]))

from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig  # noqa: E402
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager  # noqa: E402
from bedrock_agentcore.runtime import BedrockAgentCoreApp  # noqa: E402
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client  # noqa: E402
from strands import Agent  # noqa: E402
from strands.models import BedrockModel  # noqa: E402
from strands.tools.mcp import MCPClient  # noqa: E402

from common.prompts import AGENT_SYSTEM_PROMPT  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vira360")

REGION = os.environ.get("AWS_REGION", "us-east-1")
TEXT_MODEL_ID = os.environ.get("TEXT_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
MEMORY_ID = os.environ.get("MEMORY_ID", "")
GATEWAY_URL = os.environ.get("GATEWAY_URL", "")
TOOL_MODE = os.environ.get("TOOL_MODE", "gateway")  # gateway | local | auto
DEFAULT_ACTOR = "vira360-demo-user"

assert not TEXT_MODEL_ID.startswith("global."), "global. inference profiles are not allowed"

app = BedrockAgentCoreApp()


def _gateway_client() -> MCPClient:
    return MCPClient(lambda: aws_iam_streamablehttp_client(GATEWAY_URL, aws_service="bedrock-agentcore", aws_region=REGION))


def _list_all_tools(client: MCPClient):
    tools, token = [], None
    while True:
        page = client.list_tools_sync(pagination_token=token)
        tools.extend(page)
        token = getattr(page, "pagination_token", None)
        if not token:
            return tools


def _session_manager(session_id: str, actor_id: str):
    if not MEMORY_ID:
        return None
    retrieval = {}
    for s in json.loads(os.environ.get("MEMORY_STRATEGY_IDS", "[]")):
        retrieval[f"/strategy/{s}/actor/{{actorId}}/"] = RetrievalConfig(top_k=5, relevance_score=0.3, strategy_id=s)
    cfg = AgentCoreMemoryConfig(memory_id=MEMORY_ID, session_id=session_id, actor_id=actor_id,
                                retrieval_config=retrieval or None)
    return AgentCoreMemorySessionManager(cfg, region_name=REGION)


def _run(prompt: str, session_id: str, actor_id: str, tools, tool_source: str) -> dict:
    agent = Agent(
        model=BedrockModel(model_id=TEXT_MODEL_ID, region_name=REGION),
        system_prompt=AGENT_SYSTEM_PROMPT,
        tools=tools,
        session_manager=_session_manager(session_id, actor_id),
        callback_handler=None,
    )
    result = agent(prompt)
    used = list(getattr(result.metrics, "tool_metrics", {}).keys())
    return {"result": str(result), "session_id": session_id, "actor_id": actor_id, "tool_source": tool_source,
            "tools_called": used, "memory_enabled": bool(MEMORY_ID), "model": TEXT_MODEL_ID}


def handle(payload: dict, session_id: str | None = None) -> dict:
    prompt = payload.get("prompt") or payload.get("input") or ""
    if not prompt:
        return {"error": "payload must include 'prompt'"}
    session_id = payload.get("session_id") or session_id or f"session-{uuid.uuid4()}"
    actor_id = payload.get("actor_id") or DEFAULT_ACTOR

    if TOOL_MODE in ("gateway", "auto"):
        try:
            client = _gateway_client()
            with client:
                tools = _list_all_tools(client)
                log.info("Gateway tools: %s", [t.tool_name for t in tools])
                return _run(prompt, session_id, actor_id, tools, "gateway")
        except Exception:
            if TOOL_MODE == "gateway":
                raise
            log.exception("Gateway unavailable; falling back to local tools (TOOL_MODE=auto)")
    from local_tools import LOCAL_TOOLS
    return _run(prompt, session_id, actor_id, LOCAL_TOOLS, "local")


@app.entrypoint
def invoke(payload, context=None):
    return handle(payload, getattr(context, "session_id", None))


if __name__ == "__main__":
    app.run()
