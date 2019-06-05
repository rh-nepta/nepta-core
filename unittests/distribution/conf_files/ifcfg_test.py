from unittest import TestCase
import ipaddress as ia

from testing.model import network as nm
from testing.distribution import conf_files as cf


class IfcfgTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_generic_test(self):
        intf = nm.Interface('int1',
                            nm.IPv4Configuration(
                                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                                ia.IPv4Address('192.168.0.255'),
                                [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')]),
                            nm.IPv6Configuration(
                                [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64'), ia.IPv6Interface('fec0::35/64')],
                                ia.IPv6Address('fd00::ff'),
                                [ia.IPv6Address('2001:4860:4860::8844'), ia.IPv6Address('2001:4860:4860::8888')]))
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64 fec0::35/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_ipv4_test(self):
        intf = nm.Interface('int1', nm.IPv4Configuration(
            [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')], ia.IPv4Address('192.168.0.255'),
            [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')]))
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_ipv4_addr_only(self):
        intf = nm.Interface('int1', nm.IPv4Configuration(
            [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')]))
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_ipv4_addr_n_gw_only(self):
        intf = nm.Interface('int1', nm.IPv4Configuration(
            [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')], ia.IPv4Address('192.168.0.255')))
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_ipv6_test(self):
        intf = nm.Interface('int1', None,
                            nm.IPv6Configuration([ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64')],
                                                 ia.IPv6Address('fd00::ff'), [ia.IPv6Address('2001:4860:4860::8844'),
                                                                              ia.IPv6Address('2001:4860:4860::8888')]))
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_empty_int(self):
        intf = nm.Interface('int1')
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
'''
        self.assertEqual(expected_result, ifcfg.get_content())


class EthIfcfgTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_empty_eth_int(self):
        intf = nm.EthernetInterface('int1', 'aa:bb:cc:dd:ee:ff')
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
HWADDR=aa:bb:cc:dd:ee:ff
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_full_eth_int(self):
        intf = nm.EthernetInterface('int1', 'aa:bb:cc:dd:ee:ff', nm.IPv4Configuration(
            [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')], ia.IPv4Address('192.168.0.255'),
            [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')]),
                                    nm.IPv6Configuration(
                                        [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64')],
                                        ia.IPv6Address('fd00::ff'), [ia.IPv6Address('2001:4860:4860::8844'),
                                                                     ia.IPv6Address('2001:4860:4860::8888')]),
                                    mtu=1450)
        ifcfg = cf.IfcfgFile(intf)

        expected_result = '''DEVICE=int1
ONBOOT=yes
BOOTPROTO=none
MTU=1450
HWADDR=aa:bb:cc:dd:ee:ff
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected_result, ifcfg.get_content())

    def test_vlan_int(self):
        eth = nm.EthernetInterface('ixgbe_0', '00:22:33:44:55:66')
        vlan = nm.VlanInterface(eth, 963, nm.IPv4Configuration(
            [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')], ia.IPv4Address('192.168.0.255'),
            None),
                                nm.IPv6Configuration([ia.IPv6Interface('fd00::1/64')], None,
                                                     [ia.IPv6Address('2001:4860:4860::8844'),
                                                      ia.IPv6Address('2001:4860:4860::8888')]))
        ifcfg = cf.IfcfgFile(vlan)
        expected = '''\
DEVICE=ixgbe_0.963
ONBOOT=yes
BOOTPROTO=none
MTU=1500
VLAN=yes
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
'''
        self.assertEqual(expected, ifcfg.get_content())


class VariousIfcfgTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None
        self.generic_eth = nm.EthernetInterface('ixgbe_1', '00:11:22:33:44:55', nm.IPv4Configuration(
            [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')], ia.IPv4Address('192.168.0.255'),
            [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')]),
                                                nm.IPv6Configuration(
                                                    [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64')],
                                                    ia.IPv6Address('fd00::ff'), [ia.IPv6Address('2001:4860:4860::8844'),
                                                                                 ia.IPv6Address(
                                                                                     '2001:4860:4860::8888')]))

    def test_team_master(self):
        team_int = nm.TeamMasterInterface('team1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        team_file = cf.IfcfgFile(team_int)
        expected = '''\
DEVICE=team1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
DEVICETYPE=Team
TEAM_CONFIG='{"runner": {"active": true, "link_watch": "ethotool", "fast_rate": true, "name": "lacp", "tx_hash": ["eth", "ipv4", "ipv6", "tcp"]}}'
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected, team_file.get_content())

    def test_team_slave(self):
        team_slave = nm.TeamChildInterface(self.generic_eth)
        team_master = nm.TeamMasterInterface('asdf')
        team_master.add_interface(team_slave)
        ifcfg = cf.IfcfgFile(team_slave)

        expected = '''\
DEVICE=ixgbe_1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
HWADDR=00:11:22:33:44:55
DEVICETYPE=TeamPort
TEAM_MASTER=asdf
'''
        self.assertEqual(expected, ifcfg.get_content())

    def test_bond_master(self):
        team_int = nm.BondMasterInterface('team1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        team_file = cf.IfcfgFile(team_int)
        expected = '''\
DEVICE=team1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
TYPE=Bond
BONDING_MASTER=yes
BONDING_OPTS="mode=4 xmit_hash_policy=1"
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected, team_file.get_content())

    def test_bond_slave(self):
        slave = nm.BondChildInterface(self.generic_eth)
        master = nm.BondMasterInterface('asdf')
        master.add_interface(slave)
        ifcfg = cf.IfcfgFile(slave)

        expected = '''\
DEVICE=ixgbe_1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
HWADDR=00:11:22:33:44:55
MASTER=asdf
SLAVE=yes
'''
        self.assertEqual(expected, ifcfg.get_content())

    def test_bridge_master(self):
        bridge_master = nm.LinuxBridge('br1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        ifcfg = cf.IfcfgFile(bridge_master)
        expected = '''\
DEVICE=br1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
TYPE=Bridge
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected, ifcfg.get_content())

    def test_bridge_slave(self):
        bridge_master = nm.LinuxBridge('br1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        bridge_slave = nm.EthernetInterface('bnxt_1', '00:11:22:33:44:55', self.generic_eth.v4_conf,
                                            self.generic_eth.v6_conf)
        bridge_master.add_interface(bridge_slave)
        ifcfg = cf.IfcfgFile(bridge_slave)
        expected = '''\
DEVICE=bnxt_1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
HWADDR=00:11:22:33:44:55
BRIDGE=br1
'''
        self.assertEqual(expected, ifcfg.get_content())

    def test_ovs_ip(self):
        ovs1 = nm.OVSwitch('ovs1')
        ovs_ip = nm.OVSIntPort('ovs_ip_1', ovs1, self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        ifcfg = cf.IfcfgFile(ovs_ip)
        expected = '''\
DEVICE=ovs_ip_1
ONBOOT=yes
BOOTPROTO=none
MTU=1500
DEVICETYPE=ovs
TYPE=OVSIntPort
OVS_BRIDGE=ovs1
NM_CONTROLLED=yes
IPADDR0=192.168.0.1
NETMASK0=255.255.255.0
IPADDR1=192.168.1.1
NETMASK1=255.255.255.0
GATEWAY=192.168.0.255
GATEWAY0=192.168.0.255
DNS1=8.8.4.4
DNS2=1.1.1.1
IPV6INIT=yes
IPV6_AUTOCONF=no
IPV6ADDR=fd00::1/64
IPV6ADDR_SECONDARIES="fec0::34/64"
IPV6_DEFAULTGW=fd00::ff
'''
        self.assertEqual(expected, ifcfg.get_content())
