#!/usr/bin/env python3
"""Delete every resource created by agent/infra/*.py, in reverse dependency order.

Only resources whose names start with vira360-demo / vira360_demo are ever touched (hard allowlist).
The Knowledge Base <KB_ID>, bucket vira360-demo-kb-*, and role vira360-demo-kb-role are explicitly protected.
Requires --yes. Re-running is safe: already-deleted resources are skipped.
"""
import argparse
import re
import sys
import time

import boto3

REGION, ACCOUNT = "us-east-1", "123456789012"
PROTECTED = {"vira360-demo-kb-role", f"vira360-demo-kb-{ACCOUNT}"}
ALLOW = re.compile(r"^vira360[-_]demo")
RUNTIME, GATEWAY, MEMORY = "vira360_demo_agent", "vira360-demo-gateway", "vira360_demo_memory"
FUNCTION = "vira360-demo-tools"
ROLES = ["vira360-demo-runtime-role", "vira360-demo-gateway-role", "vira360-demo-tools-lambda-role"]
CODE_BUCKET = f"vira360-demo-agent-code-{ACCOUNT}"
LOG_GROUPS_PREFIXES = ["/aws/lambda/vira360-demo-tools", "/aws/bedrock-agentcore/runtimes/vira360_demo_agent-"]


def ok(name):
    assert ALLOW.match(name) and name not in PROTECTED, f"refusing to touch {name}"
    return name


def step(msg, fn):
    try:
        fn()
        print("deleted:", msg)
    except Exception as e:  # noqa: BLE001
        code = getattr(e, "response", {}).get("Error", {}).get("Code", type(e).__name__)
        print(f"skip   : {msg} ({code})")


def wait_gone(get, tries=60):
    for _ in range(tries):
        try:
            get()
        except Exception:  # noqa: BLE001
            return
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="actually delete (otherwise only lists what would be deleted)")
    a = ap.parse_args()
    ctl = boto3.client("bedrock-agentcore-control", region_name=REGION)
    iam, lam, s3, logs = (boto3.client(n, region_name=REGION) for n in ("iam", "lambda", "s3", "logs"))
    plan = [f"runtime {RUNTIME} (+DEFAULT endpoint)", f"memory {MEMORY}-*", f"gateway {GATEWAY}-* (+targets)",
            f"lambda {FUNCTION}", f"roles {ROLES}", f"bucket {CODE_BUCKET}", f"log groups {LOG_GROUPS_PREFIXES}"]
    if not a.yes:
        print("Dry run. Would delete:\n  " + "\n  ".join(plan) + "\nRe-run with --yes to delete.")
        return

    for r in ctl.list_agent_runtimes()["agentRuntimes"]:
        if r["agentRuntimeName"] == RUNTIME:
            rid = r["agentRuntimeId"]
            for e in ctl.list_agent_runtime_endpoints(agentRuntimeId=rid)["runtimeEndpoints"]:
                if e["name"] != "DEFAULT":
                    step(f"endpoint {e['name']}", lambda e=e: ctl.delete_agent_runtime_endpoint(agentRuntimeId=rid, endpointName=e["name"]))
            step(f"runtime {rid}", lambda: ctl.delete_agent_runtime(agentRuntimeId=rid))
            wait_gone(lambda: ctl.get_agent_runtime(agentRuntimeId=rid))
    for m in ctl.list_memories()["memories"]:
        if m["id"].startswith(MEMORY + "-"):
            step(f"memory {m['id']}", lambda m=m: ctl.delete_memory(memoryId=ok(m["id"])))
            wait_gone(lambda: ctl.get_memory(memoryId=m["id"]))
    for g in ctl.list_gateways()["items"]:
        if g["name"] == GATEWAY:
            gid = g["gatewayId"]
            for t in ctl.list_gateway_targets(gatewayIdentifier=gid)["items"]:
                step(f"gateway target {t['name']}", lambda t=t: ctl.delete_gateway_target(gatewayIdentifier=gid, targetId=t["targetId"]))
                wait_gone(lambda: ctl.get_gateway_target(gatewayIdentifier=gid, targetId=t["targetId"]))
            step(f"gateway {gid}", lambda: ctl.delete_gateway(gatewayIdentifier=gid))
            wait_gone(lambda: ctl.get_gateway(gatewayIdentifier=gid))
    step(f"lambda {FUNCTION}", lambda: lam.delete_function(FunctionName=ok(FUNCTION)))
    for role in ROLES:
        def rm(role=role):
            ok(role)
            for p in iam.list_role_policies(RoleName=role)["PolicyNames"]:
                iam.delete_role_policy(RoleName=role, PolicyName=p)
            for p in iam.list_attached_role_policies(RoleName=role)["AttachedPolicies"]:
                iam.detach_role_policy(RoleName=role, PolicyArn=p["PolicyArn"])
            iam.delete_role(RoleName=role)
        step(f"role {role}", rm)

    def rm_bucket():
        ok(CODE_BUCKET)
        b = boto3.resource("s3", region_name=REGION).Bucket(CODE_BUCKET)
        b.objects.all().delete()
        b.object_versions.all().delete()
        s3.delete_bucket(Bucket=CODE_BUCKET)
    step(f"bucket {CODE_BUCKET}", rm_bucket)
    for prefix in LOG_GROUPS_PREFIXES:
        for lg in logs.describe_log_groups(logGroupNamePrefix=prefix)["logGroups"]:
            step(f"log group {lg['logGroupName']}", lambda lg=lg: logs.delete_log_group(logGroupName=lg["logGroupName"]))
    print("Done. agent/config.local.json can be deleted.")


if __name__ == "__main__":
    sys.exit(main())
