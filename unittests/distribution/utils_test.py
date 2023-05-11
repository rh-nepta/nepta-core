from unittest import TestCase, skip

from nepta.core.distribution.utils.system import TimeDateCtl
from nepta.core.model.system import TimeZone


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
