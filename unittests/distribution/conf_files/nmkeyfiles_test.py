from unittest import TestCase
import ipaddress as ia

from nepta.core.model import network as nm
from nepta.core.distribution.conf_files import NmcliKeyFile


class NmKeyfilesTest(TestCase):
    def test_generic_test(self):
        intf = nm.Interface(
            'int1',
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                ia.IPv4Address('192.168.0.255'),
                [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')],
            ),
            nm.IPv6Configuration(
                [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64'), ia.IPv6Interface('fec0::35/64')],
                ia.IPv6Address('fd00::ff'),
                [ia.IPv6Address('2001:4860:4860::8844'), ia.IPv6Address('2001:4860:4860::8888')],
            ),
        )
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=f2783e9c-9ed1-5f0f-854b-f58e1325b1a7
interface-name=int1

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
address3=fec0::35/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual
'''
        self.assertEqual(expected_result, keyfile.get_content())

    def test_ipv4_test(self):
        intf = nm.Interface(
            'int1',
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                ia.IPv4Address('192.168.0.255'),
                [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')],
            ),
        )
        nm_keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=54152369-0951-59a9-ab27-f0864cff25c2
interface-name=int1

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual
'''
        self.assertEqual(expected_result, nm_keyfile.get_content())

    def test_ipv4_addr_only(self):
        intf = nm.Interface(
            'int1', nm.IPv4Configuration([ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')])
        )
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=9eaccad3-a869-57c9-a70e-9e07f0c63174
interface-name=int1

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
may-fail=false
method=manual
'''
        self.assertEqual(expected_result, keyfile.get_content())

    def test_ipv4_addr_n_gw_only(self):
        intf = nm.Interface(
            'int1',
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                ia.IPv4Address('192.168.0.255'),
            ),
        )
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=c9fc21c4-4994-5453-b707-d26cb074f6e4
interface-name=int1

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
may-fail=false
method=manual
'''
        self.assertEqual(expected_result, keyfile.get_content())

    def test_ipv6_test(self):
        intf = nm.Interface(
            'int1',
            None,
            nm.IPv6Configuration(
                [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64')],
                ia.IPv6Address('fd00::ff'),
                [ia.IPv6Address('2001:4860:4860::8844'), ia.IPv6Address('2001:4860:4860::8888')],
            ),
        )
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=60b96431-e7aa-535a-b4f0-02ce4b185506
interface-name=int1

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual
'''
        self.assertEqual(expected_result, keyfile.get_content())

    def test_empty_int(self):
        intf = nm.Interface('int1')
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=740ddd22-19a5-5d29-b30a-e9c074169100
interface-name=int1
'''
        self.assertEqual(expected_result, keyfile.get_content())

    def test_static_routes(self):
        intf = nm.Interface(
            'int1',
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                ia.IPv4Address('192.168.0.255'),
            ),
            nm.IPv6Configuration(
                [ia.IPv6Interface('fd02::1/64')],
                ia.IPv6Address('fd02::ff'),
            ),
        )
        nm.Route4(ia.IPv4Network('10.0.0.0/24'), intf)
        nm.Route4(ia.IPv4Network('10.2.0.0/24'), intf, ia.IPv4Address('8.8.8.8'))
        nm.Route6(ia.IPv6Network('fd00::/64'), intf)
        nm.Route6(ia.IPv6Network('fd00::/64'), intf, ia.IPv6Address('fd01::1'))
        keyfile = NmcliKeyFile(intf)

        expected_result = '''\
[connection]
id=int1
uuid=d5766853-3226-5d31-b820-c25a8d78ee5f
interface-name=int1

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
may-fail=false
method=manual
route1=10.0.0.0/24,0.0.0.0,0
route2=10.2.0.0/24,8.8.8.8,0

[ipv6]
address1=fd02::1/64
gateway=fd02::ff
may-fail=false
method=manual
route1=fd00::/64,::,0
route2=fd00::/64,fd01::1,0
'''

        self.assertEqual(expected_result, keyfile.get_content())


class EthKeyFileTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_empty_eth_int(self):
        intf = nm.EthernetInterface('int1', 'aa:bb:cc:dd:ee:ff')
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=806b64d9-2550-52b8-9d6c-7684320e15a8
interface-name=int1
type=ethernet

[ethernet]
mac-address=aa:bb:cc:dd:ee:ff
mtu=1500
'''
        print(keyfile.get_content())
        self.assertEqual(expected_result, keyfile.get_content())

    def test_full_eth_int(self):
        intf = nm.EthernetInterface(
            'int1',
            'aa:bb:cc:dd:ee:ff',
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                ia.IPv4Address('192.168.0.255'),
                [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')],
            ),
            nm.IPv6Configuration(
                [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64')],
                ia.IPv6Address('fd00::ff'),
                [ia.IPv6Address('2001:4860:4860::8844'), ia.IPv6Address('2001:4860:4860::8888')],
            ),
            mtu=1450,
        )
        keyfile = NmcliKeyFile(intf)

        expected_result = '''[connection]
id=int1
uuid=44ffb090-6c33-5836-a3eb-5cd7f8c6285a
interface-name=int1
type=ethernet

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual

[ethernet]
mac-address=aa:bb:cc:dd:ee:ff
mtu=1450
'''
        self.assertEqual(expected_result, keyfile.get_content())

    def test_vlan_int(self):
        eth = nm.EthernetInterface('ixgbe_0', '00:22:33:44:55:66')
        vlan = nm.VlanInterface(
            eth,
            963,
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                gw=ia.IPv4Address('192.168.0.255'),
            ),
            nm.IPv6Configuration(
                [ia.IPv6Interface('fd00::1/64')],
                dns=[ia.IPv6Address('2001:4860:4860::8844'), ia.IPv6Address('2001:4860:4860::8888')],
            ),
        )
        keyfile = NmcliKeyFile(vlan)
        expected = '''\
[connection]
id=ixgbe_0.963
uuid=cede41a3-2e7d-57bd-bd6a-4a9281094d58
interface-name=ixgbe_0.963
type=vlan

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual

[vlan]
interface-name=ixgbe_0.963
parent=ixgbe_0
id=963
'''
        self.assertEqual(expected, keyfile.get_content())

    def test_offloads(self):
        intf = nm.EthernetInterface('int1', 'aa:bb:cc:dd:ee:ff', offloads={'gro': False, 'gso': True})
        keyfile = NmcliKeyFile(intf)

        expected_result = '''\
[connection]
id=int1
uuid=67a78a49-7849-5797-a5cb-00641d6f8b22
interface-name=int1
type=ethernet

[ethernet]
mac-address=aa:bb:cc:dd:ee:ff
mtu=1500

[ethtool]
feature-gro=false
feature-gso=true
'''
        print(keyfile.get_content())
        self.assertEqual(expected_result, keyfile.get_content())


class VariousNmKeyFilTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None
        self.generic_eth = nm.EthernetInterface(
            'ixgbe_1',
            '00:11:22:33:44:55',
            nm.IPv4Configuration(
                [ia.IPv4Interface('192.168.0.1/24'), ia.IPv4Interface('192.168.1.1/24')],
                ia.IPv4Address('192.168.0.255'),
                [ia.IPv4Address('8.8.4.4'), ia.IPv4Address('1.1.1.1')],
            ),
            nm.IPv6Configuration(
                [ia.IPv6Interface('fd00::1/64'), ia.IPv6Interface('fec0::34/64')],
                ia.IPv6Address('fd00::ff'),
                [ia.IPv6Address('2001:4860:4860::8844'), ia.IPv6Address('2001:4860:4860::8888')],
            ),
        )

    def test_team_master(self):
        team_int = nm.TeamMasterInterface('team1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        team_file = NmcliKeyFile(team_int)
        expected = '''\
[connection]
id=team1
uuid=d9e6a92c-acdd-5fa3-ab22-a4276ece70c2
interface-name=team1
type=team

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual

[team]
config={"runner": {"active": true, "link_watch": "ethotool", \
"fast_rate": true, "name": "lacp", "tx_hash": ["eth", "ipv4", "ipv6", "tcp"]}}
'''
        self.assertEqual(expected, team_file.get_content())

    def test_team_slave(self):
        team_slave = nm.TeamChildInterface(self.generic_eth)
        team_master = nm.TeamMasterInterface('asdf')
        team_master.add_interface(team_slave)
        key_file = NmcliKeyFile(team_slave)

        expected = '''\
[connection]
id=ixgbe_1
uuid=95686ad9-0f11-54d9-89e3-a8d741a83cc7
interface-name=ixgbe_1
type=ethernet
master=asdf
slave-type=team

[ethernet]
mac-address=00:11:22:33:44:55
mtu=1500

[team-port]
'''
        print(key_file.get_content())
        self.assertEqual(expected, key_file.get_content())

    def test_bond_master(self):
        team_int = nm.BondMasterInterface('team1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        team_file = NmcliKeyFile(team_int)
        expected = '''\
[connection]
id=team1
uuid=389d554b-f494-5b48-a73d-a624d0ca149e
interface-name=team1
type=bond

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual

[bond]
mode=4
xmit_hash_policy=1
'''
        self.assertEqual(expected, team_file.get_content())

    def test_bond_slave(self):
        slave = nm.BondChildInterface(self.generic_eth)
        master = nm.BondMasterInterface('asdf')
        master.add_interface(slave)
        key_file = NmcliKeyFile(slave)

        expected = '''\
[connection]
id=ixgbe_1
uuid=c649dc3f-92c0-5b8e-83ac-04960107e701
interface-name=ixgbe_1
type=ethernet
master=asdf
slave-type=bond

[ethernet]
mac-address=00:11:22:33:44:55
mtu=1500

'''

        self.assertEqual(expected, key_file.get_content())

    def test_bridge_master(self):
        bridge_master = nm.LinuxBridge('br1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        key_file = NmcliKeyFile(bridge_master)
        expected = '''[connection]
id=br1
uuid=fbb02b53-01bd-516d-b87b-9237cecafb72
interface-name=br1
type=bridge

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual
'''
        self.assertEqual(expected, key_file.get_content())

    def test_bridge_slave(self):
        bridge_master = nm.LinuxBridge('br1', self.generic_eth.v4_conf, self.generic_eth.v6_conf)
        bridge_slave = nm.EthernetInterface(
            'bnxt_1', '00:11:22:33:44:55', self.generic_eth.v4_conf, self.generic_eth.v6_conf
        )
        bridge_master.add_interface(bridge_slave)
        key_file = NmcliKeyFile(bridge_slave)
        expected = '''\
[connection]
id=bnxt_1
uuid=29fff879-9057-5f8c-8d4f-8ac3f47def65
interface-name=bnxt_1
master=br1
slave-type=bridge
type=ethernet

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[ipv6]
address1=fd00::1/64
address2=fec0::34/64
gateway=fd00::ff
dns=2001:4860:4860::8844;2001:4860:4860::8888;
may-fail=false
method=manual

[ethernet]
mac-address=00:11:22:33:44:55
mtu=1500
'''
        self.assertEqual(expected, key_file.get_content())

    def test_macsec_slave(self):
        CAK = '50b71a8ef0bd5751ea76de6d6c98c03a'
        CKN = 'bbae4e26f7c88b8da2048f32f53422f9ce861a3b8413b5cfcdd6b66f05bcd529'
        intf = nm.EthernetInterface(
            'bnxt_1',
            '00:11:22:33:44:55',
        )
        macsec_intf = nm.MACSecInterface('macsec0', intf, CAK, CKN, self.generic_eth.v4_conf)
        key_file = NmcliKeyFile(macsec_intf)
        expected = '''\
[connection]
id=macsec0
uuid=ab82111a-8456-5d13-b029-5947574bd596
interface-name=macsec0
type=macsec

[ipv4]
address1=192.168.0.1/24
address2=192.168.1.1/24
gateway=192.168.0.255
dns=8.8.4.4;1.1.1.1;
may-fail=false
method=manual

[macsec]
mka-cak=50b71a8ef0bd5751ea76de6d6c98c03a
mka-ckn=bbae4e26f7c88b8da2048f32f53422f9ce861a3b8413b5cfcdd6b66f05bcd529
parent=bnxt_1
'''
        self.assertEqual(expected, key_file.get_content())
