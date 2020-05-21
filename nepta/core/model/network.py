import itertools
import ipaddress
import copy
from enum import Enum
from typing import List, Union, Any
from dataclasses import dataclass, field

from nepta.core.model.tag import SoftwareInventoryTag
from nepta.core.model import system

IpInterface = Union[ipaddress.IPv4Interface, ipaddress.IPv6Interface]
IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IpNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


class TabulatedStrFormatter:
    def __str__(self):
        return '{cls}\n\t{attrs}'.format(
            cls=self.__class__.__name__,
            attrs='\n\t'.join(
                ['{name}={value}'.format(
                    name=k, value=str(v).replace('\n', '\n\t')
                ) for k, v in self.__dict__.items() if k is not 'self']
            )
        )


@dataclass
class IPBaseConfiguration:
    addresses: List[IpInterface] = field(default_factory=list)
    gw: IpAddress = None
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
    CONF_OBJ = IPBaseConfiguration

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ip_gen = self.hosts()

    def new_addr(self) -> IpInterface:
        return ipaddress.ip_interface('{ip}/{prefix}'.format(ip=next(self._ip_gen), prefix=self.prefixlen))

    def new_addresses(self, n: int) -> List[IpInterface]:
        return [self.new_addr() for _ in range(n)]

    def new_config(self, num_of_ips=1) -> IPBaseConfiguration:
        return self.CONF_OBJ(self.new_addresses(num_of_ips))

    def subnets(self, prefixlen_diff=1, new_prefix=None):
        def new_gen(gen):
            for net in gen:
                yield self.__class__(net)

        olg_gen = super().subnets(prefixlen_diff, new_prefix)
        return new_gen(olg_gen)


class NetperfNet4(NetFormatter, ipaddress.IPv4Network):
    CONF_OBJ = IPv4Configuration


class NetperfNet6(NetFormatter, ipaddress.IPv6Network):
    CONF_OBJ = IPv6Configuration


class Interface(TabulatedStrFormatter):
    def __init__(self, name: str, v4_conf: IPv4Configuration = None, v6_conf: IPv6Configuration = None,
                 master_bridge: 'LinuxBridge' = None, mtu: int = 1500):
        self.name = name
        self.v4_conf = v4_conf
        self.v6_conf = v6_conf
        self.mtu = mtu
        self.master_bridge_name = master_bridge

    def clone(self):
        return copy.deepcopy(self)


class EthernetInterface(Interface):
    def __init__(self, name: str, mac: str, v4_conf: IPv4Configuration = None, v6_conf: IPv6Configuration = None,
                 bind_cores: List[int] = None, mtu: int = 1500):
        self.mac = mac.lower()
        self.bind_cores = bind_cores
        super().__init__(name, v4_conf, v6_conf, mtu=mtu)


class VlanInterface(Interface):
    def __init__(self, parrent: Interface, vlan_id: int, v4_conf: IPv4Configuration = None,
                 v6_conf: IPv6Configuration = None):
        self.vlan_id = vlan_id
        self.parrent = parrent.name
        name = f'{self.parrent}.{self.vlan_id}'
        super().__init__(name, v4_conf, v6_conf)


@dataclass
class GenericGuestTap:
    """
    This is virtual interface interconnecting VM with specific switch in the hypervisor.
    """
    guest: system.VirtualGuest
    switch: Any
    mac: str


@dataclass
class OVSGuestTap(GenericGuestTap):
    switch: 'OVSwitch'


@dataclass
class OVSGuestVlanTap(GenericGuestTap):
    vlan: int


@dataclass
class BridgeGuestTap(GenericGuestTap):
    switch: 'LinuxBridge'


class LinuxBridge(Interface):
    def add_interface(self, interface: Interface):
        interface.master_bridge_name = self.name


class TeamMasterInterface(Interface):
    LACP_RUNNER = (
        '{"runner": {"active": true, "link_watch": "ethotool", "fast_rate": true, "name": "lacp", '
        '"tx_hash": ["eth", "ipv4", "ipv6", "tcp"]}}'
    )
    ACT_BCKP_RUNNER = '{"runner": {"name": "activebackup", "link_watch": "ethtool"}}'

    def __init__(self, name: str, v4: IPv4Configuration = None, v6: IPv6Configuration = None, runner=LACP_RUNNER):
        super().__init__(name, v4, v6)
        self.runner = runner

    def add_interface(self, port: 'TeamChildInterface'):
        port.team = self.name


class TeamChildInterface(EthernetInterface):
    def __init__(self, original_interface: EthernetInterface):
        self.team = None
        super().__init__(original_interface.name, original_interface.mac)


#
# Bond
#
class BondMasterInterface(Interface):
    LACP_BOND_OPTS = 'mode=4 xmit_hash_policy=1'
    ACT_BCKP_BOND_OPTS = 'mode=1'

    def __init__(self, name: str, v4_conf: IPv4Configuration = None, v6_conf: IPv6Configuration = None,
                 bond_opts=LACP_BOND_OPTS):
        super().__init__(name, v4_conf, v6_conf)
        self.bond_opts = bond_opts

    def add_interface(self, interface: Interface):
        interface.master_bond = self.name


class BondChildInterface(EthernetInterface):
    def __init__(self, original_interface: EthernetInterface):
        super().__init__(original_interface.name, original_interface.mac)
        self.master_bond = None


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
    endpoint_ip: IpInterface = None
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
    _COUNTER = itertools.count()

    @property
    def name(self):
        '''
        Returned connection name must be unique across all connections.
        '''
        return f'wg{self.index}'

    @property
    def tags(self):
        return [
            SoftwareInventoryTag('WireGuard'),
            SoftwareInventoryTag(self.name),
        ]


