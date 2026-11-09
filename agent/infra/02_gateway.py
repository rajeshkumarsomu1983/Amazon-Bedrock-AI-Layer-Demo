"""Create the AgentCore Gateway (MCP, AWS_IAM inbound auth) with the Lambda target."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import *  # noqa: F401,F403
from tool_schema import TOOLS

ROLE = "vira360-demo-gateway-role"
GW = "vira360-demo-gateway"
TARGET = "vira360-tools"
guard(GW)
cfg = load_config()
iam, ctl = client("iam"), client("bedrock-agentcore-control")


def trust(source_arn=None):
    cond = {"StringEquals": {"aws:SourceAccount": ACCOUNT}}
    if source_arn:
        cond["ArnLike"] = {"aws:SourceArn": source_arn}
    return {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                                                    "Action": "sts:AssumeRole", "Condition": cond}]}


policy = {"Version": "2012-10-17", "Statement": [{"Sid": "InvokeToolsLambda", "Effect": "Allow",
                                                  "Action": "lambda:InvokeFunction", "Resource": cfg["lambda_arn"]}]}
role_arn = ensure_role(iam, ROLE, trust(f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:gateway/*"), "vira360-demo-gateway-policy", policy)

gw = next((g for g in ctl.list_gateways()["items"] if g["name"] == GW), None)
if gw is None:
    gw = ctl.create_gateway(name=GW, description="VIRA360 demo MCP gateway", roleArn=role_arn, protocolType="MCP",
                            authorizerType="AWS_IAM")
gid = gw["gatewayId"]
while True:
    g = ctl.get_gateway(gatewayIdentifier=gid)
    print("gateway", g["status"])
    if g["status"] in ("READY", "FAILED"):
        break
    time.sleep(5)
assert g["status"] == "READY", g
# tighten trust to this gateway's ARN
ensure_role(iam, ROLE, trust(g["gatewayArn"]), "vira360-demo-gateway-policy", policy)

tcfg = {"mcp": {"lambda": {"lambdaArn": cfg["lambda_arn"], "toolSchema": {"inlinePayload": TOOLS}}}}
creds = [{"credentialProviderType": "GATEWAY_IAM_ROLE"}]
tgt = next((t for t in ctl.list_gateway_targets(gatewayIdentifier=gid)["items"] if t["name"] == TARGET), None)
if tgt is None:
    for _ in range(6):
        try:
            tgt = ctl.create_gateway_target(gatewayIdentifier=gid, name=TARGET, targetConfiguration=tcfg,
                                            credentialProviderConfigurations=creds, description="VIRA360 tools Lambda")
            break
        except ctl.exceptions.ValidationException as e:
            print("retry:", e); time.sleep(8)
else:
    tgt = ctl.update_gateway_target(gatewayIdentifier=gid, targetId=tgt["targetId"], name=TARGET,
                                    targetConfiguration=tcfg, credentialProviderConfigurations=creds)
while True:
    t = ctl.get_gateway_target(gatewayIdentifier=gid, targetId=tgt["targetId"])
    print("target", t["status"], t.get("statusReasons"))
    if t["status"] in ("READY", "FAILED", "UPDATE_UNSUCCESSFUL", "CREATE_UNSUCCESSFUL"):
        break
    time.sleep(5)
save_config(gateway_id=gid, gateway_arn=g["gatewayArn"], gateway_url=g["gatewayUrl"], gateway_role_arn=role_arn,
            gateway_target_id=tgt["targetId"], gateway_target_name=TARGET)
print("Gateway URL:", g["gatewayUrl"], "target", t["status"])
