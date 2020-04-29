from dataclasses import dataclass


@dataclass(frozen=True)
class _AbstractService:
    name: str
    enable: bool


class SysVInitService(_AbstractService):
    pass


class SystemdService(_AbstractService):
    pass


class KeyValue(object):
    def __init__(self, key, value):
        self._key = key
        self._value = value

    def __str__(self):
        return '%s %s=%s' % (self.__class__.__name__, self._key, self._value)

    def __repr__(self):
        return self.__str__()

    def get_key(self):
        return self._key

    def get_value(self):
        return self._value

    @property
    def key(self):
        return self._key

    @property
    def value(self):
        return self._value


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


class Value(object):

    def __init__(self, value):
        self._value = value

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, self._value)

    def get_value(self):
        return self._value

    @property
    def value(self):
        return self._value


class RcLocalScript(Value):
    pass


class SSHAuthorizedKey(Value):
    pass


class Package(Value):
    pass


class SpecialPackage(Package):

    def __init__(self, name, enable_repos=None, disable_repos=None):
        super().__init__(name)
        self.disable_repos = list(disable_repos) if disable_repos else []
        self.enable_repos = list(enable_repos) if enable_repos else []

    def __str__(self):
        return f"{self.__class__.__name__}: {self.value}, enable repos: {self.enable_repos}, " \
               f"disabled repos: {self.disable_repos}"


class NTPServer(Value):
    pass


class TunedAdmProfile(Value):
    pass


class VirtualGuest(object):

    # TODO : refactor to dataclass
    def __init__(self, name, cpu_count=4, mem_size=8192, cpu_pinning=None):
        self._name = name
        self._cpu_count = cpu_count
        self._mem_size = mem_size
        self._cpu_pinning = cpu_pinning
        # self._cpu_pinning is list of tuples example :  [(0,0),(1,1)]
        # tuple consist of (real cpu, virtual cpu)

    def __str__(self):
        return 'Virtual guest %s >> num of pcu : %s, memory : %s MB, cpu pinning : %s ' \
               % (self._name, self._cpu_count, self._mem_size, self._cpu_pinning)

    @property
    def name(self):
        return self._name

    def get_name(self):
        return self._name

    @property
    def cpu_count(self):
        return self._cpu_count

    def get_cpu_count(self):
        return self._cpu_count

    @property
    def mem_size(self):
        return self._mem_size

    def get_mem_size(self):
        return self._mem_size

    @property
    def cpu_pinning(self):
        return self._cpu_pinning

    def get_cpu_pinning(self):
        return self._cpu_pinning


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


if __name__ == '__main__':
    print(SystemdService('Network', SystemdService.ENABLED))
    print(SysVInitService('Network', SysVInitService.ENABLED))
    print(SysctlVariable('net.ipv4.ip_forward', 1))
    print(VirtualGuest('virt0'))
