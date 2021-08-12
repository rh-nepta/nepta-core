import json
import socket
import shutil
from unittest import TestCase, skipIf
from nepta.core.tests.mpstat import MPStat


@skipIf(shutil.which('mpstat') is None, 'Skipping because mpstat is not installed')
class MPStatTests(TestCase):

    def test_basic_functionality(self):
        mpstat = MPStat()
        mpstat.run()
        out, ret_code = mpstat.watch_output()
        self.assertIsNotNone(out)
        self.assertEqual(ret_code, 0, 'Error in mpstat execution')

        mpstat = MPStat(output='JSON')
        mpstat.run()
        output, ret_code = mpstat.watch_output()
        self.assertIsNotNone(output)
        self.assertEqual(ret_code, 0, 'Error in mpstat execution')
        parser_output = json.loads(output)
        self.assertIsNotNone(parser_output)

    def test_exceptions(self):
        self.assertRaises(ValueError, MPStat, count=3)

        mpstat = MPStat(cpu_list='ALL')
        mpstat.run()
        self.assertRaises(ValueError, mpstat.parse_json)

    def test_real_usage(self):
        mpstat = MPStat(output='JSON', cpu_list='ALL', count=2, interval=2)
        mpstat.run()
        mpstat.watch_output()
        self.assertTrue(mpstat.success())
        self.assertIsInstance(mpstat.parse_json(), dict)

    # the remote host may not be accessible from the outside
    def test_remote_exec(self):
        try:
            socket.gethostbyname('mlflow')
        except socket.gaierror:
            self.skipTest('The remote host is not accesible')
        mpstat = MPStat(output='JSON', cpu_list='ALL', count=2, interval=1)
        mpstat.remote_run('mlflow')
        mpstat.watch_output()
        self.assertTrue(mpstat.success())
        self.assertIsInstance(mpstat.parse_json(), dict)

    def test_accessing_values(self):
        mpstat = MPStat(output='JSON', cpu_list='ALL', count=2, interval=2)
        mpstat.run()
        load = mpstat.cpu_loads()
        last_load = mpstat.last_cpu_load()
        self.assertIsNotNone(load)
        self.assertIsNotNone(last_load)
        print(last_load)
