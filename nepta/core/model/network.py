import abc
import itertools
import ipaddress
import copy
from uuid import uuid5, UUID
from collections import defaultdict
from enum import Enum
from typing import List, Union, Any, Optional, Iterator, Dict
from dataclasses import dataclass, field

from nepta.core.model.tag import SoftwareInventoryTag
from nepta.core.model import system
from nepta.core.model.schedule import Path

IpInterface = Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]
IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IpNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


@dataclass
class IPBaseConfiguration:
    addresses: List[IpInterface] = field(default_factory=list)
    gw: Optional[IpAddress] = None
    dns: List[IpAddress] = field(default_factory=list)

    def __iter__(self):
        return iter(self.addresses)

    def __getitem__(self, item):
        return self.addresses[item] if self.addresses else None


class IPv4Configuration(IPBaseConfiguration):
    pass


class IPv6Configuration(IPBaseConfiguration):
    pass


class NetFormatter(ipaddress._BaseNetwork):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ip_gen = self.hosts()

    def new_addr(self) -> IpInterface:
        return ipaddress.ip_interface('{ip}/{prefix}'.format(ip=next(self._ip_gen), prefix=self.prefixlen))

    def new_addresses(self, n: int) -> List[IpInterface]:
        return [self.new_addr() for _ in range(n)]

    def new_config(self, num_of_ips=1) -> IPBaseConfiguration:
        return IPBaseConfiguration(self.new_addresses(num_of_ips))

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        for net in super().subnets(prefixlen_diff, new_prefix):
            yield self.__class__(net)


class NetperfNet4(NetFormatter, ipaddress.IPv4Network):
    def new_config(self, num_of_ips=1) -> IPv4Configuration:
        return IPv4Configuration(self.new_addresses(num_of_ips))


class NetperfNet6(NetFormatter, ipaddress.IPv6Network):
    def new_config(self, num_of_ips=1) -> IPv6Configuration:
        return IPv6Configuration(self.new_addresses(num_of_ips))


class Interface:
    _UUID_NAMESPACE = UUID('139c4235-0719-4df9-9b24-851654118d38')

    def __init__(
        self,
        name: str,
        v4_conf: Optional[IPv4Configuration] = None,
        v6_conf: Optional[IPv6Configuration] = None,
        master_bridge: Optional['LinuxBridge'] = None,
        mtu: int = 1500,
    ):
        self.name = name
        self.v4_conf = v4_conf
        self.v6_conf = v6_conf
        self.mtu = mtu
        self.master_bridge = master_bridge
        self._routes: Dict[str, List[RouteGeneric]] = defaultdict(list)

    def __str__(self):
        attrs = dict(self.__dict__)
        v4 = attrs.pop('v4_conf')
        v6 = attrs.pop('v6_conf')
        return f'{self.__class__.__name__} >> {attrs}\n\tv4_conf: {v4}\n\tv6_conf: {v6}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name})'

    def clone(self):
        return copy.deepcopy(self)

    @property
    def uuid(self) -> UUID:
        return uuid5(self._UUID_NAMESPACE, str(self))

    def add_route(self, route: 'RouteGeneric'):
        self._routes[route.__class__.__name__].append(route)

    def del_route(self, route: 'RouteGeneric'):
        self._routes[route.__class__.__name__].remove(route)


class EthernetInterface(Interface):
    def __init__(
        self,
        name: str,
        mac: str,
        v4_conf: Optional[IPv4Configuration] = None,
        v6_conf: Optional[IPv6Configuration] = None,
        bind_cores: Optional[List[int]] = None,
        mtu: int = 1500,
        offloads: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, v4_conf, v6_conf, mtu=mtu)
        self.mac = mac.lower()
        self.bind_cores = bind_cores
        self.offloads = offloads if offloads else dict()


class VlanInterface(Interface):
    def __init__(
        self,
        parent: Interface,
        vlan_id: int,
        v4_conf: Optional[IPv4Configuration] = None,
        v6_conf: Optional[IPv6Configuration] = None,
    ):
        name = f'{parent.name}.{vlan_id}'
        super().__init__(name, v4_conf, v6_conf)
        self.vlan_id = vlan_id
        self.parent = parent.name


@dataclass
class GenericGuestTap:
    """
    This is virtual interface interconnecting VM with specific switch in the hypervisor.
    """

    guest: system.VirtualGuest
    switch: Any
    mac: str

    def __repr__(self):
        return f'{self.__class__.__name__}_{self.guest.name}_{self.switch.name}_{self.mac}'


