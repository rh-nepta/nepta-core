import logging
import traceback
import sys
from functools import wraps
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import info_log_func_output
from nepta.core.scenarios.generic.scenario import SingleStreamGeneric, MultiStreamsGeneric, DuplexStreamGeneric
from nepta.core.scenarios.generic.congestion import NetemConstricted, StaticCongestion

from nepta.core.tests import Iperf3Test

logger = logging.getLogger(__name__)


def catch_and_log_exception(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error("An error occurred during test execution. iPerf3 output is :")
            if hasattr(args[1], "__iter__"):
                for test in args[1]:
                    logger.error(test.get_json_out())
            else:
                logger.error(args[1].get_json_out())
            logger.error("Traceback of catch exception :")
            traceback.print_exc(file=sys.stdout)
        return OrderedDict()

    return wrapper


class GenericIPerf3Stream(object):

    @staticmethod
    def log_iperf3_error(out_json):
        try:
            logger.error(out_json['error'])
        except KeyError:
            pass

    @classmethod
    def mbps(cls, num):
        return cls.str_round(num / 10.0 ** 6)

    @staticmethod
    def str_round(num, decimal=2):
        return "{:.{}f}".format(num, decimal)


#######################################################################################################################
# Single stream scenarios
#######################################################################################################################


class Iperf3TCPStream(SingleStreamGeneric, GenericIPerf3Stream):

    def init_test(self, path, size):
        iperf_test = Iperf3Test(client=path.their_ip, bind=path.mine_ip, time=self.test_length, len=size, interval=0.1)
        if path.cpu_pinning:
            iperf_test.affinity = ','.join([str(x) for x in path.cpu_pinning[0]])
        elif self.cpu_pinning:
            iperf_test.affinity = ','.join([str(x) for x in self.cpu_pinning[0]])
        return iperf_test

    @info_log_func_output
    @catch_and_log_exception
    def parse_results(self, test):
        result_dict = OrderedDict()
        result = test.get_result()
        result.set_data_formatter(self.str_round)
        result_dict.update(result)
        return result_dict


class Iperf3TCPReversed(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.reverse = True
        return iperf_test


class Iperf3TCPSanity(Iperf3TCPStream):
    pass


#######################################################################################################################
# Mutli stream scenarios
#######################################################################################################################


class Iperf3TCPDuplexStream(DuplexStreamGeneric, GenericIPerf3Stream):

    def init_all_tests(self, path, size):
        stream_test = Iperf3Test(client=path.their_ip, bind=path.mine_ip, time=self.test_length, len=size,
                                 port=self.base_port, interval=0.1)
        reverse_test = Iperf3Test(client=path.their_ip, bind=path.mine_ip, time=self.test_length, len=size,
                                  port=self.base_port + 1, interval=0.1, reverse=True)
        if path.cpu_pinning:
            stream_test.affinity = ",".join(map(str, path.cpu_pinning[0]))
            reverse_test.affinity = ",".join(map(str, path.cpu_pinning[1]))
        elif self.cpu_pinning:
            stream_test.affinity = ",".join(map(str, self.cpu_pinning[0]))
            reverse_test.affinity = ",".join(map(str, self.cpu_pinning[1]))

        return stream_test, reverse_test

    @info_log_func_output
    @catch_and_log_exception
    def parse_all_results(self, tests):
        result_dict = OrderedDict()
        stream_test_result = tests[0].get_result().set_data_formatter(self.str_round)
        reversed_test_result = tests[1].get_result().set_data_formatter(self.str_round)
        total = stream_test_result + reversed_test_result
        result_dict['up_throughput'] = stream_test_result['throughput']
        result_dict['down_throughput'] = reversed_test_result['throughput']
        result_dict.update(
            {'total_' + key: value for key, value in total}
        )
        return result_dict


class Iperf3TCPMultiStream(MultiStreamsGeneric, GenericIPerf3Stream):

    def init_all_tests(self, path, size):
        tests = []
        cpu_pinning_list = path.cpu_pinning if path.cpu_pinning else self.cpu_pinning
        for port, cpu_pinning in zip(range(self.base_port, self.base_port + len(cpu_pinning_list)), cpu_pinning_list):
            new_test = Iperf3Test(client=path.their_ip, bind=path.mine_ip, time=self.test_length, len=size, port=port,
                                  interval=0.1)
            new_test.affinity = ",".join([str(x) for x in cpu_pinning])
            tests.append(new_test)
        return tests

    @info_log_func_output
    @catch_and_log_exception
    def parse_all_results(self, tests):
        result_dict = OrderedDict(total_throughput=0, total_local_cpu=0, total_remote_cpu=0, total_stddev=0)
        total = sum([test.get_result() for test in tests])
        total.set_data_formatter(self.str_round)
        result_dict.update(
            {'total_' + key: value for key, value in total}
        )
        return result_dict


#######################################################################################################################
# SCTP scenarios
#######################################################################################################################

class Iperf3SCTPStream(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.sctp = True
        return iperf_test


class Iperf3SCTPSanity(Iperf3SCTPStream):
    pass


#######################################################################################################################
# Zero copy scenarios
#######################################################################################################################

class Iperf3TCPStreamZeroCopy(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.zerocopy = True
        return iperf_test


class Iperf3TCPReversedZeroCopy(Iperf3TCPStreamZeroCopy, Iperf3TCPReversed):
    pass


class Iperf3TCPDuplexStreamZeroCopy(Iperf3TCPDuplexStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for test in tests:
            test.zerocopy = True
        return tests


class Iperf3TCPMultiStreamZeroCopy(Iperf3TCPMultiStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for test in tests:
            test.zerocopy = True
        return tests


#######################################################################################################################
# Netem scenarios scenarios
#######################################################################################################################


class Iperf3SingleStreamNetemConstricted(NetemConstricted, Iperf3TCPStream):
    pass


class Iperf3MultiStreamNetemConstricted(NetemConstricted, Iperf3TCPMultiStream):
    pass


class Iperf3TCPStaticCongestion(StaticCongestion, Iperf3TCPStream):
    def init_test(self, path, size):
        test = super().init_test(path, size)
        test.congestion = path.cca
        return test


#######################################################################################################################
# UDP scenarios scenarios
#######################################################################################################################

class Iperf3UDPStream(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.udp = True
        iperf_test.bitrate = 0
        return iperf_test


class Iperf3UDPSanity(Iperf3UDPStream):
    pass


class Iperf3UDPReversed(Iperf3TCPReversed, Iperf3UDPStream):
    pass


class Iperf3UDPMultiStream(Iperf3TCPMultiStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for test in tests:
            test.udp = True
            test.bitrate = 0
        return tests


class Iperf3UDPDuplexStream(Iperf3TCPDuplexStream, Iperf3UDPMultiStream):
    pass
