"""Direct (non-Gateway) Strands tools; same behavior as the Lambda target. Used when TOOL_MODE=local|auto."""
import json

from strands import tool

from common import core


@tool
def search_projects(query: str, k: int = 4) -> str:
    """Semantic search over VIRA360 project records in the Knowledge Base. Returns passages with scores and sources."""
    return json.dumps(core.search_projects(query, k))


@tool
def ask_projects(question: str) -> str:
    """Grounded, cited answer from the VIRA360 Knowledge Base (RetrieveAndGenerate)."""
    return json.dumps(core.ask_projects(question))


@tool
def summarize_project(project_id: str = "thread") -> str:
    """3-bullet summary of a project record (e.g. proj-endcap-001) or the demo thread ('thread')."""
    return json.dumps(core.summarize_project(project_id))


@tool
def extract_action_items(project_id: str = "thread") -> str:
    """Extract structured action items (task, owner, due, needs_approval) for a project record or 'thread'."""
    return json.dumps(core.extract_action_items(project_id))


LOCAL_TOOLS = [search_projects, ask_projects, summarize_project, extract_action_items]
