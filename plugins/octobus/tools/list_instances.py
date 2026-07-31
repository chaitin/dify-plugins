from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.tool import Tool

from client.octobus import OctoBusClient, OctoBusConfig


class ListInstancesTool(Tool):
    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        instances = OctoBusClient(
            OctoBusConfig.from_mapping(self.runtime.credentials)
        ).list_instances()
        yield self.create_json_message({"count": len(instances), "instances": instances})
