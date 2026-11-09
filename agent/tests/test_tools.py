import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lambda_tools"))

from common import core  # noqa: E402
import handler  # noqa: E402


def ctx(name):
    return SimpleNamespace(client_context=SimpleNamespace(custom={"bedrockAgentCoreToolName": name}))


def test_tool_name_prefix_stripped():
    assert handler.tool_name_from_context(ctx("vira360-tools___search_projects")) == "search_projects"
    assert handler.tool_name_from_context(ctx("search_projects")) == "search_projects"


def test_unknown_tool():
    assert "error" in handler.lambda_handler({}, ctx("x___nope"))


def test_dispatch():
    with mock.patch.dict(core.TOOLS, {"search_projects": lambda query, k=4: {"q": query}}):
        assert handler.lambda_handler({"query": "a"}, ctx("t___search_projects")) == {"q": "a"}


def test_extract_strips_fences():
    with mock.patch.object(core, "converse", return_value='```json\n[{"task":"x"}]\n```'):
        out = core.extract_action_items("proj-endcap-001")
    assert out["parsed"] and out["action_items"] == [{"task": "x"}]


def test_extract_non_json():
    with mock.patch.object(core, "converse", return_value="nope"):
        assert core.extract_action_items("thread")["parsed"] is False


def test_load_project_text():
    assert "shelf depth" in core.load_project_text("proj-endcap-001")
    assert "Rajesh" in core.load_project_text("thread")
