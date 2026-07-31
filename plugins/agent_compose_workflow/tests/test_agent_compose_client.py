import pytest
import responses
from dify_plugin.core.runtime import Session
from dify_plugin.entities.agent import AgentRuntime
from dify_plugin.entities.tool import ToolRuntime
from dify_plugin.invocations.storage import StorageInvocationError
from strategies.dynamic_workflow import DynamicWorkflowAgentStrategy, DynamicWorkflowParams

from client.agent_compose import (
    GET_PROJECT_PROCEDURE,
    LIST_PROJECTS_PROCEDURE,
    RUN_AGENT_PROCEDURE,
    AgentComposeClient,
    AgentComposeConfig,
    AgentComposeError,
    cleanup_policy_to_proto,
    forget_agent_compose_sandbox_id,
    parse_agent_selection,
    remember_agent_compose_sandbox_id,
    resolve_agent_compose_sandbox_id,
    resolve_agent_reference,
)
from tools.run_agent import RunAgentTool


def test_cleanup_policy_to_proto() -> None:
    assert cleanup_policy_to_proto("stop_on_completion").endswith("STOP_ON_COMPLETION")
    assert cleanup_policy_to_proto("keep_running").endswith("KEEP_RUNNING")
    assert cleanup_policy_to_proto("remove_on_completion").endswith("REMOVE_ON_COMPLETION")
    assert cleanup_policy_to_proto("keep_running").startswith("RUN_SANDBOX_")
    with pytest.raises(AgentComposeError):
        cleanup_policy_to_proto("forever")


def test_agent_strategy_defaults_to_stop_on_completion() -> None:
    params = DynamicWorkflowParams(agent="project/agent", query="hello")

    assert params.cleanup_policy == "stop_on_completion"


def test_agent_strategy_does_not_expose_manual_sandbox_id() -> None:
    assert "sandbox_id" not in DynamicWorkflowParams.model_fields


@responses.activate
def test_agent_strategy_stop_mode_skips_storage_and_emits_distinct_outputs() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + RUN_AGENT_PROCEDURE,
        json={
            "run": {
                "summary": {
                    "runId": "run-1",
                    "sandboxId": "sandbox-1",
                    "status": "RUN_STATUS_SUCCEEDED",
                },
                "output": "done",
            }
        },
    )
    session = Session.empty_session()
    session.conversation_id = "conversation-1"
    session.storage = FailingStorage(ValueError("storage must not be used"))
    strategy = DynamicWorkflowAgentStrategy(
        runtime=AgentRuntime(user_id="user-1"),
        session=session,
    )

    messages = list(
        strategy._invoke(
            {
                "agent_compose_url": base_url,
                "agent_compose_token": "token",
                "agent": '{"project_id":"project-1","agent_name":"writer"}',
                "query": "hello",
                "cleanup_policy": "stop_on_completion",
            }
        )
    )

    assert [message.type.value for message in messages].count("text") == 1
    assert [message.type.value for message in messages].count("json") == 1
    variables = {
        message.message.variable_name: message.message.variable_value
        for message in messages
        if message.type.value == "variable"
    }
    assert variables == {
        "run_id": "run-1",
        "sandbox_id": "sandbox-1",
        "status": "RUN_STATUS_SUCCEEDED",
        "error": "",
        "warnings": [],
    }
    assert b'"sandboxId"' not in responses.calls[0].request.body


def test_agent_strategy_accepts_connection_settings() -> None:
    params = DynamicWorkflowParams(
        agent_compose_url="http://agent-compose.test",
        agent_compose_token="secret-token",
        agent_compose_timeout_seconds=120,
        agent="project/agent",
        query="hello",
    )

    assert params.agent_compose_url == "http://agent-compose.test"
    assert params.agent_compose_token == "secret-token"
    assert params.agent_compose_timeout_seconds == 120


