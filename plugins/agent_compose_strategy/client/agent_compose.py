import hashlib
import json
import os
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import requests
from dify_plugin.invocations.storage import StorageInvocationError

GET_PROJECT_PROCEDURE = "/agentcompose.v2.ProjectService/GetProject"
LIST_PROJECTS_PROCEDURE = "/agentcompose.v2.ProjectService/ListProjects"
RUN_AGENT_PROCEDURE = "/agentcompose.v2.RunService/RunAgent"


class AgentComposeError(RuntimeError):
    """Raised when dynamic-workflow cannot complete an agent-compose request."""


@dataclass(frozen=True)
class AgentComposeConfig:
    base_url: str
    bearer_token: str = ""
    timeout_seconds: int = 900

    @classmethod
    def from_env(cls) -> "AgentComposeConfig":
        base_url = (
            os.getenv("DYNAMIC_WORKFLOW_AGENT_COMPOSE_URL") or os.getenv("AGENT_COMPOSE_HOST") or ""
        ).strip()
        timeout_raw = os.getenv("DYNAMIC_WORKFLOW_TIMEOUT_SECONDS", "900").strip()
        try:
            timeout_seconds = int(timeout_raw)
        except ValueError as exc:
            raise AgentComposeError("DYNAMIC_WORKFLOW_TIMEOUT_SECONDS must be an integer") from exc
        return cls(
            base_url=base_url,
            bearer_token=os.getenv("DYNAMIC_WORKFLOW_AGENT_COMPOSE_TOKEN", "").strip(),
            timeout_seconds=timeout_seconds,
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any] | None) -> "AgentComposeConfig":
        env_config = cls.from_env()
        values = values or {}

        def read(name: str) -> str:
            return str(values.get(name) or "").strip()

        timeout_seconds = env_config.timeout_seconds
        timeout_raw = read("agent_compose_timeout_seconds")
        if timeout_raw:
            try:
                timeout_seconds = int(timeout_raw)
            except ValueError as exc:
                raise AgentComposeError("agent_compose_timeout_seconds must be an integer") from exc

        return cls(
            base_url=read("agent_compose_url") or env_config.base_url,
            bearer_token=read("agent_compose_token") or env_config.bearer_token,
            timeout_seconds=timeout_seconds,
        )

    def normalized_base_url(self) -> str:
        base_url = self.base_url.rstrip("/")
        if not base_url:
            raise AgentComposeError(
                "agent-compose URL is not configured. Set "
                "DYNAMIC_WORKFLOW_AGENT_COMPOSE_URL or AGENT_COMPOSE_HOST."
            )
        if not base_url.startswith(("http://", "https://")):
            raise AgentComposeError("agent-compose URL must start with http:// or https://")
        if self.timeout_seconds <= 0:
            raise AgentComposeError("agent-compose timeout must be greater than zero")
        return base_url


@dataclass(frozen=True)
class RunAgentResult:
    output: str
    run_id: str
    sandbox_id: str
    status: str
    error: str
    warnings: tuple[str, ...]
    raw: dict[str, Any]

    @property
    def success(self) -> bool:
        return self.status == "RUN_STATUS_SUCCEEDED" and not self.error

    def failure_reason(self) -> str:
        if self.success:
            return ""
        if self.error:
            return self.error
        if self.status:
            return f"agent-compose run finished with status {self.status}"
        return "agent-compose run did not return a terminal success status"


