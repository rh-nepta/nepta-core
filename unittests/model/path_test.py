from unittest import TestCase
from ipaddress import IPv4Interface as IPv4

from nepta.core.model.schedule import CongestedPath


class CongestedPathTest(TestCase):

    def test_uuid_gen(self):
        c1 = CongestedPath(IPv4('192.168.0.1/24'), IPv4('192.168.0.2/24'), '500000', '3', 'cubic', ['ixgbe', 'IPv4'])
        c2 = CongestedPath(IPv4('192.168.0.1/24'), IPv4('192.168.0.2/24'), '250000', '3', 'cubic', ['ixgbe', 'IPv4'])
        self.assertNotEqual(c1.id, c2.id)