def test_agent_compose_config_from_mapping_overrides_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DYNAMIC_WORKFLOW_AGENT_COMPOSE_URL", "http://env-agent-compose.test")
    config = AgentComposeConfig.from_mapping(
        {
            "agent_compose_url": "http://credential-agent-compose.test",
            "agent_compose_token": "token",
            "agent_compose_timeout_seconds": "30",
        }
    )

    assert config.base_url == "http://credential-agent-compose.test"
    assert config.bearer_token == "token"
    assert config.timeout_seconds == 30


@responses.activate
def test_list_agents_fetches_project_agents() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={
            "projects": [
                {
                    "projectId": "project-1",
                    "name": "Demo Project",
                    "agentCount": 1,
                },
            ],
            "hasMore": False,
        },
        status=200,
    )
    responses.post(
        base_url + GET_PROJECT_PROCEDURE,
        json={
            "project": {
                "summary": {
                    "projectId": "project-1",
                    "name": "Demo Project",
                },
                "agents": [
                    {
                        "projectId": "project-1",
                        "agentName": "writer",
                        "provider": "openai",
                        "model": "gpt-4.1-mini",
                    }
                ],
            }
        },
        status=200,
    )

    client = AgentComposeClient(AgentComposeConfig(base_url=base_url, bearer_token="token"))
    agents = client.list_agents()

    assert len(agents) == 1
    assert agents[0].project_id == "project-1"
    assert agents[0].project_name == "Demo Project"
    assert agents[0].agent_name == "writer"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer token"
    project_id, agent_name = parse_agent_selection(agents[0].selection_value())
    assert project_id == "project-1"
    assert agent_name == "writer"


@responses.activate
def test_list_agents_paginates_frozen_v2_total_response() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={"projects": [{"projectId": "project-1", "name": "One"}], "total": 2},
    )
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={"projects": [{"projectId": "project-2", "name": "Two"}], "total": 2},
    )
    for project_id, agent_name in [("project-1", "writer"), ("project-2", "reader")]:
        responses.post(
            base_url + GET_PROJECT_PROCEDURE,
            json={
                "project": {
                    "agents": [
                        {
                            "projectId": project_id,
                            "agentName": agent_name,
                            "enabled": True,
                            "availability": "PROJECT_AGENT_AVAILABILITY_AVAILABLE",
                        }
                    ]
                }
            },
        )

    agents = AgentComposeClient(AgentComposeConfig(base_url=base_url)).list_agents(page_size=1)

    assert [agent.agent_name for agent in agents] == ["writer", "reader"]
    assert b'"offset": 1' in responses.calls[1].request.body


@responses.activate
def test_list_agents_excludes_disabled_and_unavailable_agents() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={"projects": [{"projectId": "project-1", "name": "Demo"}], "total": 1},
    )
    responses.post(
        base_url + GET_PROJECT_PROCEDURE,
        json={
            "project": {
                "agents": [
                    {"agentName": "disabled", "enabled": False},
                    {
                        "agentName": "broken",
                        "enabled": True,
                        "availability": "PROJECT_AGENT_AVAILABILITY_VALIDATION_FAILED",
                    },
                    {
                        "agentName": "writer",
                        "enabled": True,
                        "displayName": "Writer",
                        "driver": "docker",
                    },
                ]
            }
        },
    )

    agents = AgentComposeClient(AgentComposeConfig(base_url=base_url)).list_agents()

    assert [agent.agent_name for agent in agents] == ["writer"]
    assert agents[0].display_name == "Writer"
    assert agents[0].driver == "docker"


