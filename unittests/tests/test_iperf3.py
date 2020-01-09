from unittest import TestCase
import json
import os

from nepta.core.tests.iperf3 import Iperf3TestResult, Iperf3Test


class Iperf3TestResultTest(TestCase):
    JSON_FILENAME = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), 'sample_json.json'
    )

    def setUp(self) -> None:
        self.json_data = json.load(open(self.JSON_FILENAME))

    def test_parse(self):
        result = Iperf3TestResult.from_json(self.json_data)

        self.assertIsInstance(result, Iperf3TestResult)

    def test_add(self):
        result1 = Iperf3TestResult.from_json(self.json_data)
        result2 = Iperf3TestResult.from_json(self.json_data)

        result3 = result1 + result2

        self.assertIsInstance(result3, Iperf3TestResult)
        self.assertEqual(result3['throughput'], result1['throughput'] + result2['throughput'])
        self.assertEqual(result3['stddev'], result1['stddev'] + result2['stddev'])

    def test_sum(self):
        result1 = Iperf3TestResult.from_json(self.json_data)
        result2 = Iperf3TestResult.from_json(self.json_data)
        result3 = Iperf3TestResult.from_json(self.json_data)
        result4 = result1 + result2

        result5 = sum([result1, result2, result3, result4])

        self.assertIsInstance(result5, Iperf3TestResult)
        self.assertAlmostEqual(result5['throughput'], result1['throughput'] * 5, places=5)
        self.assertAlmostEqual(result5['stddev'], result1['stddev'] * 5, places=5)

    def test_format(self):
        def str_round(num, decimal=3):
            return "{:.{}f}".format(num, decimal)

        result = Iperf3TestResult.from_json(self.json_data)
        result.set_data_formatter(str_round)

        for key in result._DIMENSIONS:
            self.assertRegex(result[key], '[0-9]*[.][0-9]{3}$')

        for key, val in result:
            self.assertRegex(val, '[0-9]*[.][0-9]{3}$')

    def test_update_dict(self):
        test = dict()
        result = Iperf3TestResult.from_json(self.json_data)

        test.update(result)

        for key in ['throughput', 'local_cpu', 'remote_cpu', 'stddev']:
            self.assertEqual(test[key], result[key])

    def test_get_result_from_test(self):
        test = Iperf3Test()
        test._output = open(self.JSON_FILENAME).read()

        result = test.get_result()
        self.assertLessEqual(result['throughput'], 10e4)

        result = test.get_result(Iperf3TestResult.ThroughputFormat.GBPS)
        self.assertLessEqual(result['throughput'], 10, )
