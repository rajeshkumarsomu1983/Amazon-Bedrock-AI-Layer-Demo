# VIRA360 AgentCore agent

Python [Strands](https://strandsagents.com) agent running on Amazon Bedrock AgentCore (account 123456789012, us-east-1).
Model: `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (geography-scoped US profile, never `global.`).

```
npm run agent / agent/invoke.py
        | SigV4 (InvokeAgentRuntime)
        v
 AgentCore Runtime  vira360_demo_agent  (direct code deploy, Python 3.13, arm64)
   |  Strands Agent + AgentCoreMemorySessionManager ---> AgentCore Memory vira360_demo_memory
   |       (session_id / actor_id)                         short-term events + semantic & user-preference strategies
   |  MCP over HTTPS, SigV4 (service bedrock-agentcore)
   v
 AgentCore Gateway  vira360-demo-gateway  (MCP, inbound auth = AWS_IAM)
   |  target vira360-tools  (GATEWAY_IAM_ROLE -> lambda:InvokeFunction)
   v
 Lambda vira360-demo-tools  -> Bedrock KB <KB_ID> (Retrieve / RetrieveAndGenerate) + Converse (Sonnet 4.5)
```

## Tools (served by the Gateway, exposed as `vira360-tools___<name>`)

| Tool | What it does |
|---|---|
| `search_projects` | KB `Retrieve`, returns passages + scores + S3 URIs |
| `ask_projects` | KB `RetrieveAndGenerate` (Sonnet 4.5), grounded answer + citations |
| `summarize_project` | 3-bullet summary of `proj-*` record or the demo `thread` (prompt ported from `src/summarize.js`) |
| `extract_action_items` | JSON action items (prompt ported from `src/extract.js`) |

`agent/runtime/local_tools.py` has the same tools called directly (`TOOL_MODE=local`, or `auto` to fall back if the Gateway is down). Deployed default is `gateway`; each response reports `tool_source` and `tools_called`.

## Auth choice

Gateway inbound auth is **AWS_IAM (SigV4)**: no secrets to store, the Runtime signs with its execution role (`bedrock-agentcore:InvokeGateway` on this one gateway). Unsigned requests get HTTP 401. If you need non-AWS callers, switch to `CUSTOM_JWT` (Cognito); not implemented here.

## Deploy (idempotent, in order)

```bash
export AWS_PROFILE=<AWS_PROFILE> AWS_REGION=us-east-1
uv venv --python 3.13 agent/.venv
uv pip install --python agent/.venv/bin/python -r agent/runtime/requirements.txt pytest
agent/.venv/bin/python agent/infra/01_lambda.py    # role + Lambda
agent/.venv/bin/python agent/infra/02_gateway.py   # gateway role, gateway, Lambda target
agent/.venv/bin/python agent/infra/03_memory.py    # memory + 2 long-term strategies (takes a few minutes)
agent/.venv/bin/python agent/infra/04_runtime.py   # build arm64 zip, upload, create/update runtime
agent/.venv/bin/python agent/infra/gateway_check.py  # unsigned=401, signed tools/list + tools/call
```

IDs are written to the gitignored `agent/config.local.json`. Re-run `04_runtime.py` after changing agent code or prompts. Runtime and Memory names use underscores because hyphens are not allowed there.

## Invoke

```bash
npm run agent -- "Summarize project proj-endcap-001"
python3 agent/invoke.py "What needs approval?" --session-id <33+ chars> [--actor-id ID] [--json]
```

Reuse `--session-id` to continue a conversation. Run `invoke.py` with the venv interpreter that has `boto3` (`agent/.venv/bin/python agent/invoke.py ...`); if `boto3` is missing it prints that hint and exits.

## Memory

- Short-term: every turn is stored as an event keyed by `session_id` + `actor_id`; the next invocation restores the history, so follow-ups ("that") resolve even after the Runtime microVM is gone.
- Long-term: semantic and user-preference strategies extract records asynchronously (about a minute or two) into `/strategy/{strategyId}/actor/{actorId}/`; they are retrieved for the same actor in any session.

## Costs / cleanup

Runtime, Gateway, Memory, Lambda and model calls are usage-billed; idle resources cost little. `python3 agent/teardown.py` lists what it would delete; `--yes` deletes it (only `vira360-demo*` names; the KB, its bucket and `vira360-demo-kb-role` are protected).

## Troubleshooting

- Runtime errors: CloudWatch group `/aws/bedrock-agentcore/runtimes/<runtimeId>-DEFAULT`.
- Tool errors: `/aws/lambda/vira360-demo-tools`.
- `AccessDenied` on `RetrieveAndGenerate`: Lambda role needs `bedrock:GetInferenceProfile` on the profile ARN (already included).
- Tests: `agent/.venv/bin/python -m pytest agent/tests`.
