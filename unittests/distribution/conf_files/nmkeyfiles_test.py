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
interface-name=int1
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
        print(keyfile.get_content())
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
