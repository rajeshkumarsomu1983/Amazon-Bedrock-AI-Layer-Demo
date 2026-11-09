def _s(desc, props, required):
    return {"type": "object", "description": desc, "properties": props, "required": required}


TOOLS = [
    {"name": "search_projects",
     "description": "Semantic search over VIRA360 project records (Bedrock Knowledge Base Retrieve). Returns top passages with relevance scores and S3 source URIs.",
     "inputSchema": _s("Search input", {
         "query": {"type": "string", "description": "Natural-language search query"},
         "k": {"type": "integer", "description": "Number of results (default 4)"}}, ["query"])},
    {"name": "ask_projects",
     "description": "Grounded, cited answer from the VIRA360 Knowledge Base (RetrieveAndGenerate with Claude Sonnet 4.5). Use for status updates and questions about project history.",
     "inputSchema": _s("Question input", {
         "question": {"type": "string", "description": "The question or request"}}, ["question"])},
    {"name": "summarize_project",
     "description": "Summarize a VIRA360 project record (e.g. proj-endcap-001) or the demo thread (project_id 'thread') in exactly 3 bullets.",
     "inputSchema": _s("Summarize input", {
         "project_id": {"type": "string", "description": "Project record id such as proj-endcap-001, or 'thread'"}}, ["project_id"])},
    {"name": "extract_action_items",
     "description": "Extract structured action items (task, owner, due, needs_approval) from a VIRA360 project record or the demo thread.",
     "inputSchema": _s("Extract input", {
         "project_id": {"type": "string", "description": "Project record id such as proj-endcap-001, or 'thread'"}}, ["project_id"])},
]
