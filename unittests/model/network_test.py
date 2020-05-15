from unittest import TestCase
import ipaddress as ia

from nepta.core.model.network import NetperfNet4, NetperfNet6
from nepta.core.model.network import IPv4Configuration, IPv6Configuration


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
