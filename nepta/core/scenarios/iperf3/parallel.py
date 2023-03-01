import logging
import traceback
import sys
from functools import wraps
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import ParallelPathGeneric, info_log_func_output
from nepta.core.scenarios.iperf3.generic import GenericIPerf3Stream, catch_and_log_exception

from nepta.core.tests import Iperf3Test, MPStat, RemoteMPStat

logger = logging.getLogger(__name__)


class Iperf3TCPParallelPath(GenericIPerf3Stream, ParallelPathGeneric):
    def init_all_tests(self, paths, size):
        tests = []
        cpu_pinning_list = paths.cpu_pinning if paths.cpu_pinning else self.cpu_pinning
        for port, path, cpu in zip(range(self.base_port, self.base_port + len(paths)), paths, cpu_pinning_list):
            new_test = Iperf3Test(
                client=path.their_ip,
                bind=path.mine_ip,
                time=self.test_length,
                len=size,
                port=port,
                interval=self.interval,
                parallel=self.parallel,
            )
            new_test.affinity = ','.join([str(x) for x in cpu])
            tests.append(new_test)

        assert len(tests) == len(paths), 'The number of tests is not equal to the number of defined paths!'
        tests.append(
            MPStat(interval=self.test_length, count=1, cpu_list=','.join([str(x[0]) for x in cpu_pinning_list]))
        )
        tests.append(
            RemoteMPStat(
                host=path.their_ip,
                interval=self.test_length,
                count=1,
                cpu_list=','.join([str(x[1]) for x in cpu_pinning_list]),
            )
        )

        return tests

    @info_log_func_output
    @catch_and_log_exception
    def parse_all_results(self, tests):
        mpstats = tests[-2:]
        tests = tests[:-2]
        total = sum([test.get_result() for test in tests])

        total.add_mpstat_sum(*mpstats)
        total.set_data_formatter(self.str_round)

        result_dict = OrderedDict({'total_' + key: value for key, value in total})
        return result_dict
