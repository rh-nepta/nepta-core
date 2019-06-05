from unittest import TestCase

from testing.model.network import EthernetInterface
from testing.distribution.conf_files import UdevRulesFile


class UdevTest(TestCase):

    def test_basic_udev(self):
        e1 = EthernetInterface('i40e', 'aa:bb:cc:dd:ee:ff')
        e2 = EthernetInterface('bnxt', 'aa:bb:cc:22:ee:ff')

        ufile = UdevRulesFile([e1, e2])

        expected_output = \
            'SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{address}=="%s", ATTR{dev_id}=="0x0, ATTR{type}=="1", KERNEL=="eth*", NAME="%s"\nSUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{address}=="%s", ATTR{dev_id}=="0x0, ATTR{type}=="1", KERNEL=="eth*", NAME="%s"\n' % (e1.mac, e1.name, e2.mac, e2.name)

        print(ufile._make_content())
        self.assertEqual(expected_output, ufile._make_content())
