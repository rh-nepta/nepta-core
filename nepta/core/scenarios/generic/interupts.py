import logging
import re
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.distribution.components import Command
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

        for path in self.paths:
            iperf3_test = Iperf3Test(client=path.their_ip, bind=path.mine_ip, time=self.test_length, len=self.msg_size,
                                     affinity='0,0')
            iperf3_test.run()
            # TODO maybe check ret code
            iperf3_test.watch_output()

        interrupts_table = self.get_parsed_interrupts()
        sums_per_cpu = []
