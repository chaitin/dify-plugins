import json
import os
import re
import time
import uuid
from collections.abc import Generator
from typing import Any

from dify_plugin.entities import ParameterOption
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.tool import Tool

from client.agent_compose import (
    AgentComposeClient,
    AgentComposeConfig,
    AgentComposeError,
    cleanup_policy_reuses_sandbox,
    parse_agent_selection,
    remember_agent_compose_sandbox_id,
    resolve_agent_compose_sandbox_id,
)


class RunAgentTool(Tool):
    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        project_id, agent_name = parse_agent_selection(str(tool_parameters.get("agent") or ""))
        selection = json.loads(str(tool_parameters.get("agent") or "{}"))
        query = str(tool_parameters.get("query") or "").strip()
        instruction = str(tool_parameters.get("instruction") or "").strip()
        if not query:
            raise AgentComposeError("query is required")
        cleanup_policy = str(tool_parameters.get("cleanup_policy") or "stop_on_completion")
        reuse_sandbox = cleanup_policy_reuses_sandbox(cleanup_policy)
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
                "cleanup_policy": cleanup_policy,
            },
            metadata={"started_at": started_at, "provider": "agent-compose"},
            status=ToolInvokeMessage.LogMessage.LogStatus.START,
        )
        yield run_log

        client = AgentComposeClient(AgentComposeConfig.from_mapping(self.runtime.credentials))
        file_paths = upload_files(
            client,
            str(tool_parameters.get("workspace_id") or selection.get("workspace_id", "")),
            tool_parameters.get("files"),
            self.session,
        )
        prompt = build_prompt(instruction, query, file_paths)
        try:
            result = client.run_agent(
                project_id=project_id,
                agent_name=agent_name,
                prompt=prompt,
                sandbox_id=sandbox_id,
                cleanup_policy=cleanup_policy,
                output_schema_json=str(tool_parameters.get("output_schema_json") or ""),
                client_request_id=str(tool_parameters.get("client_request_id") or ""),
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

    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        if parameter != "agent":
            return []
        return [
            ParameterOption(
                value=agent.selection_value(),
                label={
                    "en_US": agent_option_label(
                        agent.project_name, agent.agent_name, agent.display_name
                    ),
                    "zh_Hans": agent_option_label(
                        agent.project_name, agent.agent_name, agent.display_name
                    ),
                },
            )
            for agent in AgentComposeClient(
                AgentComposeConfig.from_mapping(self.runtime.credentials)
            ).list_agents()
        ]


def agent_option_label(project_name: str, agent_name: str, display_name: str = "") -> str:
    agent_label = display_name or agent_name
    if display_name and display_name != agent_name:
        agent_label = f"{display_name} ({agent_name})"
    return f"{project_name}/{agent_label}" if project_name else agent_label


def build_prompt(instruction: str | None, query: str, file_paths: list[str] | None = None) -> str:
    instruction = (instruction or "").strip()
    query = query.strip()
    if not instruction and not file_paths:
        return query
    payload = {"instruction": instruction, "query": query}
    if file_paths:
        payload["files"] = file_paths
    return json.dumps(
        payload,
        ensure_ascii=False,
    )


def upload_files(client, workspace_id: str, files, session) -> list[str]:
    if not files:
        return []
    if isinstance(files, dict):
        files = [files]
    request_id = (
        re.sub(r"[^A-Za-z0-9_-]", "", str(getattr(session, "conversation_id", "") or ""))
        or uuid.uuid4().hex
    )
    paths = []
    for index, item in enumerate(files):
        data = item if isinstance(item, dict) else getattr(item, "__dict__", {})
        name = (
            os.path.basename(str(data.get("filename") or data.get("name") or f"file-{index}"))
            or f"file-{index}"
        )
        content = data.get("content") or getattr(item, "blob", None)
        if isinstance(content, str):
            content = content.encode()
        url = data.get("url")
        if content is None and url:
            import requests

            response = requests.get(str(url), timeout=300)
            response.raise_for_status()
            response.raise_for_status()
            content = response.content
        if not isinstance(content, (bytes, bytearray)):
            raise AgentComposeError(f"unable to read uploaded file {name}")
        path = f"inputs/{request_id}/{index}-{name}"
        client.upload_workspace_file(
            workspace_id=workspace_id,
            path=path,
            content=bytes(content),
            filename=name,
            content_type=str(
                data.get("mime_type") or data.get("mimeType") or "application/octet-stream"
            ),
        )
        paths.append(path)
    return paths
