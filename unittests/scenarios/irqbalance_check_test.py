from unittest import TestCase

from nepta.core.scenarios.generic.interupts import IRQBalanceCheck


class IRQBalanceScenarioTest(TestCase):

    def setUp(self):
        example_str = open('example_interrupt_out.txt', 'r').read()
        self.scenario = IRQBalanceCheck([])
        self.scenario.interrupt_cmd.run = lambda: None
        self.scenario.interrupt_cmd.watch_output = lambda: (example_str, 0)

    def test_parser(self):
        table = self.scenario.get_parsed_interrupts(True)

        cpu_sums = [sum(table[y][x] for y in range(len(table))) for x in range(len(table[0]))]

        self.assertEqual(cpu_sums[0], 18732087)
        self.assertEqual(cpu_sums[2], 200958)
        self.assertEqual(cpu_sums[-1], 165653)

        irq_sums = [sum(table[y][x] for x in range(len(table[0]))) for y in range(len(table))]

        self.assertEqual(irq_sums[1], 21738)
        self.assertEqual(irq_sums[4], 3091726)
        self.assertEqual(irq_sums[-1], 200855)

    def test_scenario_core(self):
        scenario_sec = self.scenario.run_scenario()
        self.assertEqual(scenario_sec.params['scenario_name'], self.scenario.__class__.__name__)

        res_sec = scenario_sec.subsections.filter('test_result')[0]
        self.assertEqual(res_sec.params['value'], 'FAIL')

    def test_evaluator(self):
        self.scenario.get_parsed_interrupts = lambda: [list(range(24)) for _ in range(10)]

        scenario_sec = self.scenario.run_scenario()
        self.assertEqual(scenario_sec.params['scenario_name'], self.scenario.__class__.__name__)

        res_sec = scenario_sec.subsections.filter('test_result')[0]
        self.assertEqual(res_sec.params['value'], 'PASS')
