"""Create (or update) the Lambda that backs the Gateway target + its least-privilege role."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import *  # noqa: F401,F403

ROLE = "vira360-demo-tools-lambda-role"
FN = "vira360-demo-tools"

iam, lam = client("iam"), client("lambda")
guard(FN)
trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
policy = {"Version": "2012-10-17", "Statement": [
    {"Sid": "KbRetrieve", "Effect": "Allow", "Action": ["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
     "Resource": f"arn:aws:bedrock:{REGION}:{ACCOUNT}:knowledge-base/{KB_ID}"},
    {"Sid": "InvokeSonnet", "Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
     "Resource": [f"arn:aws:bedrock:{REGION}:{ACCOUNT}:inference-profile/{SONNET_PROFILE}"] + fm_arns(SONNET_FM)},
    {"Sid": "GetProfile", "Effect": "Allow", "Action": "bedrock:GetInferenceProfile",
     "Resource": f"arn:aws:bedrock:{REGION}:{ACCOUNT}:inference-profile/{SONNET_PROFILE}"},
    {"Sid": "ReadDocs", "Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::vira360-demo-kb-123456789012/docs/*"},
    {"Sid": "Logs", "Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
     "Resource": f"arn:aws:logs:{REGION}:{ACCOUNT}:log-group:/aws/lambda/{FN}:*"},
]}
role_arn = ensure_role(iam, ROLE, trust, "vira360-demo-tools-policy", policy)

BUILD_DIR.mkdir(exist_ok=True)
zpath = zip_dir({"common": AGENT_DIR / "common", "data": AGENT_DIR / "data"}, BUILD_DIR / "lambda.zip",
                {"handler.py": AGENT_DIR / "lambda_tools" / "handler.py"})
env = {"Variables": {"KB_ID": KB_ID, "TEXT_MODEL_ID": SONNET_PROFILE, "DOCS_BUCKET": "vira360-demo-kb-123456789012",
                     "AWS_ACCOUNT_ID": ACCOUNT}}
try:
    lam.get_function(FunctionName=FN)
    lam.update_function_code(FunctionName=FN, ZipFile=zpath.read_bytes())
    lam.get_waiter("function_updated").wait(FunctionName=FN)
    lam.update_function_configuration(FunctionName=FN, Environment=env, Timeout=60, MemorySize=512, Role=role_arn)
except lam.exceptions.ResourceNotFoundException:
    for attempt in range(8):
        try:
            lam.create_function(FunctionName=FN, Runtime="python3.13", Architectures=["arm64"], Role=role_arn,
                                Handler="handler.lambda_handler", Code={"ZipFile": zpath.read_bytes()},
                                Timeout=60, MemorySize=512, Environment=env,
                                Description="VIRA360 demo AgentCore Gateway tools")
            break
        except lam.exceptions.InvalidParameterValueException as e:
            print("IAM propagation, retrying:", e)
            time.sleep(8)
    lam.get_waiter("function_active_v2").wait(FunctionName=FN)
fn = lam.get_function(FunctionName=FN)["Configuration"]
save_config(lambda_arn=fn["FunctionArn"], lambda_role_arn=role_arn)
print("Lambda:", fn["FunctionArn"], fn["State"])
