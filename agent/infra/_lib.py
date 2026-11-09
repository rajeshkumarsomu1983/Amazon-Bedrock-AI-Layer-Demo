"""Shared helpers for the idempotent infra scripts. Only vira360-demo*/vira360_demo* names are ever touched."""
import json
import re
import time
import zipfile
from pathlib import Path

import boto3

REGION = "us-east-1"
ACCOUNT = "123456789012"
KB_ID = "<KB_ID>"
AGENT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = AGENT_DIR / "config.local.json"
BUILD_DIR = AGENT_DIR / ".build"
SONNET_PROFILE = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_PROFILE = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
SONNET_FM = "anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_FM = "anthropic.claude-haiku-4-5-20251001-v1:0"
FM_REGIONS = ["us-east-1", "us-east-2", "us-west-2"]
CODE_BUCKET = f"vira360-demo-agent-code-{ACCOUNT}"


def guard(name: str) -> str:
    assert re.match(r"^vira360[-_]demo", name), f"refusing to touch non-vira360-demo resource: {name}"
    return name


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}


def save_config(**kw):
    cfg = load_config()
    cfg.update(kw)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n")
    return cfg


def client(name):
    return boto3.client(name, region_name=REGION)


def zip_dir(src_dirs: dict, out: Path, extra_files: dict | None = None):
    """src_dirs: {arcname_prefix: Path}; files 644 / dirs 755."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        def add(path: Path, arc: str):
            zi = zipfile.ZipInfo(arc, date_time=(2026, 1, 1, 0, 0, 0))
            zi.external_attr = (0o100644 << 16)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, path.read_bytes())
        for prefix, d in src_dirs.items():
            for p in sorted(Path(d).rglob("*")):
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                    add(p, f"{prefix}/{p.relative_to(d)}".lstrip("/"))
        for arc, p in (extra_files or {}).items():
            add(Path(p), arc)
    return out


def fm_arns(fm_id):
    return [f"arn:aws:bedrock:{r}::foundation-model/{fm_id}" for r in FM_REGIONS]


def ensure_role(iam, name, trust, policy_name, policy):
    guard(name)
    try:
        arn = iam.get_role(RoleName=name)["Role"]["Arn"]
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(trust))
    except iam.exceptions.NoSuchEntityException:
        arn = iam.create_role(
            RoleName=name, AssumeRolePolicyDocument=json.dumps(trust),
            Description="VIRA360 demo AgentCore agent (safe to delete via agent/teardown.py)",
        )["Role"]["Arn"]
        time.sleep(10)
    iam.put_role_policy(RoleName=name, PolicyName=policy_name, PolicyDocument=json.dumps(policy))
    return arn
