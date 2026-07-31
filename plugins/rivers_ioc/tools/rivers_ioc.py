from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from rivers_client import RiversAPIError, RiversClient


class RiversIOCTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        try:
            result = RiversClient(self.runtime.credentials.get("api_key", "")).query_ip(
                tool_parameters.get("ip_address")
            )
            yield self.create_json_message(result)
        except RiversAPIError as exc:
            yield self.create_text_message(f"Rivers IOC query failed: {exc}")
