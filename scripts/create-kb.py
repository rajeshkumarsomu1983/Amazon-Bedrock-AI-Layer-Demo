"""Creates a managed Bedrock Knowledge Base for the VIRA360 demo.

Uses S3 Vectors as the vector store (no OpenSearch hourly floor) and Titan Text
Embeddings V2. Run `node scripts/export-docs.js` first to produce ./kb-corpus.
Usage: python3 scripts/create-kb.py   (uses your current AWS credentials/profile)
"""
import json, os, time, pathlib, boto3
from botocore.exceptions import ClientError

REGION = os.environ.get("AWS_REGION", "us-east-1")
sts = boto3.client("sts", region_name=REGION)
ACCT = sts.get_caller_identity()["Account"]
P = "vira360-demo"
BUCKET = f"{P}-kb-{ACCT}"
VBUCKET = f"{P}-vectors-{ACCT}"
INDEX = "kb-index"
ROLE = f"{P}-kb-role"
KB_NAME = f"{P}-kb"
EMBED_ARN = f"arn:aws:bedrock:{REGION}::foundation-model/amazon.titan-embed-text-v2:0"

s3 = boto3.client("s3", region_name=REGION)
s3v = boto3.client("s3vectors", region_name=REGION)
iam = boto3.client("iam")
ba = boto3.client("bedrock-agent", region_name=REGION)

# 1. Source bucket + corpus
try:
    if REGION == "us-east-1":
        s3.create_bucket(Bucket=BUCKET)
    else:
        s3.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": REGION})
except ClientError as e:
    if e.response["Error"]["Code"] not in ("BucketAlreadyOwnedByYou",):
        raise
s3.put_public_access_block(Bucket=BUCKET, PublicAccessBlockConfiguration={
    "BlockPublicAcls": True, "IgnorePublicAcls": True,
    "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
corpus = pathlib.Path(__file__).parent.parent / "kb-corpus"
for f in sorted(corpus.glob("*.txt")):
    s3.upload_file(str(f), BUCKET, f"docs/{f.name}")
    print("uploaded", f.name)

# 2. Vector bucket + index (Titan V2 = 1024 dims)
try:
    s3v.create_vector_bucket(vectorBucketName=VBUCKET)
except ClientError as e:
    if e.response["Error"]["Code"] != "ConflictException":
        raise
try:
    s3v.create_index(vectorBucketName=VBUCKET, indexName=INDEX, dataType="float32",
        dimension=1024, distanceMetric="cosine",
        metadataConfiguration={"nonFilterableMetadataKeys": ["AMAZON_BEDROCK_TEXT"]})
except ClientError as e:
    if e.response["Error"]["Code"] != "ConflictException":
        raise
vb_arn = s3v.get_vector_bucket(vectorBucketName=VBUCKET)["vectorBucket"]["vectorBucketArn"]
idx_arn = s3v.get_index(vectorBucketName=VBUCKET, indexName=INDEX)["index"]["indexArn"]

# 3. IAM role for the KB
trust = {"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "bedrock.amazonaws.com"}, "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": ACCT},
                  "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock:{REGION}:{ACCT}:knowledge-base/*"}}}]}
try:
    iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps(trust))
except ClientError as e:
    if e.response["Error"]["Code"] != "EntityAlreadyExists":
        raise
policy = {"Version": "2012-10-17", "Statement": [
    {"Effect": "Allow", "Action": "bedrock:InvokeModel", "Resource": EMBED_ARN},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:ListBucket"],
     "Resource": [f"arn:aws:s3:::{BUCKET}", f"arn:aws:s3:::{BUCKET}/*"],
     "Condition": {"StringEquals": {"aws:ResourceAccount": ACCT}}},
    {"Effect": "Allow", "Action": ["s3vectors:GetIndex", "s3vectors:QueryVectors", "s3vectors:PutVectors",
                                   "s3vectors:GetVectors", "s3vectors:DeleteVectors"],
     "Resource": idx_arn}]}
iam.put_role_policy(RoleName=ROLE, PolicyName="kb-access", PolicyDocument=json.dumps(policy))
role_arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
time.sleep(15)  # IAM propagation

# 4. Knowledge base
existing = [k for k in ba.list_knowledge_bases()["knowledgeBaseSummaries"] if k["name"] == KB_NAME]
if existing:
    kb_id = existing[0]["knowledgeBaseId"]
else:
    for attempt in range(5):
        try:
            kb = ba.create_knowledge_base(
                name=KB_NAME, roleArn=role_arn,
                knowledgeBaseConfiguration={"type": "VECTOR", "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": EMBED_ARN,
                    "embeddingModelConfiguration": {"bedrockEmbeddingModelConfiguration": {
                        "dimensions": 1024, "embeddingDataType": "FLOAT32"}}}},
                storageConfiguration={"type": "S3_VECTORS", "s3VectorsConfiguration": {"indexArn": idx_arn}})
            kb_id = kb["knowledgeBase"]["knowledgeBaseId"]
            break
        except ClientError as e:
            if attempt == 4:
                raise
            print("retrying create_knowledge_base:", e.response["Error"]["Message"])
            time.sleep(10)
while ba.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]["status"] != "ACTIVE":
    time.sleep(3)

# 5. Data source + sync
ds_list = ba.list_data_sources(knowledgeBaseId=kb_id)["dataSourceSummaries"]
if ds_list:
    ds_id = ds_list[0]["dataSourceId"]
else:
    ds_id = ba.create_data_source(
        knowledgeBaseId=kb_id, name=f"{P}-s3",
        dataSourceConfiguration={"type": "S3", "s3Configuration": {
            "bucketArn": f"arn:aws:s3:::{BUCKET}", "inclusionPrefixes": ["docs/"]}})["dataSource"]["dataSourceId"]
job = ba.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)["ingestionJob"]["ingestionJobId"]
while True:
    j = ba.get_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job)["ingestionJob"]
    if j["status"] in ("COMPLETE", "FAILED"):
        break
    time.sleep(3)
print("ingestion:", j["status"], j.get("statistics"), j.get("failureReasons", ""))
print(f"\nKB_ID={kb_id}")
