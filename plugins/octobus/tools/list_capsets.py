from collections.abc import Generator
from typing import Any

from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.tool import Tool

from client.octobus import OctoBusClient, OctoBusConfig


class ListCapsetsTool(Tool):
    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        capsets = OctoBusClient(OctoBusConfig.from_mapping(self.runtime.credentials)).list_capsets()
        payload = {
            "count": len(capsets),
            "capsets": [
                {
                    "id": capset.id,
                    "name": capset.name,
                    "description": capset.description,
                    "raw": capset.raw,
                }
                for capset in capsets
            ],
        }
        yield self.create_json_message(payload)
