import ipaddress as ia
from unittest import TestCase

from nepta.core.model.network import WireGuardPeer, WireGuardTunnel, NetperfNet4
from nepta.core.distribution.conf_files import WireGuardConnectionFile


class WireGuardTest(TestCase):

    def setUp(self) -> None:
        self.wg_net = NetperfNet4('10.0.0.0/16')
        self.local_net = NetperfNet4('192.168.0.0/24')
        self.remote_net = NetperfNet4('192.168.1.0/24')

        self.local_pub = 'ASwib7rC75WMP/p7fF6NS88+X2lD4/PWF2MomKhorV0='
        self.local_priv = '+AUrLxPi3adajZja/OzUA36PKbK+vP2q+tZwWNRS31g='
        self.remote_pub = 'OAIWay9oFQOH7P4Rfo9avKoorEMC1m/w5pHynl7231g='
        self.remote_priv = 'WK5fZKmnm+jumdHDfTQEFHoGDfJG+3OhRgijvyGy40Q='

        self.my_int = ia.IPv4Interface('8.8.8.8/27')
        self.rem_int = ia.IPv4Interface('8.8.8.10/27')

    def test_interface(self):
        p0 = WireGuardPeer(self.local_pub, self.local_priv, [self.wg_net, self.local_net], self.rem_int)
        p1 = WireGuardPeer(self.remote_pub, self.remote_priv, [self.wg_net, self.remote_net, self.wg_net], self.my_int, 12345)
        p2 = WireGuardPeer('public', 'private', [ia.IPv4Network('224.0.0.0/25')])

        local_tunnel = WireGuardTunnel(self.wg_net.new_addr(), p0.private_key, peers=[p1, p2])
        remote_tunnel = WireGuardTunnel(self.wg_net.new_addr(), p1.private_key, 12345, peers=[p0])

        # tunnel name must be unique
        self.assertNotEqual(local_tunnel.name, remote_tunnel.name)

        local_cfg = WireGuardConnectionFile(local_tunnel)
        remote_cfg = WireGuardConnectionFile(remote_tunnel)

        self.assertEqual(
            local_cfg.get_content(),
f"""[Interface]
Address = 10.0.0.1/16
PrivateKey = {self.local_priv}
ListenPort = 51820

[Peer]
PublicKey = {self.remote_pub}
AllowedIPs = 10.0.0.0/16, 192.168.1.0/24, 10.0.0.0/16
Endpoint = 8.8.8.8:12345

[Peer]
PublicKey = {p2.public_key}
AllowedIPs = {p2.allowed_ips[0]}
""")

        self.assertEqual(
            remote_cfg.get_content(),
f"""[Interface]
Address = 10.0.0.2/16
PrivateKey = {self.remote_priv}
ListenPort = 12345

[Peer]
PublicKey = {self.local_pub}
AllowedIPs = 10.0.0.0/16, 192.168.0.0/24
Endpoint = 8.8.8.10:51820
"""
        )
