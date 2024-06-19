from unittest import TestCase, skip
import os

from nepta.core.distribution.utils.network import IpCommand
from nepta.core.distribution.utils.system import TimeDateCtl
from nepta.core.model.system import TimeZone

CUR_DIR = os.path.dirname(__file__)


class TimeDateCtlTest(TestCase):
    @skip('skip for CI')
    def test_status(self):
        out = TimeDateCtl.status()
        self.assertTrue('Time zone' in out)
        self.assertTrue('NTP' in out)

    @skip('skip for CI')
    def test_set_timezone(self):
        zone = TimeZone('Europe/Prague')
        out = TimeDateCtl.set_timezone(zone)
        self.assertEqual(0, len(out))


class IpCmdTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls.ip_xfrm_state = IpCommand.Xfrm.state

    @classmethod
    def tearDownClass(cls):
        IpCommand.Xfrm.state = cls.ip_xfrm_state

    def test_xfrm_parser(self):
        with open(os.path.join(CUR_DIR, 'xfrm_example.txt')) as f:
            content = f.read()
            IpCommand.Xfrm.state = lambda: content

        self.assertEqual(IpCommand.Xfrm.number_of_tunnel(), 120, 'Number of tunnels should be 100')

        IpCommand.Xfrm.state = lambda: ''
        self.assertEqual(IpCommand.Xfrm.number_of_tunnel(), 0, 'Number of tunnels should be 0')
