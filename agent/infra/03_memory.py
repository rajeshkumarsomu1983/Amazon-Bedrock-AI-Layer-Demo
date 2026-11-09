"""Create AgentCore Memory: short-term events + long-term semantic and user-preference strategies."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import *  # noqa: F401,F403

NAME = "vira360_demo_memory"  # Memory names allow [a-zA-Z][a-zA-Z0-9_]* only (no hyphens)
guard(NAME)
ctl = client("bedrock-agentcore-control")
NS_TEMPLATE = "/strategy/{memoryStrategyId}/actor/{actorId}/"

mem = next((m for m in ctl.list_memories()["memories"] if m["id"].startswith(NAME + "-")), None)
if mem is None:
    strategies = [
        {"semanticMemoryStrategy": {"name": "vira360SemanticFacts", "description": "Project facts mentioned in conversation",
                                    "namespaceTemplates": [NS_TEMPLATE]}},
        {"userPreferenceMemoryStrategy": {"name": "vira360UserPrefs", "description": "User preferences (format, tone, focus)",
                                          "namespaceTemplates": [NS_TEMPLATE]}},
    ]
    mem = ctl.create_memory(name=NAME, description="VIRA360 demo agent memory", eventExpiryDuration=30,
                            memoryStrategies=strategies)["memory"]
mid = mem["id"]
while True:
    m = ctl.get_memory(memoryId=mid)["memory"]
    print("memory", m["status"])
    if m["status"] in ("ACTIVE", "FAILED"):
        break
    time.sleep(15)
assert m["status"] == "ACTIVE", m
strategies = [{"id": s["strategyId"], "name": s["name"], "type": s["type"]} for s in m.get("strategies", [])]
save_config(memory_id=mid, memory_arn=m["arn"], memory_strategies=strategies)
print("Memory:", mid, strategies)
