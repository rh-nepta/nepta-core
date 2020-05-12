from unittest import TestCase

from nepta.core.model.system import NTPServer
from nepta.core.distribution.conf_files import ChronyConf

class TestChrony(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ntp1 = NTPServer('server1.ntp.com')
        self.ntp2 = NTPServer('server2.ntp.com')

    def test_single_ntp(self):
        cfg = ChronyConf([self.ntp1])
        print()
        print(cfg._make_content())

    def test_more_ntp(self):
        cfg = ChronyConf([self.ntp1, self.ntp2])
        print()
        print(cfg._make_content())