@dataclass(repr=False)
class OVSGuestTap(GenericGuestTap):
    switch: 'OVSwitch'


@dataclass
class OVSGuestVlanTap(GenericGuestTap):
    vlan: int

    def __repr__(self):
        return super().__repr__() + f'_{self.vlan}'


@dataclass(repr=False)
class BridgeGuestTap(GenericGuestTap):
    switch: 'LinuxBridge'


class LinuxBridge(Interface):
    def add_interface(self, interface: Interface):
        interface.master_bridge = self


class TeamMasterInterface(Interface):
    class Runner(Enum):
        LACP = (
            '{"runner": {"active": true, "link_watch": "ethotool", "fast_rate": true, "name": "lacp", '
            '"tx_hash": ["eth", "ipv4", "ipv6", "tcp"]}}'
        )
        ACT_BCKP = '{"runner": {"name": "activebackup", "link_watch": "ethtool"}}'

    def __init__(
        self,
        name: str,
        v4_conf: Optional[IPv4Configuration] = None,
        v6_conf: Optional[IPv6Configuration] = None,
        runner: Runner = Runner.LACP,
    ):
        super().__init__(name, v4_conf, v6_conf)
        self.runner = runner

    def add_interface(self, port: 'TeamChildInterface'):
        port.team = self.name


class TeamChildInterface(EthernetInterface):
    def __init__(self, original_interface: EthernetInterface):
        super().__init__(original_interface.name, original_interface.mac)
        self.team: str = ''


#
# Bond
#
class BondMasterInterface(Interface):
    class BondOpts(Enum):
        LACP = 'mode=4 xmit_hash_policy=1'
        ACT_BCKP = 'mode=1'

    def __init__(
        self,
        name: str,
        v4_conf: Optional[IPv4Configuration] = None,
        v6_conf: Optional[IPv6Configuration] = None,
        bond_opts: BondOpts = BondOpts.LACP,
    ):
        super().__init__(name, v4_conf, v6_conf)
        self.bond_opts = bond_opts

    def add_interface(self, interface: 'BondChildInterface'):
        interface.master_bond = self.name


class BondChildInterface(EthernetInterface):
    def __init__(self, original_interface: EthernetInterface):
        super().__init__(original_interface.name, original_interface.mac)
        self.master_bond: str = ''


@dataclass
class WireGuardPeer:
    """
    Represents peer in the configuration. Keys are generated using `wg` command. For more details see wireguard doc.
    private key >>  wg genkey > private
    public key  >>  wg pubkey < private > public
    """

    public_key: str
    private_key: str
    allowed_ips: List[IpNetwork]
    endpoint_ip: Optional[IpInterface] = None
    endpoint_port: int = 51820

    @property
    def endpoint(self):
        return f'{self.endpoint_ip.ip}:{self.endpoint_port}'


@dataclass
class WireGuardTunnel:
    """
    Also called wireguard interface.
    """

    local_ip: IpInterface
    private_key: str
    local_port: int = 51820
    peers: List[WireGuardPeer] = field(default_factory=list)
    # this is unique index generated by class counter incremented by each new object
    index: int = field(init=False, default_factory=lambda: next(WireGuardTunnel._COUNTER))

    # this is used to assign unique int to each wiregaurd tunnel
    _COUNTER: Iterator[int] = itertools.count()

    @property
    def name(self):
        """
        Returned connection name must be unique across all connections.
        """
        return f'wg{self.index}'

    @property
    def tags(self):
        return [
            SoftwareInventoryTag('WireGuard'),
            SoftwareInventoryTag(self.name),
        ]