@responses.activate
def test_run_agent_tool_fetches_dynamic_agent_options() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={
            "projects": [
                {
                    "projectId": "project-1",
                    "name": "Demo Project",
                    "agentCount": 1,
                },
            ],
        },
        status=200,
    )
    responses.post(
        base_url + GET_PROJECT_PROCEDURE,
        json={
            "project": {
                "agents": [
                    {
                        "projectId": "project-1",
                        "agentName": "writer",
                        "model": "gpt-4.1-mini",
                    }
                ],
            }
        },
        status=200,
    )
    tool = RunAgentTool(
        runtime=ToolRuntime(
            credentials={
                "agent_compose_url": base_url,
                "agent_compose_token": "token",
            },
            user_id="user-1",
            session_id="session-1",
        ),
        session=Session.empty_session(),
    )

    options = tool.fetch_parameter_options("agent")

    assert len(options) == 1
    assert options[0].label.en_us == "Demo Project/writer"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer token"
    project_id, agent_name = parse_agent_selection(options[0].value)
    assert project_id == "project-1"
    assert agent_name == "writer"


@responses.activate
def test_resolve_agent_reference_accepts_unique_agent_name() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={"projects": [{"projectId": "project-1", "name": "Demo Project"}]},
        status=200,
    )
    responses.post(
        base_url + GET_PROJECT_PROCEDURE,
        json={
            "project": {
                "agents": [
                    {
                        "projectId": "project-1",
                        "agentName": "writer",
                    }
                ],
            }
        },
        status=200,
    )
    client = AgentComposeClient(AgentComposeConfig(base_url=base_url))

    assert resolve_agent_reference(client, "writer") == ("project-1", "writer")


@responses.activate
def test_resolve_agent_reference_accepts_project_agent_name() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={"projects": [{"projectId": "project-1", "name": "Demo Project"}]},
        status=200,
    )
    responses.post(
        base_url + GET_PROJECT_PROCEDURE,
        json={
            "project": {
                "agents": [
                    {
                        "projectId": "project-1",
                        "agentName": "writer",
                    }
                ],
            }
        },
        status=200,
    )
    client = AgentComposeClient(AgentComposeConfig(base_url=base_url))

    assert resolve_agent_reference(client, "Demo Project/writer") == ("project-1", "writer")


@responses.activate
def test_resolve_agent_reference_rejects_ambiguous_agent_name() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + LIST_PROJECTS_PROCEDURE,
        json={
            "projects": [
                {"projectId": "project-1", "name": "Project 1"},
                {"projectId": "project-2", "name": "Project 2"},
            ]
        },
        status=200,
    )
    for project_id in ["project-1", "project-2"]:
        responses.post(
            base_url + GET_PROJECT_PROCEDURE,
            json={
                "project": {
                    "agents": [
                        {
                            "projectId": project_id,
                            "agentName": "writer",
                        }
                    ],
                }
            },
            status=200,
        )
    client = AgentComposeClient(AgentComposeConfig(base_url=base_url))

    with pytest.raises(AgentComposeError, match="ambiguous"):
        resolve_agent_reference(client, "writer")


def test_resolve_agent_compose_sandbox_id_prefers_explicit_value() -> None:
    session = Session.empty_session()
    session.conversation_id = "conversation-1"

    assert (
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id="manual-sandbox",
            dify_session=session,
            project_id="project-1",
            agent_name="writer",
        )
        == "manual-sandbox"
    )


class FakeStorage:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}

    def get(self, key: str) -> bytes:
        return self.values[key]

    def exist(self, key: str) -> bool:
        return key in self.values

    def set(self, key: str, val: bytes) -> None:
        self.values[key] = val


class FailingStorage:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def get(self, key: str) -> bytes:
        raise self.error

    def exist(self, key: str) -> bool:
        raise self.error

    def set(self, key: str, val: bytes) -> None:
        raise self.error


def test_sandbox_storage_sdk_errors_degrade_to_empty_state() -> None:
    session = Session.empty_session()
    session.conversation_id = "conversation-1"
    session.storage = FailingStorage(StorageInvocationError("storage unavailable"))

    assert (
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id=None,
            dify_session=session,
            project_id="project-1",
            agent_name="writer",
        )
        == ""
    )
    remember_agent_compose_sandbox_id(
        explicit_sandbox_id=None,
        dify_session=session,
        project_id="project-1",
        agent_name="writer",
        agent_compose_sandbox_id="sandbox-1",
    )
    forget_agent_compose_sandbox_id(
        dify_session=session,
        project_id="project-1",
        agent_name="writer",
    )


