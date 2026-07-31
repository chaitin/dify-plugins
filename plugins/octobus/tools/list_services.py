from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.tool import Tool

from client.octobus import OctoBusClient, OctoBusConfig


class ListServicesTool(Tool):
    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        services = OctoBusClient(
            OctoBusConfig.from_mapping(self.runtime.credentials)
        ).list_services()
        yield self.create_json_message({"count": len(services), "services": services})
