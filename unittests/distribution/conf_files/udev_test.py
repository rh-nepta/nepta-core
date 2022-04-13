from unittest import TestCase

from nepta.core.model.network import EthernetInterface
from nepta.core.distribution.conf_files import UdevRulesFile


class UdevTest(TestCase):
    def test_basic_udev(self):
        e1 = EthernetInterface('i40e', 'aa:bb:cc:dd:ee:ff')
        e2 = EthernetInterface('bnxt', 'aa:bb:cc:22:ee:ff')

        ufile = UdevRulesFile([e1, e2])

        expected_output = (
            'SUBSYSTEM=="net", ACTION=="add", ATTR{address}=="%s", '
            'NAME="%s"\nSUBSYSTEM=="net", ACTION=="add", ATTR{address}=="%s", '
            'NAME="%s"\n' % (e1.mac, e1.name, e2.mac, e2.name)
        )

        print(ufile._make_content())
        self.assertEqual(expected_output, ufile._make_content())
