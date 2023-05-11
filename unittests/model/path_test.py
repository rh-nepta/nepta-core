from unittest import TestCase
from uuid import UUID
from ipaddress import IPv4Interface as IPv4

from nepta.core.model.schedule import CongestedPath, ParallelPathList, PathList, Path
from nepta.core.model.tag import SoftwareInventoryTag as Sw, HardwareInventoryTag as Hw


class CongestedPathTest(TestCase):
    def test_uuid_gen(self):
        c1 = CongestedPath(
            IPv4('192.168.0.1/24'), IPv4('192.168.0.2/24'), '500000', '3', 'cubic', [Hw('ixgbe'), Sw('IPv4')]
        )
        c2 = CongestedPath(
            IPv4('192.168.0.1/24'), IPv4('192.168.0.2/24'), '250000', '3', 'cubic', [Hw('ixgbe'), Sw('IPv4')]
        )
        self.assertNotEqual(c1.id, c2.id)


class ParallelPathListTest(TestCase):
    def setUp(self) -> None:
        ip1 = IPv4('192.168.0.1/24')
        ip2 = IPv4('192.168.0.2/24')
        self.path_list = ParallelPathList(
            [
                PathList(
                    [
                        Path(ip1, ip2, [Sw('ipv4'), Sw('vlan'), Hw('mlx5'), Hw('mlx5'), Hw('gso', 'offload')]),
                        Path(ip1, ip2, [Sw('ipv4'), Sw('vlan'), Hw('mlx5')]),
                    ]
                ),
                PathList(
                    [
                        Path(ip1, ip2, [Sw('ipv4'), Hw('mlx5')]),
                        Path(ip1, ip2, [Sw('ipv4'), Hw('mlx5')]),
                    ]
                ),
            ]
        )

    def test_parallel_path_attrs(self):
        for pl in self.path_list:
            self.assertIsInstance(pl.desc, str)
            self.assertIsInstance(pl.id, UUID)
            self.assertIsInstance(pl.dict(), dict)
            self.assertIsInstance(pl.hw_inventory, list)
            self.assertIsInstance(pl.sw_inventory, list)
