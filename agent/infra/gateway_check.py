"""Verify Gateway auth + MCP: unsigned request must be rejected; SigV4-signed tools/list and tools/call must work."""
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import load_config, REGION  # noqa: E402
from mcp import ClientSession  # noqa: E402
from mcp_proxy_for_aws.client import aws_iam_streamablehttp_client  # noqa: E402

url = load_config()["gateway_url"]
# Only ever talk to the HTTPS gateway endpoint. Guarding the scheme stops a tampered
# config from pointing urlopen at file:// or another unexpected scheme (Bandit B310).
if not url.startswith("https://"):
    sys.exit(f"gateway_url must be an https:// endpoint, got: {url!r}")

req = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
                             headers={"Content-Type": "application/json"}, method="POST")
try:
    r = urllib.request.urlopen(req, timeout=20)  # nosec B310 - scheme asserted https above
    print("UNSIGNED: HTTP", r.status, "<-- UNEXPECTED (gateway is open)")
except urllib.error.HTTPError as e:
    print("UNSIGNED request:", e.code, e.read().decode()[:200])


async def main():
    async with aws_iam_streamablehttp_client(url, aws_service="bedrock-agentcore", aws_region=REGION) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            names = [t.name for t in tools.tools]
            print("SIGNED tools/list:", names)
            target = next(n for n in names if n.endswith("___search_projects"))
            res = await s.call_tool(target, {"query": "coating quality problems on the samples", "k": 2})
            print("SIGNED tools/call", target, "isError=", res.isError)
            print(res.content[0].text[:600])

asyncio.run(main())
