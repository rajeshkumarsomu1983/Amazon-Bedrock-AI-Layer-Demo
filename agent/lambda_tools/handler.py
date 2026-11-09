"""Lambda target for the VIRA360 AgentCore Gateway. Dispatches on the Gateway-provided tool name."""
import json

from common.core import TOOLS


def tool_name_from_context(context) -> str:
    custom = getattr(getattr(context, "client_context", None), "custom", None) or {}
    name = custom.get("bedrockAgentCoreToolName", "")
    # Gateway sends "<targetName>___<toolName>"
    return name.split("___", 1)[-1]


def lambda_handler(event, context):
    name = tool_name_from_context(context)
    fn = TOOLS.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name!r}"}
    try:
        return fn(**(event or {}))
    except Exception as e:  # noqa: BLE001 - surface as tool error, not Lambda crash
        return {"error": f"{type(e).__name__}: {e}"}