class IPsecTunnel(object):
    MODE_TRANSPORT = 'transport'
    MODE_TUNNEL = 'tunnel'

    PHASE2_ESP = 'esp'
    PHASE2_AH = 'ah'

    ENCAPSULATION_YES = 'yes'
    ENCAPSULATION_NO = 'no'

    OFFLOAD_YES = 'yes'
    OFFLOAD_NO = 'no'
    OFFLOAD_AUTO = 'auto'

    @classmethod
    def generate_tunnels(cls, addrs1: IPBaseConfiguration, addrs2: IPBaseConfiguration, properties: List[dict]):
        return [cls(addr1, addr2, **prop) for addr1, addr2, prop in zip(addrs1, addrs2, properties)]

    def __init__(
        self,
        left_ip,
        right_ip,
        cipher,
        passphrase,
        mode=MODE_TRANSPORT,
        phase2=PHASE2_ESP,
        replay_window=None,
        encapsulation=ENCAPSULATION_NO,
        nic_offload=OFFLOAD_NO,
    ):
        if not isinstance(left_ip, ipaddress._BaseAddress) or not isinstance(right_ip, ipaddress._BaseAddress):
            raise TypeError('Left and Right IP address should be object from ipaddress module')
        self.left_ip = left_ip
        self.right_ip = right_ip
        self.cipher = cipher
        self.phase2 = phase2
        self.passphrase = passphrase
        self.mode = mode
        self.encapsulation = encapsulation
        self.nic_offload = nic_offload

        # The default is kernel stack specific, but usually 32. Linux
        # NETKEY/XFRM allows at least up to 2048. A value of of 0 disables
        # replay protection.
        self.replay_window = replay_window

    def __str__(self):
        replay_window_str = 'default' if self.replay_window is None else '%d' % self.replay_window
        return (
            'IPSec %s tunnel %s <=> %s, [%s]cipher: %s, mode: %s, replay-window: %s, nat-traversal: %s, '
            'nic-offload %s'
            % (
                self.family,
                self.left_ip,
                self.right_ip,
                self.phase2,
                self.cipher,
                self.mode,
                replay_window_str,
                self.encapsulation,
                self.nic_offload,
            )
        )

    @property
    def family(self):
        if self.left_ip.version == 6:
            return 'IPv6'
        else:
            return 'IPv4'

    @property
    def name(self):
        '''
        Returned connection name must be unique accross all IPsec connections
        in this testing framework.

        The name of a connection is used in ipsec configuration.
        '''
        return (
            f'{self.family}_{self.mode}_{self.cipher}_encap-{self.encapsulation}_'
            f'{self.left_ip.ip}_{self.right_ip.ip}'
        )

    @property
    def tags(self):
        tags = [SoftwareInventoryTag(self.family), SoftwareInventoryTag('IPsec')]
        tags.append(SoftwareInventoryTag(self.mode.capitalize()))
        if self.encapsulation == self.ENCAPSULATION_YES:
            tags.append(SoftwareInventoryTag('NatTraversal'))
        if self.replay_window:
            tags.append(SoftwareInventoryTag('ReplayWindow', self.replay_window))
        if self.nic_offload != self.OFFLOAD_NO:
            tags.append(SoftwareInventoryTag('NicOffload', self.nic_offload))
        tags.append(SoftwareInventoryTag(self.cipher))
        return tags


class RouteGeneric(object):
    @classmethod
    def from_path(cls, path, interfaces):
        destination = None
        interface = None
        for i in interfaces:
            if path.mine_ip in cls._get_ip_from_iface(i):
                destination = path.their_ip
                interface = i
            if path.their_ip in cls._get_ip_from_iface(i):
                destination = path.mine_ip
                interface = i

        return cls._construct_route(destination, interface)

    @classmethod
    def _get_ip_from_iface(cls, iface):
        raise NotImplementedError

    @classmethod
    def _get_route_metric(cls, iface):
        raise NotImplementedError

    @classmethod
    def _construct_route(cls, destination, interface):
        raise NotImplementedError

    def __init__(self, destination, interface, gw=None, metric=0):
        self._destination = destination
        self._interface = interface
        self._gw = gw.ip if isinstance(gw, (ipaddress.IPv4Interface, ipaddress.IPv6Interface)) else gw
        self._metric = metric

    def __str__(self):
        type_string = self.__class__.__name__
        r = '%s %s' % (type_string, self._destination)
        if self._gw is not None:
            r += ' via %s' % self._gw
        r += ' dev %s' % self._interface.name
        r += ' metric %s' % self._metric
        return r

    def get_destination(self):
        return self._destination

    def get_interface(self):
        return self._interface

    def get_gateway(self):
        return self._gw

    def get_metric(self):
        return self._metric


class Route4(RouteGeneric):
    @classmethod
    def _get_ip_from_iface(cls, iface):
        if iface.v4_conf:
            return [interface.ip for interface in iface.v4_conf.addresses]
        else:
            return []

    @classmethod
    def _construct_route(cls, destination, interface, metric=0):
        return Route4(destination, interface, metric=metric)


class Route6(RouteGeneric):
    @classmethod
    def _get_ip_from_iface(cls, iface):
        if iface.v6_conf:
            return [interface.ip for interface in iface.v6_conf.addresses]
        else:
            return []

    @classmethod
    def _construct_route(cls, destination, interface, metric=1):
        return Route6(destination, interface, metric=metric)


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
    remote_ip = IpAddress
    key: Any = ''


class OVSIntPort(Interface):
    def __init__(self, name: str, ovs_switch: OVSwitch, v4_conf: IPv4Configuration = None,
                 v6_conf: IPv6Configuration = None):
        self.ovs_switch = ovs_switch
        super(OVSIntPort, self).__init__(name, v4_conf, v6_conf)
