import json
import time
from collections.abc import Generator
from typing import Any

from dify_plugin.entities.agent import AgentInvokeMessage
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.agent import AgentStrategy
from pydantic import BaseModel

from client.agent_compose import (
    AgentComposeClient,
    AgentComposeConfig,
    AgentComposeError,
    cleanup_policy_keeps_sandbox,
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
    instruction: str | None = None
    cleanup_policy: str = "stop_on_completion"
    output_schema_json: str | None = None
    client_request_id: str | None = None


class DynamicWorkflowAgentStrategy(AgentStrategy):
    def _invoke(self, parameters: dict[str, Any]) -> Generator[AgentInvokeMessage, None, None]:
        params = DynamicWorkflowParams(**parameters)
        prompt = build_prompt(params.instruction, params.query)
        client = AgentComposeClient(
            AgentComposeConfig.from_mapping(
                {
                    "agent_compose_url": params.agent_compose_url,
                    "agent_compose_token": params.agent_compose_token,
                    "agent_compose_timeout_seconds": params.agent_compose_timeout_seconds,
                }
            )
        )
        project_id, agent_name = resolve_agent_reference(client, params.agent)
        keep_sandbox = cleanup_policy_keeps_sandbox(params.cleanup_policy)
        sandbox_id = ""
        if keep_sandbox:
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

        if keep_sandbox:
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


def build_prompt(instruction: str | None, query: str) -> str:
    instruction = (instruction or "").strip()
    query = query.strip()
    if not instruction:
        return query
    return json.dumps(
        {
            "instruction": instruction,
            "query": query,
        },
        ensure_ascii=False,
    )
