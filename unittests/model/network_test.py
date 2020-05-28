from unittest import TestCase
import ipaddress as ia

from nepta.core.model.network import NetperfNet4, NetperfNet6
from nepta.core.model.network import IPv4Configuration, IPv6Configuration
from nepta.core.model import network, schedule
from nepta.core.distribution.conf_files import Route4File


class NetFormatterTest(TestCase):
    def setUp(self) -> None:
        self.net4 = NetperfNet4(ia.ip_network('192.168.0.0/24'))
        self.net6 = NetperfNet6(ia.ip_network('FE80::/64'))

    def test_generators(self):
        ipv4_gen = self.net4.subnets(new_prefix=30)
        for i in range(4):
            self.assertIsInstance(next(ipv4_gen), NetperfNet4)

        ipv6_gen = self.net6.subnets(new_prefix=80)
        for i in range(4):
            self.assertIsInstance(next(ipv6_gen), NetperfNet6)

    def test_new_addr(self):
        self.assertIsInstance(self.net4.new_addr(), ia.IPv4Interface)
        self.assertIsInstance(self.net6.new_addr(), ia.IPv6Interface)

        for i in [4, 6]:
            self.assertEqual(i, len(self.net4.new_addresses(i)))
            self.assertEqual(i, len(self.net6.new_addresses(i)))

    def test_new_conf(self):
        self.assertIsInstance(self.net4.new_config(), IPv4Configuration)
        self.assertIsInstance(self.net6.new_config(), IPv6Configuration)

        for i in [4, 6]:
            cfg4 = self.net4.new_config(i)
            cfg6 = self.net6.new_config(i)
            self.assertEqual(i, len(cfg4.addresses))
            self.assertEqual(i, len(cfg6.addresses))
            for j, ip in enumerate(cfg4):
                self.assertEqual(ip, cfg4[j])
            for j, ip in enumerate(cfg6):
                self.assertEqual(ip, cfg6[j])


class InterfaceTest(TestCase):
    def setUp(self) -> None:
        self.net4 = NetperfNet4(ia.ip_network('192.168.0.0/24'))
        self.gw4 = self.net4.broadcast_address
        self.net6 = NetperfNet6(ia.ip_network('FE80::/64'))
        self.dns6 = self.net6.new_addresses(3)

    def test_init_and_str(self):
        """
        This test is not used primarily to raise assertions. It is used to check accepted variables by constructor. The
        check should be evaluated using `mypy`.
        """
        generic = network.Interface(
            'eth2',
            IPv4Configuration(self.net4.new_addresses(3), self.gw4),
            IPv6Configuration(self.net6.new_addresses(2), dns=self.dns6),
        )

        mac = '00:11:22:33:44:55:66'
        eth = network.EthernetInterface(
            'eth2',
            mac,
            IPv4Configuration(self.net4.new_addresses(3), self.gw4),
            IPv6Configuration(self.net6.new_addresses(2), dns=self.dns6),
        )
        self.assertEqual(eth.mac, mac)

        network.VlanInterface(generic, 10, self.net4.new_config(2))
        network.VlanInterface(eth, 20)


class RouteTest(TestCase):
    def setUp(self) -> None:
        self.net1 = NetperfNet4('192.168.0.0/24')
        self.net2 = NetperfNet4('192.168.1.0/24')

        self.local_int1 = network.Interface('eth1', self.net1.new_config())
        self.local_int2 = network.Interface('eth2', self.net2.new_config())
        self.remote_int1 = network.Interface('eth3', self.net1.new_config())
        self.remote_int2 = network.Interface('eth4', self.net2.new_config())

        self.path1 = schedule.Path(
            self.local_int1.v4_conf[0], self.remote_int1.v4_conf[0], [schedule.SoftwareInventoryTag('IPv4')]
        )
        self.path2 = schedule.Path(
            self.local_int2.v4_conf[0], self.remote_int2.v4_conf[0], [schedule.SoftwareInventoryTag('IPv4')]
        )

    def test_from_path_creator(self):
        local_route1 = network.Route4.from_path(self.path1, [self.local_int1, self.local_int2])
        self.assertEqual(local_route1.destination, self.remote_int1.v4_conf[0].ip)
        self.assertEqual(local_route1.interface, self.local_int1)

        local_route2 = network.Route4.from_path(self.path2, [self.local_int1, self.local_int2])
        self.assertEqual(local_route2.destination, self.remote_int2.v4_conf[0].ip)
        self.assertEqual(local_route2.interface, self.local_int2)

        remote_route1 = network.Route4.from_path(self.path1, [self.remote_int1, self.remote_int2])
        self.assertEqual(remote_route1.destination, self.local_int1.v4_conf[0].ip)
        self.assertEqual(remote_route1.interface, self.remote_int1)

        remote_route2 = network.Route4.from_path(self.path2, [self.remote_int1, self.remote_int2])
        self.assertEqual(remote_route2.destination, self.local_int2.v4_conf[0].ip)
        self.assertEqual(remote_route2.interface, self.remote_int2)
