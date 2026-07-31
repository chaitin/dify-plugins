from collections.abc import Generator
from typing import Any

from dify_plugin.entities import ParameterOption
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.tool import Tool

from client.octobus import Capability, OctoBusClient, OctoBusConfig


class DescribeCapsetTool(Tool):
    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        capset_id = str(tool_parameters.get("capset_id") or "").strip()
        client = OctoBusClient(OctoBusConfig.from_mapping(self.runtime.credentials))
        catalog = client.catalog(capset_id)
        capabilities = client.list_capabilities(capset_id, catalog=catalog)
        yield self.create_json_message(
            {
                "capset_id": capset_id,
                "capabilities": [capability_payload(item) for item in capabilities],
                "catalog": catalog,
                "mcp_endpoint": client.mcp_endpoint(capset_id),
            }
        )

    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        if parameter != "capset_id":
            return []
        return [
            ParameterOption(
                value=capset.id,
                label={"en_US": capset.label, "zh_Hans": capset.label},
            )
            for capset in OctoBusClient(
                OctoBusConfig.from_mapping(self.runtime.credentials)
            ).list_capsets()
        ]


def capability_payload(capability: Capability) -> dict[str, Any]:
    return {
        "capset_id": capability.capset_id,
        "tool_name": capability.tool_name,
        "name": capability.name,
        "description": capability.description,
        "service_id": capability.service_id,
        "method": capability.method,
        "protocol": capability.protocol,
        "input_schema": capability.input_schema,
        "raw": capability.raw,
    }
