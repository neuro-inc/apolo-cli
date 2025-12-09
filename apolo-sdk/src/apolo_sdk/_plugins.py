import enum
import numbers
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Union

from ._errors import ConfigError
from ._rewrite import rewrite_module


@rewrite_module
class ConfigScope(enum.Flag):
    GLOBAL = enum.auto()
    LOCAL = enum.auto()
    ALL = GLOBAL | LOCAL


_ParamType = Union[
    type[bool],
    type[numbers.Real],
    type[numbers.Integral],
    type[str],
    tuple[type[list[Any]], type[bool]],
    tuple[type[list[Any]], type[str]],
    tuple[type[list[Any]], type[numbers.Real]],
    tuple[type[list[Any]], type[numbers.Integral]],
]


@rewrite_module
class ConfigBuilder:
    _config_spec: dict[str, dict[str, tuple[_ParamType, ConfigScope]]]

    def __init__(self) -> None:
        self._config_spec = {}

    def _define_param(
        self,
        section: str,
        name: str,
        type: _ParamType,
        scope: ConfigScope,
    ) -> None:
        if section == "alias":
            raise ConfigError("Registering aliases is not supported yet.")
        if section in self._config_spec and name in self._config_spec[section]:
            raise ConfigError(f"Config parameter {section}.{name} already registered")
        self._config_spec.setdefault(section, {})
        self._config_spec[section][name] = (type, scope)

    def _get_spec(
        self, scope: ConfigScope = ConfigScope.ALL
    ) -> Mapping[str, Mapping[str, _ParamType]]:
        return {
            section: {name: val[0] for name, val in body.items() if val[1] & scope}
            for section, body in self._config_spec.items()
        }

    def define_int(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, numbers.Integral, scope)

    def define_bool(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, bool, scope)

    def define_str(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, str, scope)

    def define_float(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, numbers.Real, scope)

    def define_int_list(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, (list, numbers.Integral), scope)

    def define_bool_list(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, (list, bool), scope)

    def define_str_list(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, (list, str), scope)

    def define_float_list(
        self, section: str, name: str, *, scope: ConfigScope = ConfigScope.ALL
    ) -> None:
        self._define_param(section, name, (list, numbers.Real), scope)


@dataclass(frozen=True)
class _VersionRecord:
    package: str
    update_text: Callable[[str, str], str]
    exclusive: bool
    delay: float


@rewrite_module
class VersionChecker:
    def __init__(self) -> None:
        self._records: dict[str, _VersionRecord] = {}
        self._has_exclusive: bool = False

    def register(
        self,
        package: str,
        update_text: Callable[[str, str], str],
        *,
        exclusive: bool = False,
        delay: float = 0,
    ) -> None:
        record = _VersionRecord(package, update_text, exclusive, delay)
        if exclusive:
            if self._has_exclusive:
                package = next(iter(self._records))
                raise ConfigError(
                    f"Exclusive record for package {package} already exists"
                )
            self._records = {package: record}
            self._has_exclusive = True
        elif not self._has_exclusive:
            self._records[package] = record


@rewrite_module
class PluginManager:

    _config: ConfigBuilder
    _version_checker: VersionChecker

    def __init__(self) -> None:
        self._config = ConfigBuilder()
        self._version_checker = VersionChecker()

    @property
    def config(self) -> ConfigBuilder:
        return self._config

    @property
    def version_checker(self) -> VersionChecker:
        return self._version_checker
