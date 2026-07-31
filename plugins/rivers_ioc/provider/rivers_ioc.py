from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from rivers_client import RiversAPIError, RiversClient


class RiversIOCProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            # A public, non-sensitive address provides real authorization validation.
            RiversClient(credentials.get("api_key", "")).query_ip("1.1.1.1")
        except RiversAPIError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
