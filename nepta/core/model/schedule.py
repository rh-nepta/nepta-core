import copy
import uuid
import logging

from collections import OrderedDict
from nepta.core.model.tag import HardwareInventoryTag, SoftwareInventoryTag

logger = logging.getLogger(__name__)


class Path(object):
    def __init__(self, mine_ip, their_ip, tags, cpu_pinning=None):
        self.mine_ip = mine_ip.ip
        self.their_ip = their_ip.ip
        self.cpu_pinning = cpu_pinning
        self.hw_inventory = [tag for tag in tags if isinstance(tag, HardwareInventoryTag)]
        self.sw_inventory = [tag for tag in tags if isinstance(tag, SoftwareInventoryTag)]

    def __repr__(self):
        return self.desc

    @property
    def tags(self):
        return self.hw_inventory + self.sw_inventory

    @property
    def id(self):
        sorted_tags = copy.deepcopy(self.tags)
        sorted_tags.sort()
        uid = uuid.uuid5(uuid.NAMESPACE_DNS, ','.join(map(str, sorted_tags)))
        logger.debug('Sorted tags : {}, generated uid: {}'.format(sorted_tags, uid))
        return uid

    @property
    def desc(self):
        return '{} {} <=> {}, tags:{}'.format(
            self.__class__.__name__, self.mine_ip, self.their_ip, (self.hw_inventory + self.sw_inventory)
        )

    def dict(self):
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


class PathList(list):
    def clone(self):
        return copy.deepcopy(self)

    def set_all_cpu_pinning(self, cpu_pinning, clone=True):
        new = self.clone() if clone else self
        for path in new:
            path.cpu_pinning = cpu_pinning
        return new

    def set_dynamic_duplex_stream_pinning(self, clone=True):
        new = self.clone() if clone else self
        for path in new:
            if path.cpu_pinning:
                path.cpu_pinning = (path.cpu_pinning[0], [path.cpu_pinning[0][0] + 1, path.cpu_pinning[0][1] + 1])
        return new

    def __add__(self, other):
        return self.__class__(super().__add__(other))


class ScenarioSettings(dict):
    def clone(self):
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
