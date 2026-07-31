import time
from collections.abc import Generator
from typing import Any

from dify_plugin.entities import ParameterOption
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.interfaces.tool import Tool

from client.octobus import (
    OctoBusClient,
    OctoBusConfig,
    parse_arguments_json,
    parse_capability_selection,
)


class CallCapabilityTool(Tool):
    def _invoke(
        self,
        tool_parameters: dict[str, Any],
    ) -> Generator[ToolInvokeMessage, None, None]:
        selected_capset_id, selected_tool_name = parse_capability_selection(
            tool_parameters.get("capability")
        )
        capset_id = str(tool_parameters.get("capset_id") or selected_capset_id).strip()
        tool_name = str(tool_parameters.get("tool_name") or selected_tool_name).strip()
        arguments = parse_arguments_json(tool_parameters.get("arguments_json"))

        started_at = time.perf_counter()
        run_log = self.create_log_message(
            label="octobus capability call",
            data={"capset_id": capset_id, "tool_name": tool_name, "arguments": arguments},
            metadata={"started_at": started_at, "provider": "octobus"},
            status=ToolInvokeMessage.LogMessage.LogStatus.START,
        )
        yield run_log

        result = OctoBusClient(
            OctoBusConfig.from_mapping(self.runtime.credentials)
        ).call_capability(
            capset_id=capset_id,
            tool_name=tool_name,
            arguments=arguments,
        )
        payload = {
            "capset_id": capset_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
        }
        yield self.finish_log_message(
            log=run_log,
            data=payload,
            metadata={
                "started_at": started_at,
                "finished_at": time.perf_counter(),
                "elapsed_time": time.perf_counter() - started_at,
                "provider": "octobus",
            },
            status=ToolInvokeMessage.LogMessage.LogStatus.SUCCESS,
        )
        yield self.create_json_message(payload)

    def _fetch_parameter_options(self, parameter: str) -> list[ParameterOption]:
        client = OctoBusClient(OctoBusConfig.from_mapping(self.runtime.credentials))
        if parameter == "capset_id":
            return [
                ParameterOption(
                    value=capset.id,
                    label={"en_US": capset.label, "zh_Hans": capset.label},
                )
                for capset in client.list_capsets()
            ]
        if parameter != "capability":
            return []
        return [
            ParameterOption(
                value=capability.selection_value(),
                label={"en_US": capability.label, "zh_Hans": capability.label},
            )
            for capability in client.list_all_capabilities()
        ]
