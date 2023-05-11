import logging
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import SingleStreamGeneric, MultiStreamsGeneric, info_log_func_output
from nepta.core.tests.netperf import NetperfRrTest

logger = logging.getLogger(__name__)


class NetperfTcpRr(SingleStreamGeneric):
    TEST = 'TCP_RR'

    def init_test(self, path, size):
        cpu_pinning = path.cpu_pinning if path.cpu_pinning else self.cpu_pinning
        netperf_test = NetperfRrTest(
            src_ip=path.mine_ip.ip,
            dst_ip=path.their_ip.ip,
            length=self.test_length,
            # set local and remote sent size
            request_size=f'{size}, {size}',
            test=self.TEST,
        )
        if cpu_pinning:
            netperf_test.local_cpu = cpu_pinning[0][0]
            netperf_test.remote_cpu = cpu_pinning[0][1]
        return netperf_test

    def parse_results(self, test):
        return test.get_results()


class NetperfTcpCrr(NetperfTcpRr):
    TEST = 'TCP_CRR'


class ParallelNetperfTcpCrr(MultiStreamsGeneric):
    TEST = 'TCP_CRR'

    def init_all_tests(self, path, size):
        tests = []
        cpu_pinning_list = path.cpu_pinning if path.cpu_pinning else self.cpu_pinning
        for local, remote in cpu_pinning_list:
            new_test = NetperfRrTest(
                src_ip=path.mine_ip.ip,
                dst_ip=path.their_ip.ip,
                length=self.test_length,
                # set local and remote sent size
                request_size=f'{size}, {size}',
                test=self.TEST,
                local_cpu=local,
                remote_cpu=remote,
            )
            tests.append(new_test)
        return tests

    @info_log_func_output
    def parse_all_results(self, tests):
        result_dict = OrderedDict()
        total = sum([test.get_results() for test in tests])
        result_dict.update({'total_' + key: value for key, value in total})
        return result_dict


class ParallelNetperfTcpRr(ParallelNetperfTcpCrr):
    TEST = 'TCP_RR'
