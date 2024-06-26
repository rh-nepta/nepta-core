import copy
import uuid
import logging
import ipaddress as ia
from collections import OrderedDict
from typing import Union, List, Sequence, Optional, Any
from abc import ABC, abstractmethod

from nepta.core.model.tag import HardwareInventoryTag, SoftwareInventoryTag

logger = logging.getLogger(__name__)


class _PathInterface(ABC):
    _hw_inventory: List[HardwareInventoryTag] = []
    _sw_inventory: List[SoftwareInventoryTag] = []

    @property
    def hw_inventory(self) -> List[HardwareInventoryTag]:
        return self._hw_inventory

    @property
    def sw_inventory(self) -> List[SoftwareInventoryTag]:
        return self._sw_inventory

    @property
    def tags(self) -> List[Union[HardwareInventoryTag, SoftwareInventoryTag]]:
        return self.hw_inventory + self.sw_inventory

    @property
    def id(self) -> uuid.UUID:
        sorted_tags = copy.deepcopy(self.tags)
        sorted_tags.sort()
        uid = uuid.uuid5(uuid.NAMESPACE_DNS, ','.join(map(str, sorted_tags)))
        logger.debug('Sorted tags : {}, generated uid: {}'.format(sorted_tags, uid))
        return uid

    def __repr__(self):
        return self.desc

    @property
    @abstractmethod
    def desc(self) -> str:
        pass

    @abstractmethod
    def dict(self) -> dict:
        pass


class Path(_PathInterface):
    def __init__(
        self,
        mine_ip: Union[ia.IPv4Interface, ia.IPv6Interface],
        their_ip: Union[ia.IPv4Interface, ia.IPv6Interface],
        tags: List[Union[HardwareInventoryTag, SoftwareInventoryTag]],
        cpu_pinning: Optional[Sequence[Sequence[int]]] = None,
    ):
        self.mine_ip = mine_ip
        self.their_ip = their_ip
        self.cpu_pinning = cpu_pinning
        self._hw_inventory = [tag for tag in tags if isinstance(tag, HardwareInventoryTag)]
        self._sw_inventory = [tag for tag in tags if isinstance(tag, SoftwareInventoryTag)]

    @property
    def desc(self) -> str:
        return '{} {} <=> {}, tags:{}'.format(
            self.__class__.__name__, self.mine_ip, self.their_ip, (self.hw_inventory + self.sw_inventory)
        )

    def dict(self) -> dict:
        return OrderedDict(uuid=self.id, srcip=self.mine_ip, dstip=self.their_ip, desc=self.desc)


class CongestedPath(Path):
    def __init__(self, mine_ip, their_ip, limit_bandwidth, delay, cca, tags, cpu_pinning=None):
        path_tags = [
            SoftwareInventoryTag('delay', delay),
            SoftwareInventoryTag('bandwidth', limit_bandwidth),
            SoftwareInventoryTag('congestion_control_alg', cca),
        ]
        super().__init__(mine_ip, their_ip, tags + path_tags, cpu_pinning)
        self.limit_bandwidth = limit_bandwidth
        self.delay = delay
        self.cca = cca

    def dict(self):
        d = super().dict()
        d['delay'] = self.delay
        d['bandwidth'] = self.limit_bandwidth
        return d


class UBenchPath(Path):
    cpu_pinning: Sequence[Sequence[Any]]

    def __init__(self, mine_ip, their_ip, tags, cpu_pinning, irq_settings):
        super().__init__(mine_ip, their_ip, tags, cpu_pinning)
        self.irq_settings = irq_settings


class PathList(list, _PathInterface):
    def clone(self) -> 'PathList':
        return copy.deepcopy(self)

    def set_all_cpu_pinning(self, cpu_pinning, clone=True) -> 'PathList':
        new = self.clone() if clone else self
        for path in new:
            path.cpu_pinning = cpu_pinning
        return new

    def set_dynamic_duplex_stream_pinning(self, clone=True) -> 'PathList':
        new = self.clone() if clone else self
        for path in new:
            if path.cpu_pinning:
                path.cpu_pinning = (path.cpu_pinning[0], [path.cpu_pinning[0][0] + 1, path.cpu_pinning[0][1] + 1])
        return new

    def __add__(self, other) -> 'PathList':
        return self.__class__(super().__add__(other))

    @property
    def hw_inventory(self) -> List[HardwareInventoryTag]:
        return list(set(sum([path.hw_inventory for path in self], [])))

    @property
    def sw_inventory(self) -> List[SoftwareInventoryTag]:
        return list(set(sum([path.sw_inventory for path in self], [])))

    def dict(self) -> dict:
        return OrderedDict(uuid=self.id, desc=self.desc, len=len(self))

    @property
    def desc(self) -> str:
        return '[[' + ', '.join([p.desc for p in self]) + ']]'

    @property
    def cpu_pinning(self):
        cpu = [p.cpu_pinning for p in self]
        return cpu if all(cpu) else None


class ParallelPathList(list):
    pass


class ScenarioSettings(dict):
    def clone(self) -> dict:
        return copy.deepcopy(self)


class RsyncHost(object):
    def __init__(self, server, destination, attempt_delays=None):
        """
        This objects represents sending destination of created nepta-dataformat package.
        :param server: URL or IP address of server
        :param destination: system path in server to store package
        :param attempt_delays: list of delays between rsync attempts to send data, time in minutes !!!
        """
        self.server = server
        self.destination = destination
        self.attempt_delays = attempt_delays if attempt_delays is not None else [0]

    def __repr__(self):
        return f'{self.__class__.__name__}: {self.__dict__}'

    def __str__(self):
        return f'{self.__class__.__name__}: server address: {self.server}, destination: {self.destination}'