def test_sandbox_storage_does_not_hide_unexpected_errors() -> None:
    session = Session.empty_session()
    session.conversation_id = "conversation-1"
    session.storage = FailingStorage(ValueError("programming error"))

    with pytest.raises(ValueError, match="programming error"):
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id=None,
            dify_session=session,
            project_id="project-1",
            agent_name="writer",
        )


def test_resolve_agent_compose_sandbox_id_reads_stored_agent_scoped_value() -> None:
    session = Session.empty_session()
    session.conversation_id = "conversation-1"
    session.storage = FakeStorage()

    remember_agent_compose_sandbox_id(
        explicit_sandbox_id="",
        dify_session=session,
        project_id="project-1",
        agent_name="writer",
        agent_compose_sandbox_id="agent-compose-sandbox-writer",
    )
    remember_agent_compose_sandbox_id(
        explicit_sandbox_id="",
        dify_session=session,
        project_id="project-1",
        agent_name="reader",
        agent_compose_sandbox_id="agent-compose-sandbox-reader",
    )

    first = resolve_agent_compose_sandbox_id(
        explicit_sandbox_id="",
        dify_session=session,
        project_id="project-1",
        agent_name="writer",
    )
    second = resolve_agent_compose_sandbox_id(
        explicit_sandbox_id=None,
        dify_session=session,
        project_id="project-1",
        agent_name="writer",
    )
    other_agent = resolve_agent_compose_sandbox_id(
        explicit_sandbox_id="",
        dify_session=session,
        project_id="project-1",
        agent_name="reader",
    )

    assert first == "agent-compose-sandbox-writer"
    assert first == second
    assert other_agent == "agent-compose-sandbox-reader"

    forget_agent_compose_sandbox_id(
        dify_session=session,
        project_id="project-1",
        agent_name="writer",
    )
    assert (
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id=None,
            dify_session=session,
            project_id="project-1",
            agent_name="writer",
        )
        == ""
    )
    assert (
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id=None,
            dify_session=session,
            project_id="project-1",
            agent_name="reader",
        )
        == "agent-compose-sandbox-reader"
    )


def test_resolve_agent_compose_sandbox_id_returns_empty_for_missing_key() -> None:
    session = Session.empty_session()
    session.conversation_id = "conversation-1"
    session.storage = FakeStorage()

    assert (
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id=None,
            dify_session=session,
            project_id="project-1",
            agent_name="writer",
        )
        == ""
    )


def test_resolve_agent_compose_sandbox_id_returns_empty_without_conversation() -> None:
    assert (
        resolve_agent_compose_sandbox_id(
            explicit_sandbox_id="",
            dify_session=Session.empty_session(),
            project_id="project-1",
            agent_name="writer",
        )
        == ""
    )


@responses.activate
def test_run_agent_posts_connect_json_and_parses_result() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + RUN_AGENT_PROCEDURE,
        json={
            "warnings": ["top-level warning"],
            "run": {
                "summary": {
                    "runId": "run-1",
                    "sandboxId": "sandbox-1",
                    "status": "RUN_STATUS_SUCCEEDED",
                    "warnings": ["summary warning"],
                },
                "output": "done",
                "warnings": ["top-level warning"],
            },
        },
        status=200,
    )

    client = AgentComposeClient(
        AgentComposeConfig(base_url=base_url, bearer_token="token", timeout_seconds=30)
    )
    result = client.run_agent(
        project_id="project-1",
        agent_name="agent",
        prompt="hello",
        sandbox_id="sandbox-existing",
    )

    assert result.success
    assert result.output == "done"
    assert result.run_id == "run-1"
    assert result.sandbox_id == "sandbox-1"
    assert result.warnings == ("top-level warning", "summary warning")
    request = responses.calls[0].request
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Authorization"] == "Bearer token"
    assert b'"projectId": "project-1"' in request.body
    assert b'"cleanupPolicy": "RUN_SANDBOX_CLEANUP_POLICY_STOP_ON_COMPLETION"' in request.body
    assert b'"sandboxId": "sandbox-existing"' in request.body
    assert b'"sessionId"' not in request.body


