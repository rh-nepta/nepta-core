import ipaddress
import copy
from typing import List
from dataclasses import dataclass, field

from nepta.core.model.tag import SoftwareInventoryTag


@dataclass
class IPBaseConfiguration:
    addresses: List[ipaddress._BaseAddress] = field(default_factory=list)
    gw: ipaddress._BaseAddress = None
    dns: List[ipaddress._BaseAddress] = field(default_factory=list)

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

    def new_addr(self) -> ipaddress._BaseAddress:
        return ipaddress.ip_interface('{ip}/{prefix}'.format(ip=next(self._ip_gen), prefix=self.prefixlen))

    def new_addresses(self, n: int) -> List[ipaddress._BaseAddress]:
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


class Interface(object):

    def __init__(self, name, v4_conf=None, v6_conf=None, mtu=1500):
        self.name = name
        self.v4_conf = v4_conf
        self.v6_conf = v6_conf
        self.mtu = mtu

    def __str__(self):
        return self.make_iface_string() + ':\n\t' + self.make_v4_addr_string() + '\n\t' + self.make_v6_addr_string()

    def make_iface_string(self):
        return 'Internet interface %s' % self.name

    @staticmethod
    def _make_addr_str(addr_list):
        ret_str = ''
        if addr_list is not None:
            for addr in addr_list.addresses:
                ret_str += addr.with_prefixlen
                ret_str += ", "
            if addr_list.gw:
                ret_str += 'GW=%s, ' % addr_list.gw
            if len(addr_list.dns):
                ret_str += 'DNS: '
                for dns in addr_list.dns:
                    ret_str += dns.compressed + ', '
        return ret_str

    def make_v4_addr_string(self):
        s = 'IPv4 adresses: ' + self._make_addr_str(self.v4_conf)
        return s

    def make_v6_addr_string(self):
        s = 'IPv6 adresses: ' + self._make_addr_str(self.v6_conf)
        return s

    def clone(self):
        return copy.deepcopy(self)


class EthernetInterface(Interface):

    def __init__(self, name, mac, v4_conf=None, v6_conf=None, bind_cores=None, mtu=1500):
        self.mac = mac
        if self.mac is not None:
            self.mac = self.mac.lower()
        self.master_bridge_name = None
        # TODO check where this is used and test it if it is functional?
        self.bind_cores = bind_cores
        super(EthernetInterface, self).__init__(name, v4_conf, v6_conf, mtu)

    def make_iface_string(self):
        return 'Ethernet interface %s, MAC:%s, Bridge: %s, MTU: %s' % \
               (self.name, self.mac, self.master_bridge_name, self.mtu)


class VlanInterface(EthernetInterface):

    def __init__(self, parrent, vlan_id, v4_conf=None, v6_conf=None):
        self.vlan_id = vlan_id
        self.parrent = parrent
        name = '%s.%s' % (self.parrent.name, self.vlan_id)
        super(VlanInterface, self).__init__(name, None, v4_conf, v6_conf)

    def make_iface_string(self):
        return 'Ethernet vlan interface %s, vlan id: %s, parrent name: %s' % (
            self.name, self.vlan_id, self.parrent.name)


#
# Guest taps for virtual guests
#
class GenericGuestTap(object):

    def __init__(self, guest, switch, mac):
        self.switch = switch
        self.guest = guest
        self.mac = mac

    def __str__(self):
        return '%s. MAC: %s, Switch: %s, guest: %s' % (
            self.__class__.__name__, self.mac, self.switch.name, self.guest)

    def __repr__(self):
        return "%s_%s_%s" % (self.switch.name, self.guest.name, self.mac)


class OVSGuestTap(GenericGuestTap):
    pass


class OVSGuestVlanTap(GenericGuestTap):
    def __init__(self, guest, switch, mac, vlan):
        super(OVSGuestVlanTap, self).__init__(guest, switch, mac)
        self.vlan = vlan

    def __repr__(self):
        return super().__repr__() + "_v%s" % self.vlan


class BridgeGuestTap(GenericGuestTap):
    pass


