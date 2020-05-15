from dataclasses import dataclass, field
from typing import Any, List, Tuple


@dataclass(frozen=True)
class SystemService:
    name: str
    enable: bool = True


@dataclass(frozen=True)
class KeyValue:
    key: str
    value: Any


class Repository(KeyValue):
    pass


class SysctlVariable(KeyValue):
    pass


class SSHConfigItem(KeyValue):
    pass


class KDumpOption(KeyValue):
    pass


@dataclass(frozen=True)
class SSHIdentity:
    name: str
    private_key: str
    public_key: str


@dataclass(frozen=True)
class Value:
    value: Any


class RcLocalScript(Value):
    pass


class SSHAuthorizedKey(Value):
    pass


class Package(Value):
    pass


@dataclass(frozen=True)
class SpecialPackage:
    name: str
    enable_repos: List[Repository] = field(default_factory=list)
    disable_repos: List[Repository] = field(default_factory=list)


class NTPServer(Value):
    pass


class TunedAdmProfile(Value):
    pass


@dataclass(frozen=True)
class VirtualGuest:
    name: str
    cpu_count: int = 4
    mem_size: int = 8192
    cpu_pinning: Tuple[Tuple[int, int], ...] = field(default_factory=tuple)
    # cpu_pinning is a tuple of tuples example :  [(0,0),(1,1)]
    # tuple consist of (real cpu, virtual cpu)


class _VariousOptions:
    def __init__(self, **kwargs):
        self.options = kwargs


class _NamedOptions(_VariousOptions):

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    def __str__(self):
        return f'{self.__class__.__name__} {self.name} [{self.options}]'


class KernelModule(_NamedOptions):
    pass
