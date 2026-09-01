from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from dify_plugin.file.entities import FileType
from dify_plugin.file.file import File

from client.agent_compose import AgentComposeError
from tools.run_agent import build_prompt, upload_files


def test_upload_files_reads_dify_file_blob_and_isolates_path() -> None:
    file = File(
        url="https://files.example/report.pdf", filename="../report.pdf", type=FileType.DOCUMENT
    )
    file._blob = b"pdf"
    client = Mock()

    paths = upload_files(client, "workspace-1", [file], SimpleNamespace(conversation_id="conv/1"))

    assert paths == ["inputs/conv1/0-report.pdf"]
    client.upload_workspace_file.assert_called_once_with(
        workspace_id="workspace-1",
        path=paths[0],
        content=b"pdf",
        filename="report.pdf",
        content_type="application/octet-stream",
    )
    assert '"files": ["inputs/conv1/0-report.pdf"]' in build_prompt("", "question", paths)


def test_upload_files_validates_workspace_and_size() -> None:
    file = {"filename": "large.pdf", "content": b"x" * (50 * 1024 * 1024 + 1)}
    with pytest.raises(AgentComposeError, match="workspace_id"):
        upload_files(Mock(), "", [file], SimpleNamespace())
    with pytest.raises(AgentComposeError, match="size limits"):
        upload_files(Mock(), "workspace-1", [file], SimpleNamespace())


def test_upload_files_empty_is_backward_compatible() -> None:
    assert upload_files(Mock(), "", None, SimpleNamespace()) == []
    assert build_prompt(None, "question", []) == "question"
