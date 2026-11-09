#!/usr/bin/env python3
"""Invoke the deployed VIRA360 AgentCore Runtime.

Usage: python3 agent/invoke.py "prompt" [--session-id ID] [--actor-id ID] [--json]
Reuse the same --session-id across calls to see AgentCore Memory carry context between turns.
Runtime ARN comes from $AGENT_RUNTIME_ARN or agent/config.local.json.
"""
import argparse
import json
import os
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV_PY = HERE / ".venv" / "bin" / "python"

try:
    import boto3
except ImportError:
    # Run this script with the agent venv's interpreter, which has boto3 installed.
    # We intentionally do NOT spawn a subprocess here; the caller picks the interpreter.
    hint = f"{VENV_PY} {Path(__file__).name} ..." if VENV_PY.exists() \
        else "uv venv --python 3.13 agent/.venv && uv pip install --python agent/.venv/bin/python boto3"
    sys.exit(f"boto3 not found. Run this script with the agent venv interpreter:\n  {hint}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="+", help="question or request for the agent")
    ap.add_argument("--session-id", help="reuse to continue a conversation (min 33 chars; auto-generated if omitted)")
    ap.add_argument("--actor-id", default="vira360-demo-user", help="memory actor (end user) id")
    ap.add_argument("--json", action="store_true", help="print the full JSON response")
    a = ap.parse_args()

    arn = os.environ.get("AGENT_RUNTIME_ARN")
    cfg_path = HERE / "config.local.json"
    if not arn and cfg_path.exists():
        arn = json.loads(cfg_path.read_text()).get("runtime_arn")
    if not arn:
        sys.exit("No runtime ARN: set AGENT_RUNTIME_ARN or run agent/infra/04_runtime.py")

    session_id = a.session_id or f"vira360-demo-session-{uuid.uuid4()}"
    if len(session_id) < 33:
        sys.exit(f"--session-id must be at least 33 characters (got {len(session_id)})")
    payload = {"prompt": " ".join(a.prompt), "session_id": session_id, "actor_id": a.actor_id}

    client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    res = client.invoke_agent_runtime(agentRuntimeArn=arn, runtimeSessionId=session_id, qualifier="DEFAULT",
                                      contentType="application/json", accept="application/json",
                                      payload=json.dumps(payload).encode())
    body = res["response"].read().decode("utf-8")
    try:
        out = json.loads(body)
    except json.JSONDecodeError:
        print(body)
        return
    if a.json or not isinstance(out, dict) or "result" not in out:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
    print(f"\n=== VIRA360 Agent ===\n{out['result']}\n")
    print(f"[session: {out['session_id']} | tools: {', '.join(out.get('tools_called', [])) or 'none'} | "
          f"tool source: {out.get('tool_source')}]", file=sys.stderr)


if __name__ == "__main__":
    main()
