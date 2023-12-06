import json
import socket
import shutil
import os
from unittest import TestCase, skipIf
from nepta.core.tests.mpstat import MPStat

CUR_DIR = os.path.dirname(__file__)


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

        mpstat = MPStat(cpu_list='ALL', output=None)
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


class MPstatParserTest(TestCase):
    @staticmethod
    def mockup_parse_json(test: MPStat, path: str):
        with open(os.path.join(CUR_DIR, path)) as f:
            data = json.loads(f.read())
            test.parse_json = lambda: data  # type: ignore

    def test_parse_all(self):
        mpstat = MPStat(output='JSON', cpu_list='ALL', count=2, interval=5)
        self.mockup_parse_json(mpstat, 'mpstat_out/all-cores.json')

        cpu_loads = mpstat.cpu_loads()
        self.assertEqual(len(cpu_loads), 2)

        last_cpu_loads = mpstat.last_cpu_load()
        self.assertEqual(len(last_cpu_loads), 49)

        cpu_names = [x['cpu'] for x in last_cpu_loads]
        self.assertIn('all', cpu_names)
        self.assertIn('45', cpu_names)

    def test_parse_no_cpu(self):
        mpstat = MPStat(output='JSON', cpu_list='', count=2, interval=5)
        self.mockup_parse_json(mpstat, 'mpstat_out/no-cpu.json')

        cpu_loads = mpstat.cpu_loads()
        self.assertEqual(len(cpu_loads), 2)

        last_cpu_loads = mpstat.last_cpu_load()
        self.assertEqual(len(last_cpu_loads), 1)

        cpu_names = [x['cpu'] for x in last_cpu_loads]
        self.assertIn('all', cpu_names)
        self.assertNotIn('45', cpu_names)

    def test_parse_single_cpu(self):
        mpstat = MPStat(output='JSON', cpu_list='', count=2, interval=5)
        self.mockup_parse_json(mpstat, 'mpstat_out/single-core.json')

        cpu_loads = mpstat.cpu_loads()
        self.assertEqual(len(cpu_loads), 2)

        last_cpu_loads = mpstat.last_cpu_load()
        self.assertEqual(len(last_cpu_loads), 1)

        cpu_names = [x['cpu'] for x in last_cpu_loads]
        self.assertNotIn('all', cpu_names)
        self.assertNotIn('45', cpu_names)
        self.assertIn('12', cpu_names)

    def test_parse_4_cpu(self):
        mpstat = MPStat(output='JSON', cpu_list='', count=2, interval=5)
        self.mockup_parse_json(mpstat, 'mpstat_out/4-cores.json')

        cpu_loads = mpstat.cpu_loads()
        self.assertEqual(len(cpu_loads), 2)
        self.assertIsInstance(cpu_loads, list)
        self.assertIsInstance(cpu_loads[0], list)
        self.assertIsInstance(cpu_loads[0][0], dict)

        last_cpu_loads = mpstat.last_cpu_load()
        self.assertEqual(len(last_cpu_loads), 4)
        self.assertIsInstance(last_cpu_loads, list)
        self.assertIsInstance(last_cpu_loads[0], dict)

        cpu_names = [x['cpu'] for x in last_cpu_loads]
        self.assertNotIn('all', cpu_names)
        self.assertNotIn('45', cpu_names)
        self.assertNotIn('12', cpu_names)
        self.assertIn('3', cpu_names)
        self.assertIn('9', cpu_names)
