from unittest import TestCase
import ipaddress

from nepta.core.model.network import Route4, Route6, Interface, NetperfNet4, NetperfNet6
from nepta.core.distribution.conf_files import Route4File, Route6File


class RouteConfigFile(TestCase):

    def setUp(self) -> None:
        self.net4 = NetperfNet4('192.168.0.0/24')
        self.net6 = NetperfNet6('FE80::/64')
        self.int1 = Interface('eth1', self.net4.new_config(2), self.net6.new_config(2))
        self.routes_4 = [
            Route4(self.net4, self.int1, self.int1.v4_conf[0].ip, 10),
            Route4(self.net4, self.int1, self.int1.v4_conf[0].ip),
            Route4(self.net4, self.int1),
        ]

        self.routes_6 = [
            Route6(self.net6, self.int1, self.int1.v6_conf[0].ip, 20),
            Route6(self.net6, self.int1, self.int1.v6_conf[0].ip),
            Route6(self.net6, self.int1),
        ]

    def test_route_file_content(self):
        cfg4 = Route4File(self.routes_4)
        cfg6 = Route6File(self.routes_6)

        self.assertEqual(cfg4.get_content(),
                         """\
192.168.0.0/24 via 192.168.0.1 dev eth1 metric 10
192.168.0.0/24 via 192.168.0.1 dev eth1 metric 0
192.168.0.0/24 via 192.168.0.0/24 dev eth1 metric 0
"""
                         )

        self.assertEqual(cfg6.get_content(), """\
fe80::/64 via fe80::1 dev eth1 metric 20
fe80::/64 via fe80::1 dev eth1 metric 0
fe80::/64 via fe80::/64 dev eth1 metric 0
"""
                         )
