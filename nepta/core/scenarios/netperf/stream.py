import logging
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import SingleStreamGeneric, MultiStreamsGeneric, DuplexStreamGeneric
from nepta.core.tests import NetperStreamfTest

logger = logging.getLogger(__name__)


def round_f(num, decimal=2):
    return '{:.{}f}'.format(num, decimal)


class NetperfTCPStream(SingleStreamGeneric):
    def init_test(self, path, size):
        netperf_test = NetperStreamfTest(
            src_ip=path.mine_ip, dst_ip=path.their_ip, length=self.test_length, local_send=size, test='TCP_STREAM',
        )
        if self.cpu_pinning:
            netperf_test.local_cpu = self.cpu_pinning[0]
            netperf_test.remote_cpu = self.cpu_pinning[1]
        return netperf_test

    def parse_results(self, test):
        result_dict = OrderedDict()
        test_result = test.get_results()
        try:
            result_dict['throughput'] = test_result['throughput']
            result_dict['local_cpu'] = test_result['loc_util']
            result_dict['remote_cpu'] = test_result['rem_util']
        except KeyError:
            logging.error('Parsed NetperfDict has different structure than %s test except!!!' % self.__class__.__name__)
        return result_dict


class NetperfTCPSanity(NetperfTCPStream):
    pass


class NetperfSCTPStream(NetperfTCPStream):
    def init_test(self, path, size):
        netperf_test = super().init_test(path, size)
        netperf_test.test = 'SCTP_STREAM'
        return netperf_test


class NetperfTCPMaerts(NetperfTCPStream):
    def init_test(self, path, size):
        netperf_test = super().init_test(path, size)
        netperf_test.test = 'TCP_MAERTS'
        netperf_test.local_send = None
        netperf_test.remote_send = size
        return netperf_test


class NetperfTCPDuplexStream(DuplexStreamGeneric):
    def init_all_tests(self, path, size):
        netperf_test = NetperStreamfTest(
            src_ip=path.mine_ip, dst_ip=path.their_ip, length=self.test_length, local_send=size, test='TCP_STREAM'
        )
        maerts_test = NetperStreamfTest(
            src_ip=path.mine_ip, dst_ip=path.their_ip, length=self.test_length, local_send=size, test='TCP_MAERTS'
        )
        if self.cpu_pinning:
            netperf_test.local_cpu, netperf_test.remote_cpu = self.cpu_pinning[0]
            maerts_test.local_cpu, maerts_test.remote_cpu = self.cpu_pinning[1]

        return netperf_test, maerts_test

    def parse_all_results(self, tests):
        result_dict = OrderedDict()

        stream_test_result = tests[0].get_results()
        maerts_test_result = tests[1].get_results()

        result_dict['up_throughput'] = float(stream_test_result['throughput'])
        result_dict['down_throughput'] = float(maerts_test_result['throughput'])
        result_dict['total_throughput'] = round_f(result_dict['up_throughput'] + result_dict['down_throughput'])
        result_dict['avg_local_cpu'] = round_f(
            float(stream_test_result['loc_util']) + float(maerts_test_result['loc_util'])
        )
        result_dict['avg_remote_cpu'] = round_f(
            float(stream_test_result['rem_util']) + float(maerts_test_result['rem_util'])
        )

        return result_dict


class NetperfTCPMultiStream(MultiStreamsGeneric):
    def init_all_tests(self, path, size):
        tests = []
        for pinning in self.cpu_pinning:
            new_test = NetperStreamfTest(
                src_ip=path.mine_ip, dst_ip=path.their_ip, length=self.test_length, local_send=size, test='TCP_STREAM'
            )
            new_test.local_cpu, new_test.remote_cpu = pinning
            tests.append(new_test)
        return tests

    def parse_all_results(self, tests):
        total, local, remote = 0, 0, 0
        for test in tests:
            result = test.get_results()
            total += float(result['throughput'])
            local += float(result['loc_util'])
            remote += float(result['rem_util'])
        result_dict = OrderedDict()
        result_dict['total_throughput'] = round_f(total)
        result_dict['avg_local_cpu'] = round_f(local)
        result_dict['avg_remote_cpu'] = round_f(remote)

        return result_dict