@responses.activate
def test_run_agent_uses_result_json_when_output_is_empty() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + RUN_AGENT_PROCEDURE,
        json={
            "run": {
                "summary": {
                    "runId": "run-1",
                    "status": "RUN_STATUS_SUCCEEDED",
                },
                "resultJson": '{"ok":true}',
            }
        },
        status=200,
    )

    client = AgentComposeClient(AgentComposeConfig(base_url=base_url))
    result = client.run_agent(project_id="project-1", agent_name="agent", prompt="hello")

    assert result.output == '{"ok":true}'


@responses.activate
def test_run_agent_failed_status_has_failure_reason() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + RUN_AGENT_PROCEDURE,
        json={
            "run": {
                "summary": {
                    "runId": "run-1",
                    "status": "RUN_STATUS_FAILED",
                },
            }
        },
        status=200,
    )

    client = AgentComposeClient(AgentComposeConfig(base_url=base_url))
    result = client.run_agent(project_id="project-1", agent_name="agent", prompt="hello")

    assert not result.success
    assert result.failure_reason() == "agent-compose run finished with status RUN_STATUS_FAILED"


@responses.activate
def test_run_agent_raises_on_http_error() -> None:
    base_url = "http://agent-compose.test"
    responses.post(base_url + RUN_AGENT_PROCEDURE, body="bad", status=503)
    client = AgentComposeClient(AgentComposeConfig(base_url=base_url))

    with pytest.raises(AgentComposeError, match="HTTP 503"):
        client.run_agent(project_id="project-1", agent_name="agent", prompt="hello")


@responses.activate
def test_run_agent_uses_tool_provider_credentials() -> None:
    base_url = "http://credential-agent-compose.test"
    responses.post(
        base_url + RUN_AGENT_PROCEDURE,
        json={
            "run": {
                "summary": {"runId": "run-1", "status": "RUN_STATUS_SUCCEEDED"},
                "output": "done",
            }
        },
    )
    session = Session.empty_session()
    session.conversation_id = "conversation-1"
    session.storage = FailingStorage(ValueError("storage must not be used"))
    tool = RunAgentTool(
        runtime=ToolRuntime(
            credentials={"agent_compose_url": base_url, "agent_compose_token": "token"},
            user_id="user-1",
            session_id="session-1",
        ),
        session=session,
    )

    messages = list(
        tool.invoke(
            {
                "agent": '{"project_id":"project-1","agent_name":"writer"}',
                "query": "hello",
                "client_request_id": "dify-request-1",
            }
        )
    )

    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer token"
    assert b'"clientRequestId": "dify-request-1"' in request.body
    variables = {
        message.message.variable_name: message.message.variable_value
        for message in messages
        if message.type.value == "variable"
    }
    assert variables == {
        "run_id": "run-1",
        "sandbox_id": "",
        "status": "RUN_STATUS_SUCCEEDED",
        "error": "",
        "warnings": [],
    }


@responses.activate
def test_connect_error_uses_structured_message() -> None:
    base_url = "http://agent-compose.test"
    responses.post(
        base_url + RUN_AGENT_PROCEDURE,
        json={"code": "invalid_argument", "message": "agent is disabled"},
        status=400,
    )

    with pytest.raises(AgentComposeError, match="agent is disabled"):
        AgentComposeClient(AgentComposeConfig(base_url=base_url)).run_agent(
            project_id="project-1", agent_name="agent", prompt="hello"
        )