@dataclass(frozen=True)
class AgentComposeAgent:
    project_id: str
    project_name: str
    agent_name: str
    provider: str = ""
    model: str = ""
    image: str = ""
    driver: str = ""
    display_name: str = ""
    description: str = ""

    def selection_value(self) -> str:
        return json.dumps(
            {
                "project_id": self.project_id,
                "project_name": self.project_name,
                "agent_name": self.agent_name,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


class AgentComposeClient:
    def __init__(self, config: AgentComposeConfig | None = None) -> None:
        self.config = config or AgentComposeConfig.from_env()

    def list_agents(self, *, page_size: int = 100) -> list[AgentComposeAgent]:
        projects = self._list_projects(page_size=page_size)
        agents: list[AgentComposeAgent] = []
        for project in projects:
            project_id = str(project.get("projectId") or project.get("project_id") or "").strip()
            project_name = str(project.get("name") or "").strip()
            if not project_id:
                continue
            detail = self._get_project(project_id)
            project_body = detail.get("project")
            if not isinstance(project_body, dict):
                continue
            for agent in project_body.get("agents") or []:
                if not isinstance(agent, dict):
                    continue
                # The frozen v2 API exposes disabled and unavailable agents in
                # project details. They cannot be run and must not be offered
                # as selectable Dify options. Missing fields keep compatibility
                # with older agent-compose servers.
                if agent.get("enabled") is False:
                    continue
                availability = str(agent.get("availability") or "").strip()
                if availability in {
                    "PROJECT_AGENT_AVAILABILITY_UNAVAILABLE",
                    "PROJECT_AGENT_AVAILABILITY_VALIDATION_FAILED",
                }:
                    continue
                agent_name = str(agent.get("agentName") or agent.get("agent_name") or "").strip()
                if not agent_name:
                    continue
                agents.append(
                    AgentComposeAgent(
                        project_id=project_id,
                        project_name=project_name,
                        agent_name=agent_name,
                        provider=str(agent.get("provider") or "").strip(),
                        model=str(agent.get("model") or "").strip(),
                        image=str(agent.get("image") or "").strip(),
                        driver=str(agent.get("driver") or "").strip(),
                        display_name=str(
                            agent.get("displayName") or agent.get("display_name") or ""
                        ).strip(),
                        description=str(agent.get("description") or "").strip(),
                    )
                )
        return agents

    def run_agent(
        self,
        *,
        project_id: str,
        agent_name: str,
        prompt: str,
        sandbox_id: str = "",
        cleanup_policy: str = "stop_on_completion",
        output_schema_json: str = "",
        client_request_id: str = "",
    ) -> RunAgentResult:
        if not project_id.strip():
            raise AgentComposeError("project_id is required")
        if not agent_name.strip():
            raise AgentComposeError("agent_name is required")
        if not prompt.strip():
            raise AgentComposeError("query is required")

        payload = {
            "projectId": project_id.strip(),
            "agentName": agent_name.strip(),
            "prompt": prompt,
            "source": "RUN_SOURCE_API",
            "sandboxId": sandbox_id.strip(),
            "cleanupPolicy": cleanup_policy_to_proto(cleanup_policy),
            "outputSchemaJson": output_schema_json.strip(),
            "clientRequestId": client_request_id.strip() or f"dify-dynamic-workflow-{uuid.uuid4()}",
        }
        payload = {key: value for key, value in payload.items() if value not in {"", None}}

        body = self._post_json(RUN_AGENT_PROCEDURE, payload)
        return parse_run_agent_response(body)

    def validate_connection(self) -> None:
        """Validate URL, authentication, and the frozen v2 Project API."""
        self._post_json(LIST_PROJECTS_PROCEDURE, {"offset": 0, "limit": 1})

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.config.bearer_token:
            headers["Authorization"] = f"Bearer {self.config.bearer_token}"
        return headers

    def _list_projects(self, *, page_size: int) -> list[dict[str, Any]]:
        page_size = max(1, min(page_size, 500))
        projects: list[dict[str, Any]] = []
        offset = 0
        while True:
            payload = self._post_json(
                LIST_PROJECTS_PROCEDURE,
                {"offset": offset, "limit": page_size},
            )
            page = payload.get("projects") or []
            if isinstance(page, list):
                projects.extend(project for project in page if isinstance(project, dict))
            page_count = len(page) if isinstance(page, list) else 0

            # Current frozen v2 ListProjectsResponse is offset/limit based and
            # returns `total`. Keep the former hasMore/nextOffset shape as a
            # compatibility fallback for pre-freeze deployments.
            if "total" in payload:
                try:
                    total = int(payload.get("total") or 0)
                except (TypeError, ValueError) as exc:
                    raise AgentComposeError(
                        "agent-compose returned an invalid projects total"
                    ) from exc
                offset += page_count
                if offset >= total or page_count == 0:
                    return projects
                continue

            if not payload.get("hasMore"):
                return projects
            next_offset = payload.get("nextOffset") or payload.get("next_offset")
            try:
                new_offset = int(next_offset)
            except (TypeError, ValueError):
                new_offset = offset + page_count
            if new_offset <= offset or page_count == 0:
                raise AgentComposeError("agent-compose returned invalid project pagination")
            offset = new_offset

    def _get_project(self, project_id: str) -> dict[str, Any]:
        return self._post_json(
            GET_PROJECT_PROCEDURE,
            {"project": {"projectId": project_id}},
        )

    def _post_json(self, procedure: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = requests.post(
                self.config.normalized_base_url() + procedure,
                json=payload,
                headers=self._headers(),
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise AgentComposeError(f"cannot reach agent-compose: {exc}") from exc
        if response.status_code < 200 or response.status_code >= 300:
            detail = response.text.strip()
            try:
                error_body = response.json()
            except ValueError:
                error_body = None
            if isinstance(error_body, dict):
                detail = str(error_body.get("message") or error_body.get("code") or detail)
            raise AgentComposeError(f"agent-compose returned HTTP {response.status_code}: {detail}")
        try:
            body = response.json()
        except ValueError as exc:
            raise AgentComposeError("agent-compose returned a non-JSON response") from exc
        if not isinstance(body, dict):
            raise AgentComposeError("agent-compose returned a non-object response")
        return body


def cleanup_policy_to_proto(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"", "stop", "stop_on_completion"}:
        return "RUN_SANDBOX_CLEANUP_POLICY_STOP_ON_COMPLETION"
    if normalized in {"keep", "keep_running"}:
        return "RUN_SANDBOX_CLEANUP_POLICY_KEEP_RUNNING"
    if normalized in {"remove", "remove_on_completion"}:
        return "RUN_SANDBOX_CLEANUP_POLICY_REMOVE_ON_COMPLETION"
    raise AgentComposeError(
        "cleanup_policy must be one of: stop_on_completion, keep_running, remove_on_completion"
    )


def cleanup_policy_keeps_sandbox(value: str) -> bool:
    return cleanup_policy_to_proto(value) == "RUN_SANDBOX_CLEANUP_POLICY_KEEP_RUNNING"


def parse_agent_selection(value: str) -> tuple[str, str]:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise AgentComposeError(
            "agent selection must be generated by the agent-compose selector"
        ) from exc
    if not isinstance(payload, dict):
        raise AgentComposeError("agent selection must be a JSON object")

    project_id = str(payload.get("project_id") or payload.get("projectId") or "").strip()
    agent_name = str(payload.get("agent_name") or payload.get("agentName") or "").strip()
    if project_id and agent_name:
        return project_id, agent_name

    raise AgentComposeError("agent selection is missing project_id or agent_name")


def resolve_agent_reference(client: AgentComposeClient, value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        raise AgentComposeError("agent is required")

    if value.startswith("{"):
        return parse_agent_selection(value)

    project_name = ""
    agent_name = value
    if "/" in value:
        project_name, agent_name = [part.strip() for part in value.split("/", 1)]
    if not agent_name:
        raise AgentComposeError("agent name is required")

    matches = []
    for agent in client.list_agents():
        if project_name:
            if agent.project_name == project_name and agent.agent_name == agent_name:
                matches.append(agent)
            continue
        if agent.agent_name == agent_name:
            matches.append(agent)

    if len(matches) == 1:
        match = matches[0]
        return match.project_id, match.agent_name
    if not matches:
        raise AgentComposeError(
            f"agent-compose agent {value!r} was not found. Use project/agent or a unique agent name."
        )
    raise AgentComposeError(f"agent-compose agent {agent_name!r} is ambiguous. Use project/agent.")


def resolve_agent_compose_sandbox_id(
    *,
    explicit_sandbox_id: str | None,
    dify_session: Any,
    project_id: str,
    agent_name: str,
) -> str:
    explicit_sandbox_id = (explicit_sandbox_id or "").strip()
    if explicit_sandbox_id:
        return explicit_sandbox_id

    key = agent_compose_sandbox_storage_key(
        dify_session=dify_session,
        project_id=project_id,
        agent_name=agent_name,
    )
    if not key:
        return ""
    try:
        if not dify_session.storage.exist(key):
            return ""
        return dify_session.storage.get(key).decode("utf-8").strip()
    except (StorageInvocationError, UnicodeDecodeError):
        return ""


def remember_agent_compose_sandbox_id(
    *,
    explicit_sandbox_id: str | None,
    dify_session: Any,
    project_id: str,
    agent_name: str,
    agent_compose_sandbox_id: str,
) -> None:
    if (explicit_sandbox_id or "").strip():
        return
    agent_compose_sandbox_id = agent_compose_sandbox_id.strip()
    if not agent_compose_sandbox_id:
        return
    key = agent_compose_sandbox_storage_key(
        dify_session=dify_session,
        project_id=project_id,
        agent_name=agent_name,
    )
    if not key:
        return
    try:
        dify_session.storage.set(key, agent_compose_sandbox_id.encode("utf-8"))
    except StorageInvocationError:
        return


def forget_agent_compose_sandbox_id(
    *,
    dify_session: Any,
    project_id: str,
    agent_name: str,
) -> None:
    key = agent_compose_sandbox_storage_key(
        dify_session=dify_session,
        project_id=project_id,
        agent_name=agent_name,
    )
    if not key:
        return
    try:
        dify_session.storage.set(key, b"")
    except StorageInvocationError:
        return


def agent_compose_sandbox_storage_key(
    *,
    dify_session: Any,
    project_id: str,
    agent_name: str,
) -> str:
    conversation_id = str(getattr(dify_session, "conversation_id", "") or "").strip()
    if not conversation_id:
        return ""

    # Scope by agent to avoid reusing a sandbox created by another agent in the
    # same Dify conversation.
    namespace = f"{conversation_id}|{project_id.strip()}|{agent_name.strip()}"
    digest = hashlib.sha256(namespace.encode("utf-8")).hexdigest()[:32]
    return f"agent_compose_sandbox_{digest}"


def parse_run_agent_response(body: dict[str, Any]) -> RunAgentResult:
    run = body.get("run")
    if not isinstance(run, dict):
        raise AgentComposeError("agent-compose response is missing run")
    summary = run.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    output = str(run.get("output") or "")
    result_json = str(run.get("resultJson") or "")
    if not output and result_json:
        output = result_json
    warning_values = [body.get("warnings"), run.get("warnings"), summary.get("warnings")]
    warnings: list[str] = []
    for values in warning_values:
        if not isinstance(values, list):
            continue
        for value in values:
            warning = str(value or "").strip()
            if warning and warning not in warnings:
                warnings.append(warning)
    return RunAgentResult(
        output=output,
        run_id=str(summary.get("runId") or ""),
        sandbox_id=str(summary.get("sandboxId") or ""),
        status=str(summary.get("status") or ""),
        error=str(summary.get("error") or run.get("cleanupError") or ""),
        warnings=tuple(warnings),
        raw=body,
    )
