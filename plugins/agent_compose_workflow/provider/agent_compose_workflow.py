from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from client.agent_compose import AgentComposeClient, AgentComposeConfig


class AgentComposeWorkflowProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            client = AgentComposeClient(AgentComposeConfig.from_mapping(credentials))
            client.validate_connection()
        except Exception as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
