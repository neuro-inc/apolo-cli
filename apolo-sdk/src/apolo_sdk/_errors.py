from typing import Any, Dict, Optional

from ._rewrite import rewrite_module


@rewrite_module
class ConfigError(RuntimeError):
    pass


@rewrite_module
class ClientError(Exception):
    pass


@rewrite_module
class IllegalArgumentError(ValueError):
    def __init__(self, *args: object, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(*args)
        self.payload = payload


@rewrite_module
class AuthError(ClientError):
    pass


@rewrite_module
class AuthenticationError(AuthError):
    pass


@rewrite_module
class AuthorizationError(AuthError):
    pass


@rewrite_module
class ResourceNotFound(ValueError):
    pass


@rewrite_module
class ServerNotAvailable(ValueError):
    pass


@rewrite_module
class BadGateway(ValueError):
    pass


@rewrite_module
class ConfigLoadException(Exception):
    pass


@rewrite_module
class NDJSONError(ValueError):
    pass


@rewrite_module
class NotSupportedError(NotImplementedError):
    pass


@rewrite_module
class StdStreamError(Exception):
    def __init__(self, exit_code: int) -> None:
        super().__init__(f"Stream finished with exit code {exit_code}")

        self.exit_code = exit_code
