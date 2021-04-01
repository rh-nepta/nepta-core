import logging
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import SingleStreamGeneric
from nepta.core.tests.netperf import NetperfRrTest

logger = logging.getLogger(__name__)


class NetperfTcpRr(SingleStreamGeneric):
    TEST = 'TCP_RR'

    def init_test(self, path, size):
        netperf_test = NetperfRrTest(
            src_ip=path.mine_ip,
            dst_ip=path.their_ip,
            length=self.test_length,
            local_send=size,
            test=self.TEST,
        )
        if self.cpu_pinning:
            netperf_test.local_cpu = self.cpu_pinning[0]
            netperf_test.remote_cpu = self.cpu_pinning[1]
        return netperf_test

    def parse_results(self, test):
        return test.get_results()


class NetperfTcpCrr(NetperfTcpRr):
    TEST = 'TCP_CRR'
