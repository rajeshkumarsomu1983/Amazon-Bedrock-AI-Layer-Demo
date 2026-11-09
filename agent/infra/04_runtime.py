"""Build the direct-code-deploy ZIP, upload to S3, and create/update the AgentCore Runtime (PYTHON_3_13, arm64)."""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import *  # noqa: F401,F403

ROLE = "vira360-demo-runtime-role"
RUNTIME = "vira360_demo_agent"  # runtime names allow [a-zA-Z][a-zA-Z0-9_]* only
guard(RUNTIME)
cfg = load_config()
iam, s3, ctl = client("iam"), client("s3"), client("bedrock-agentcore-control")
KEY = "vira360_demo_agent/deployment_package.zip"

# ---- 1. code bucket (private) ----
try:
    s3.head_bucket(Bucket=CODE_BUCKET)
except Exception:
    s3.create_bucket(Bucket=CODE_BUCKET)  # us-east-1: no LocationConstraint
    s3.put_public_access_block(Bucket=CODE_BUCKET, PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
    s3.put_bucket_encryption(Bucket=CODE_BUCKET, ServerSideEncryptionConfiguration={
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})

# ---- 2. role ----
trust = {"Version": "2012-10-17", "Statement": [{
    "Sid": "AssumeRolePolicy", "Effect": "Allow", "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": ACCOUNT},
                  "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:*"}}}]}
profiles = [f"arn:aws:bedrock:{REGION}:{ACCOUNT}:inference-profile/{p}" for p in (SONNET_PROFILE, HAIKU_PROFILE)]
logs_rt = f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/bedrock-agentcore/runtimes/*"
policy = {"Version": "2012-10-17", "Statement": [
    {"Sid": "CodeZip", "Effect": "Allow", "Action": "s3:GetObject", "Resource": f"arn:aws:s3:::{CODE_BUCKET}/{KEY}"},
    {"Sid": "LogGroups", "Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:DescribeLogStreams"], "Resource": logs_rt},
    {"Sid": "LogGroupsList", "Effect": "Allow", "Action": "logs:DescribeLogGroups", "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:*"},
    {"Sid": "LogStreams", "Effect": "Allow", "Action": ["logs:CreateLogStream", "logs:PutLogEvents"], "Resource": f"{logs_rt}:log-stream:*"},
    {"Sid": "Tracing", "Effect": "Allow", "Action": ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"], "Resource": "*"},
    {"Sid": "Metrics", "Effect": "Allow", "Action": "cloudwatch:PutMetricData", "Resource": "*",
     "Condition": {"StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}}},
    {"Sid": "WorkloadIdentity", "Effect": "Allow",
     "Action": ["bedrock-agentcore:GetWorkloadAccessToken", "bedrock-agentcore:GetWorkloadAccessTokenForJWT", "bedrock-agentcore:GetWorkloadAccessTokenForUserId"],
     "Resource": [f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:workload-identity-directory/default",
                  f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:workload-identity-directory/default/workload-identity/{RUNTIME}-*"]},
    {"Sid": "Models", "Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
     "Resource": profiles + fm_arns(SONNET_FM) + fm_arns(HAIKU_FM)},
    {"Sid": "KbLocalFallback", "Effect": "Allow", "Action": ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
     "Resource": f"arn:aws:bedrock:{REGION}:{ACCOUNT}:knowledge-base/{KB_ID}"},
    {"Sid": "GetProfile", "Effect": "Allow", "Action": "bedrock:GetInferenceProfile", "Resource": profiles[0]},
    {"Sid": "Memory", "Effect": "Allow",
     "Action": ["bedrock-agentcore:CreateEvent", "bedrock-agentcore:GetEvent", "bedrock-agentcore:ListEvents",
                "bedrock-agentcore:DeleteEvent", "bedrock-agentcore:ListSessions", "bedrock-agentcore:ListActors",
                "bedrock-agentcore:RetrieveMemoryRecords", "bedrock-agentcore:ListMemoryRecords", "bedrock-agentcore:GetMemoryRecord"],
     "Resource": cfg["memory_arn"]},
    {"Sid": "InvokeGateway", "Effect": "Allow", "Action": "bedrock-agentcore:InvokeGateway", "Resource": cfg["gateway_arn"]},
]}
role_arn = ensure_role(iam, ROLE, trust, "vira360-demo-runtime-policy", policy)

# ---- 3. build package (arm64 wheels, Python 3.13) ----
pkg = BUILD_DIR / "pkg"
if "--skip-build" not in sys.argv:
    shutil.rmtree(pkg, ignore_errors=True)
    pkg.mkdir(parents=True)
    subprocess.run(["uv", "pip", "install", "--python-platform", "aarch64-manylinux2014", "--python-version", "3.13",
                    "--target", str(pkg), "--only-binary=:all:", "-r", str(AGENT_DIR / "runtime" / "requirements.txt")], check=True)
    shutil.copy(AGENT_DIR / "runtime" / "main.py", pkg / "main.py")
    shutil.copy(AGENT_DIR / "runtime" / "local_tools.py", pkg / "local_tools.py")
    shutil.copytree(AGENT_DIR / "common", pkg / "common", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(AGENT_DIR / "data", pkg / "data")
    zpath = zip_dir({"": pkg}, BUILD_DIR / "deployment_package.zip")
    print("zip MB:", round(zpath.stat().st_size / 1e6, 1))
zpath = BUILD_DIR / "deployment_package.zip"
s3.upload_file(str(zpath), CODE_BUCKET, KEY)

# ---- 4. runtime ----
env = {"AWS_REGION": REGION, "MEMORY_ID": cfg["memory_id"], "GATEWAY_URL": cfg["gateway_url"], "KB_ID": KB_ID,
       "TEXT_MODEL_ID": SONNET_PROFILE, "TOOL_MODE": "gateway",
       "MEMORY_STRATEGY_IDS": json.dumps([s["id"] for s in cfg["memory_strategies"]])}
artifact = {"codeConfiguration": {"code": {"s3": {"bucket": CODE_BUCKET, "prefix": KEY}}, "runtime": "PYTHON_3_13",
                                  "entryPoint": ["opentelemetry-instrument", "main.py"]}}
common = dict(agentRuntimeArtifact=artifact, roleArn=role_arn, networkConfiguration={"networkMode": "PUBLIC"},
              environmentVariables=env, lifecycleConfiguration={"idleRuntimeSessionTimeout": 900, "maxLifetime": 3600},
              description="VIRA360 demo agent (Strands + Gateway + Memory)")
rt = next((r for r in ctl.list_agent_runtimes()["agentRuntimes"] if r["agentRuntimeName"] == RUNTIME), None)
if rt is None:
    for _ in range(6):
        try:
            rt = ctl.create_agent_runtime(agentRuntimeName=RUNTIME, **common)
            break
        except ctl.exceptions.ValidationException as e:
            print("retry (IAM propagation?):", e)
            time.sleep(10)
else:
    rt = ctl.update_agent_runtime(agentRuntimeId=rt["agentRuntimeId"], **common)
rid = rt["agentRuntimeId"]
while True:
    r = ctl.get_agent_runtime(agentRuntimeId=rid)
    print("runtime", r["status"], r.get("agentRuntimeVersion"))
    if r["status"] in ("READY", "CREATE_FAILED", "UPDATE_FAILED"):
        break
    time.sleep(10)
assert r["status"] == "READY", r
save_config(runtime_id=rid, runtime_arn=r["agentRuntimeArn"], runtime_role_arn=role_arn, code_bucket=CODE_BUCKET, code_key=KEY)
print("Runtime ARN:", r["agentRuntimeArn"])
