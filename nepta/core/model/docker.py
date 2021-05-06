from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from nepta.core.model import network
from nepta.core.model.network import IPv4Configuration, IPv6Configuration
from typing import List, Union


@dataclass
class DockerCredentials:
    username: str
    password: str
    registry: str = None


class Image(ABC):
    @abstractmethod
    def image_name(self):
        pass


@dataclass
class LocalImage(Image):
    name: str
    context: str
    dockerfile: str

    def image_name(self):
        return self.name


@dataclass
class RemoteImage(Image):
    repository: str
    tag: str = None

    def image_name(self):
        if self.tag:
            return f'{self.repository}:{self.tag}'
        else:
            return self.repository


@dataclass
class Volume:
    name: str


class GenericDockerSubnet(network.NetFormatter):
    def __init__(self, net):
        super(GenericDockerSubnet, self).__init__(net)
        self.gw = self.new_addr()

    @property
    def gw_ip(self):
        return self.gw.ip


class DockerSubnetV4(GenericDockerSubnet, network.NetperfNet4):
    pass


class DockerSubnetV6(GenericDockerSubnet, network.NetperfNet6):
    pass


@dataclass
class Network:
    name: str
    v4: Union[DockerSubnetV4, network.NetperfNet4] = None
    v6: Union[DockerSubnetV6, network.NetperfNet4] = None

    def __post_init__(self):
        if self.v4 and not isinstance(self.v4, DockerSubnetV4):
            self.v4 = DockerSubnetV4(self.v4)
        if self.v6 and not isinstance(self.v6, DockerSubnetV6):
            self.v6 = DockerSubnetV6(self.v6)

    def __str__(self):
        return f'Docker network: {self.name}\n\tV4: {self.v4}\n\tV6: {self.v6}\n'


@dataclass
class Container:
    DEFAULT_INHERIT_ENV = [
        'RSTRNT_JOBID',
        'TEST',
        'RSTRNT_OSDISTRO',
        'RSTRNT_OSARCH',
        'BEAKER_JOB_WHITEBOARD',
        'LAB_CONTROLLER',
        'BEAKER_RECIPE_ID',
        'BEAKER_HUB_URL',
        'TASKID',
        'RECIPE_URL',
    ]

    def __init__(self, image, hostname=None, network=None, volumes=None, extra_arguments=None, inherit_env=None):
        self.image = image
        self.hostname = hostname
        self.network = network
        self.volumes = volumes
        self.v4_conf = network.v4.new_config() if network is not None else None
        self.v6_conf = network.v6.new_config() if network is not None else None
        self.extra_arguments = extra_arguments
        self.inherit_env = inherit_env if inherit_env is not None else self.DEFAULT_INHERIT_ENV


class DockerDaemonSettings(dict):
    def __hash__(self):
        return hash(frozenset(self))
