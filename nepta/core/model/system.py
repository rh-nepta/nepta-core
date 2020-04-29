from dataclasses import dataclass, field
from typing import Any, List, Tuple


@dataclass(frozen=True)
class _AbstractService:
    name: str
    enable: bool = True


class SysVInitService(_AbstractService):
    pass


class SystemdService(_AbstractService):
    pass


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


# This class can basically inherit from KeyValue... but it does not because
# of readability
class SSHIdentity(object):

    def __init__(self, priv_key, pub_key):
        self._priv_key = priv_key
        self._pub_key = pub_key

    def get_private_key(self):
        return self._priv_key

    @property
    def identity(self):
        return self._priv_key

    @property
    def pubkey(self):
        return self._pub_key

    def get_public_key(self):
        return self._pub_key


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
    cpu_count: int
    mem_size: int
    cpu_count: List[Tuple[int, int], ...] = None
    # cpu_pinning is list of tuples example :  [(0,0),(1,1)]
    # tuple consist of (real cpu, virtual cpu)


class _VariousOptions:
    def __init__(self, **kwargs):
        self.options = kwargs


class _NamedOptions(_VariousOptions):

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    def __str__(self):
        return f"{self.__class__.__name__} {self.name} [{self.options}]"


class KernelModule(_NamedOptions):
    pass
