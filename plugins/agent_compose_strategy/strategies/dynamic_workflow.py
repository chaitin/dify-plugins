import json
import os
import re
import time
import uuid
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.agent import AgentInvokeMessage
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.file.file import File
from dify_plugin.interfaces.agent import AgentStrategy
from pydantic import BaseModel

from client.agent_compose import (
    AgentComposeClient,
    AgentComposeConfig,
    AgentComposeError,
    cleanup_policy_reuses_sandbox,
    remember_agent_compose_sandbox_id,
    resolve_agent_compose_sandbox_id,
    resolve_agent_reference,
)


class DynamicWorkflowParams(BaseModel):
    agent_compose_url: str | None = None
    agent_compose_token: str | None = None
    agent_compose_timeout_seconds: int | None = None
    agent: str
    query: str
    files: list[File] | None = None
    workspace_id: str | None = None
    instruction: str | None = None
    cleanup_policy: str = "stop_on_completion"
    output_schema_json: str | None = None
    client_request_id: str | None = None


class DynamicWorkflowAgentStrategy(AgentStrategy):
    def _invoke(self, parameters: dict[str, Any]) -> Generator[AgentInvokeMessage, None, None]:
        params = DynamicWorkflowParams(**parameters)
        client = AgentComposeClient(
            AgentComposeConfig.from_mapping(
                {
                    "agent_compose_url": params.agent_compose_url,
                    "agent_compose_token": params.agent_compose_token,
                    "agent_compose_timeout_seconds": params.agent_compose_timeout_seconds,
                }
            )
        )
        file_paths = upload_files(client, params.workspace_id or "", params.files, self.session)
        prompt = build_prompt(params.instruction, params.query, file_paths)
        project_id, agent_name = resolve_agent_reference(client, params.agent)
        reuse_sandbox = cleanup_policy_reuses_sandbox(params.cleanup_policy)
        sandbox_id = ""
        if reuse_sandbox:
            sandbox_id = resolve_agent_compose_sandbox_id(
                explicit_sandbox_id=None,
                dify_session=self.session,
                project_id=project_id,
                agent_name=agent_name,
            )

        started_at = time.perf_counter()
        run_log = self.create_log_message(
            label="agent-compose run",
            data={
                "project_id": project_id,
                "agent_name": agent_name,
                "sandbox_id": sandbox_id,
                "cleanup_policy": params.cleanup_policy,
            },
            metadata={"started_at": started_at, "provider": "agent-compose"},
            status=ToolInvokeMessage.LogMessage.LogStatus.START,
        )
        yield run_log

        try:
            result = client.run_agent(
                project_id=project_id,
                agent_name=agent_name,
                prompt=prompt,
                sandbox_id=sandbox_id,
                cleanup_policy=params.cleanup_policy,
                output_schema_json=params.output_schema_json or "",
                client_request_id=params.client_request_id or "",
            )
        except AgentComposeError as exc:
            yield self.finish_log_message(
                log=run_log,
                data={"error": str(exc)},
                metadata={
                    "started_at": started_at,
                    "finished_at": time.perf_counter(),
                    "elapsed_time": time.perf_counter() - started_at,
                    "provider": "agent-compose",
                },
                status=ToolInvokeMessage.LogMessage.LogStatus.ERROR,
                error=str(exc),
            )
            raise

        if reuse_sandbox:
            remember_agent_compose_sandbox_id(
                explicit_sandbox_id=None,
                dify_session=self.session,
                project_id=project_id,
                agent_name=agent_name,
                agent_compose_sandbox_id=result.sandbox_id,
            )

        if result.output:
            yield self.create_text_message(result.output)

        metadata = {
            "run_id": result.run_id,
            "sandbox_id": result.sandbox_id,
            "status": result.status,
            "error": result.failure_reason(),
            "warnings": list(result.warnings),
        }
        yield self.finish_log_message(
            log=run_log,
            data={**metadata, "output": result.output},
            metadata={
                "started_at": started_at,
                "finished_at": time.perf_counter(),
                "elapsed_time": time.perf_counter() - started_at,
                "provider": "agent-compose",
            },
            status=ToolInvokeMessage.LogMessage.LogStatus.SUCCESS
            if result.success
            else ToolInvokeMessage.LogMessage.LogStatus.ERROR,
            error=result.failure_reason() or None,
        )
        yield self.create_json_message(
            {
                "text": result.output,
                **metadata,
            }
        )
        for name, value in metadata.items():
            yield self.create_variable_message(name, value)
        failure_reason = result.failure_reason()
        if failure_reason:
            raise AgentComposeError(failure_reason)


def build_prompt(instruction: str | None, query: str, file_paths: list[str] | None = None) -> str:
    instruction = (instruction or "").strip()
    query = query.strip()
    if not instruction and not file_paths:
        return query
    payload = {
            "instruction": instruction,
            "query": query,
        }
    if file_paths:
        payload["files"] = file_paths
    return json.dumps(payload,
        ensure_ascii=False,
    )

def upload_files(client, workspace_id: str, files, session) -> list[str]:
    if not files:
        return []
    if not workspace_id:
        raise AgentComposeError("workspace_id is required when files are provided")
    request_id = re.sub(r"[^A-Za-z0-9_-]", "", str(getattr(session, "conversation_id", "") or "")) or uuid.uuid4().hex
    paths = []
    total = 0
    for index, item in enumerate(files):
        data = item if isinstance(item, dict) else getattr(item, "__dict__", {})
        name = os.path.basename(str(data.get("filename") or data.get("name") or f"file-{index}")) or f"file-{index}"
        content = data.get("content") or getattr(item, "blob", None)
        if isinstance(content, str): content = content.encode()
        if content is None and data.get("url"):
            import requests
            response = requests.get(str(data["url"]), timeout=300)
            response.raise_for_status()
            content = response.content
        if not isinstance(content, (bytes, bytearray)):
            raise AgentComposeError(f"unable to read uploaded file {name}")
        if len(content) > 50 * 1024 * 1024 or total + len(content) > 100 * 1024 * 1024:
            raise AgentComposeError("uploaded files exceed size limits")
        total += len(content)
        path = f"inputs/{request_id}/{index}-{name}"
        client.upload_workspace_file(workspace_id=workspace_id, path=path, content=bytes(content), filename=name, content_type=str(item.get("mime_type") or "application/octet-stream"))
        paths.append(path)
    return paths
