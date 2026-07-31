from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from client.octobus import OctoBusClient, OctoBusConfig, OctoBusError


class OctoBusProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            client = OctoBusClient(OctoBusConfig.from_mapping(credentials))
            client.status()
            # Status is intentionally public in OctoBus. Listing capsets also
            # verifies that the configured admin token can access discovery.
            client.list_capsets()
        except OctoBusError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
