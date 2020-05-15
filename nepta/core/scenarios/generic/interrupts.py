import logging
import re
import uuid

from nepta.dataformat import Section
from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.distribution.command import Command
from nepta.core.tests import Iperf3Test

logger = logging.getLogger(__name__)


class IRQBalanceCheck(ScenarioGeneric):
    """
    Run one iperf3 test for each path with CPU pinning on 0th core and check operations of irqbalance -> check if there
    are interrupts on different cores than 0.
    """

    def __init__(self, paths, test_length=30, msg_size='64k'):
        self.paths = paths
        self.test_length = test_length
        self.msg_size = msg_size
        self.interrupt_cmd = Command('cat /proc/interrupts')

    def get_parsed_interrupts(self, ignore_cpu_interrupts=True):
        # TODO think about ignoring IRQ0: timer
        self.interrupt_cmd.run()
        cmd_out = self.interrupt_cmd.watch_output()[0].strip()

        # split output by lines
        lines = cmd_out.split('\n')

        # count number of cpu and add collumn for IRQ id and comment
        num_of_columns = len(lines[0].split()) + 2

        # delete line with header
        lines.pop(0)

        # split every line by column
        # -1 to columns are separated by num_of_columns - 1 spaces
        int_table = [line.split(maxsplit=num_of_columns-1) for line in lines]

        # if ignore_cpu_interrupt option is enabled, it allows only interrupts which names starts with numbers
        if ignore_cpu_interrupts:
            int_table = list(filter(lambda line: re.match(r'[0-9]+:', line[0]), int_table))

        # delete the first and the last column, which contain IRQ id and description
        int_table = [line[1:-1] for line in int_table]

        # convert into integer
        int_table = [list(map(int, parsed_line)) for parsed_line in int_table]

        return int_table

    def run_scenario(self) -> Section:
        """
        Steps:
            -> run iPerf3 tests without catching outputs (generating interrupts)
            -> parse /proc/interrupts file
            -> evaluate results
            -> store results into dataformat package
        """
        logger.info('Running scenario: %s' % self)

        for path in self.paths:
            iperf3_test = Iperf3Test(client=path.their_ip, bind=path.mine_ip, time=self.test_length, len=self.msg_size)
            iperf3_test.run()
            out, ret = iperf3_test.watch_output()
            if ret:
                logger.error(f'iPerf3 {iperf3_test} test failed!!!')

        int_table = self.get_parsed_interrupts()
        cpu_sums = [sum(int_table[y][x] for y in range(len(int_table))) for x in range(len(int_table[0]))]

        test_result = '1' if cpu_sums[0] < sum(cpu_sums[1:]) else '0'

        logger.info(f'Sums of interrupts per CPU: {cpu_sums}')
        logger.info(f'Evaluation of testing condition: {cpu_sums[0]} < {sum(cpu_sums[1:])} ???')
        logger.info(f'{self.__class__.__name__} test result: {test_result}.')

        root_sec = Section('scenario')
        root_sec.params['scenario_name'] = self.__class__.__name__
        root_sec.params['uuid'] = uuid.uuid5(uuid.NAMESPACE_DNS, self.__class__.__name__)

        runs = Section('runs')
        run = Section('run')
        item = Section('item', key='irq_balance_check', value=test_result)

        root_sec.subsections.append(runs)
        runs.subsections.append(run)
        run.subsections.append(item)

        return root_sec