@dataclass
class IPsecTunnel:
    class Mode(Enum):
        TRANSPORT = 'transport'
        TUNNEL = 'tunnel'

    class Phase2(Enum):
        ESP = 'esp'
        AH = 'ah'

    class Encapsulation(Enum):
        YES = 'yes'
        NO = 'no'

    class Offload(Enum):
        YES = 'yes'
        NO = 'no'
        AUTO = 'auto'

    # IPsec tunnel attribute definition with type hints
    left_ip: IpInterface
    right_ip: IpInterface
    cipher: str
    passphrase: str
    mode: Mode = Mode.TRANSPORT
    phase2: Phase2 = Phase2.ESP
    # The default is kernel stack specific, but usually 32. Linux
    # NETKEY/XFRM allows at least up to 2048. A value of of 0 disables
    # replay protection.
    replay_window: Optional[int] = None
    encapsulation: Encapsulation = Encapsulation.NO
    nic_offload: Offload = Offload.NO

    @classmethod
    def generate_tunnels(cls, addrs1: IPBaseConfiguration, addrs2: IPBaseConfiguration, properties: List[dict]):
        return [cls(addr1, addr2, **prop) for addr1, addr2, prop in zip(addrs1, addrs2, properties)]

    def __str__(self):
        replay_window_str = 'default' if self.replay_window is None else str(self.replay_window)
        return (
            f'IPSec {self.family} tunnel {self.left_ip} <=> {self.right_ip}, [{self.phase2.value}], '
            f'cipher: {self.cipher}, mode: {self.mode.value}, replay-window: {replay_window_str}, '
            f'nat-traversal: {self.encapsulation.value}, nic-offload {self.nic_offload.value}'
        )

    @property
    def family(self):
        if self.left_ip.version == 6:
            return 'IPv6'
        else:
            return 'IPv4'

    @property
    def name(self):
        """
        Returned connection name have to be unique across all IPsec connections
        in this testing framework. This is achieved by source and destination IP
        address combination.

        :return The name of this connection is used in ipsec configuration.
        """
        return (
            f'{self.family}_{self.mode.value}_{self.cipher}_encap-{self.encapsulation.value}_'
            f'{self.left_ip.ip}_{self.right_ip.ip}'
        )

    @property
    def tags(self):
        tags = [
            SoftwareInventoryTag(self.family),
            SoftwareInventoryTag('IPsec'),
            SoftwareInventoryTag(self.mode.value.capitalize()),
        ]
        if self.encapsulation == self.Encapsulation.YES:
            tags.append(SoftwareInventoryTag('NatTraversal'))
        if self.replay_window:
            tags.append(SoftwareInventoryTag('ReplayWindow', self.replay_window))
        if self.nic_offload != self.Offload.NO:
            tags.append(SoftwareInventoryTag('NicOffload-yes'))
        tags.append(SoftwareInventoryTag(self.cipher))
        return tags


@dataclass
class RouteGeneric(abc.ABC):
    destination: IpNetwork
    interface: Interface
    gw: Optional[IpAddress] = None
    metric: int = 0

    def __post_init__(self):
        self.interface.add_route(self)

    def __del__(self):
        self.interface.del_route(self)

    @classmethod
    def from_path(cls, path: Path, interfaces: List[Interface]):
        for i in interfaces:
            if path.mine_ip in cls._get_ip_from_iface(i):
                return cls(path.their_ip, i)
            if path.their_ip in cls._get_ip_from_iface(i):
                return cls(path.mine_ip, i)

    @classmethod
    @abc.abstractmethod
    def _get_ip_from_iface(cls, iface: Interface) -> List[IpAddress]:
        pass

    def __str__(self):
        return '{cls} {dest} {gw} dev {dev} metric {metric}'.format(
            cls=self.__class__.__name__,
            dev=self.interface.name,
            metric=self.metric,
            dest=self.destination,
            gw='' if self.gw is None else f'dev {self.gw}',
        )


class Route4(RouteGeneric):
    @classmethod
    def _get_ip_from_iface(cls, iface):
        if iface.v4_conf:
            return [interface.ip for interface in iface.v4_conf.addresses]
        else:
            return []


class Route6(RouteGeneric):
    @classmethod
    def _get_ip_from_iface(cls, iface):
        if iface.v6_conf:
            return [interface.ip for interface in iface.v6_conf.addresses]
        else:
            return []


@dataclass
class OVSwitch:
    name: str
    interfaces: List[Interface] = field(default_factory=list)
    tunnels: List['OVSTunnel'] = field(default_factory=list)

    def add_interface(self, iface: Interface):
        self.interfaces.append(iface)

    def add_tunnel(self, tunnel: 'OVSTunnel'):
        self.tunnels.append(tunnel)


@dataclass
class OVSTunnel:
    class OVSTunnelTypes(Enum):
        VXLAN = 'vxlan'
        GRE = 'gre'
        GENEVE = 'geneve'
        GREoIPSEC = 'ipsec_gre'

    name: str
    type: OVSTunnelTypes
    remote_ip: IpAddress
    key: Any = ''


class OVSIntPort(Interface):
    def __init__(
        self,
        name: str,
        ovs_switch: OVSwitch,
        v4_conf: Optional[IPv4Configuration] = None,
        v6_conf: Optional[IPv6Configuration] = None,
    ):
        self.ovs_switch = ovs_switch
        super(OVSIntPort, self).__init__(name, v4_conf, v6_conf)
