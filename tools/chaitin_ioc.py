import logging
from collections.abc import Generator
from typing import Any

import httpx
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ChaitinIOCTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        api_key = self.runtime.credentials["api_key"]
        ip_address = tool_parameters.get("ip_address")
        api_base = "https://intelligence.rivers.chaitin.cn/api/v1/ip_info?ip={IPAddress}"
        if not api_key or not ip_address:
            yield self.create_text_message("baichuancloud api_key or argument ip address is empty")
            return
        logger.debug(f"API_URL: {api_base.format(IPAddress=ip_address)}")
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "X-CA-Token": f"{api_key}",
        }

        try:
            with httpx.Client() as client:
                r = client.get(
                    api_base.format(IPAddress=ip_address),
                    headers=headers,
                )
                logger.debug(f"response: {r.text}")
                result = str(r.json())

                yield self.create_text_message(result)
        except Exception as e:
            logger.error(f"error: {e}", exc_info=True)
            yield self.create_text_message(f"error: {e}")