#
# Bridge
#
class LinuxBridge(EthernetInterface):

    def __init__(self, name, v4_conf=None, v6_conf=None):
        super(LinuxBridge, self).__init__(name, None, v4_conf, v6_conf)

    def add_interface(self, interface):
        interface.master_bridge_name = self.name

    def make_iface_string(self):
        return 'Bridge interface %s' % self.name


#
# TEAM objects
#
class TeamMasterInterface(EthernetInterface):
    LACP_RUNNER = '{"runner": {"active": true, "link_watch": "ethotool", "fast_rate": true, "name": "lacp", ' \
                  '"tx_hash": ["eth", "ipv4", "ipv6", "tcp"]}}'
    ACT_BCKP_RUNNER = '{"runner": {"name": "activebackup", "link_watch": "ethtool"}}'

    def __init__(self, name, v4=None, v6=None, runner=LACP_RUNNER):
        super(TeamMasterInterface, self).__init__(name, None, v4, v6)
        self.runner = runner

    def make_iface_string(self):
        return "Team master interface: %s\n\tRunner JSON dump: %s asdf" % (self.name, self.runner)

    def add_interface(self, port):
        port.team = self.name


class TeamChildInterface(EthernetInterface):

    def __init__(self, original_interface):
        self.team = None
        super(TeamChildInterface, self).__init__(original_interface.name, original_interface.mac)

    def make_iface_string(self):
        return "Team child interface: %s" % self.name


#
# Bond
#
class BondMasterInterface(EthernetInterface):
    LACP_BOND_OPTS = "mode=4 xmit_hash_policy=1"
    ACT_BCKP_BOND_OPTS = "mode=1"

    def __init__(self, name, v4_conf=None, v6_conf=None, bond_opts=LACP_BOND_OPTS):
        super(BondMasterInterface, self).__init__(name, None, v4_conf, v6_conf)
        self.bond_opts = bond_opts

    def make_iface_string(self):
        return "Bond master interface: %s, bond_opts: \"%s\"" % (self.name, self.bond_opts)

    def add_interface(self, interface):
        interface.master_bond = self.name


class BondChildInterface(EthernetInterface):

    def __init__(self, original_interface):
        super().__init__(original_interface.name, original_interface.mac)
        self.master_bond = None

    def make_iface_string(self):
        return "Bond child interface: %s, master: %s" % (self.name, self.master_bond)


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

    def __init__(self, left_ip, right_ip, cipher, passphrase, mode=MODE_TRANSPORT, phase2=PHASE2_ESP,
                 replay_window=None, encapsulation=ENCAPSULATION_NO, nic_offload=OFFLOAD_NO):
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
        return 'IPSec %s tunnel %s <=> %s, [%s]cipher: %s, mode: %s, replay-window: %s, nat-traversal: %s, ' \
               'nic-offload %s' % (self.family, self.left_ip, self.right_ip, self.phase2, self.cipher, self.mode,
                                   replay_window_str, self.encapsulation, self.nic_offload)

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
        return f'{self.family}_{self.mode}_{self.cipher}_encap-{self.encapsulation}_' \
               f'{self.left_ip.ip}_{self.right_ip.ip}'

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


#
# OVS related objects
#
class OVSwitch(object):

    def __init__(self, name):
        self.name = name
        self.interfaces = []
        self.tunnel_interfaces = []
        self.trunk_interfaces = []

    def add_interface(self, iface):
        self.interfaces.append(iface)

    def add_tunnel(self, tunnel):
        self.tunnel_interfaces.append(tunnel)

    def add_trunk_interface(self, iface, vlan=None):
        item = {"iface": iface, "vlans": vlan}
        self.trunk_interfaces.append(item)

    def __str__(self):
        ret = 'OVSwitch: %s' % self.name
        for iface in self.interfaces:
            ret += '\n  switch interface %s' % iface
        return ret


class OVSTunnel(object):
    VXLAN = "vxlan"

    def __init__(self, name, type=VXLAN, remote_ip=None, key=0):
        self.name = name
        self.type = type
        self.remote_ip = remote_ip
        self.key = key


class OVSIntPort(EthernetInterface):

    def __init__(self, name, ovs_switch, v4_conf=None, v6_conf=None):
        self.ovs_switch = ovs_switch
        super(OVSIntPort, self).__init__(name, None, v4_conf, v6_conf)
