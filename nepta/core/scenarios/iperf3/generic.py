import logging
import traceback
import sys
from functools import wraps
from collections import OrderedDict

from nepta.core.scenarios.generic.scenario import info_log_func_output
from nepta.core.scenarios.generic.scenario import SingleStreamGeneric, MultiStreamsGeneric, DuplexStreamGeneric

from nepta.core.tests import Iperf3Test, Iperf3MPStat, MPStat, RemoteMPStat

logger = logging.getLogger(__name__)


def catch_and_log_exception(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f'An error {e} occurred during test execution. iPerf3 output is :')
            if hasattr(args[1], '__iter__'):
                for test in args[1]:
                    logger.error(test.get_json_out())
            else:
                logger.error(args[1].get_json_out())
            logger.error('Traceback of catch exception :')
            logger.error(traceback.print_exc(file=sys.stdout))
        return OrderedDict()

    return wrapper


class GenericIPerf3Stream(object):
    def __init__(self, *args, interval=None, parallel=None, **kwargs):
        super(GenericIPerf3Stream, self).__init__(*args, **kwargs)
        self.interval = interval
        self.parallel = parallel

    @staticmethod
    def log_iperf3_error(out_json):
        try:
            logger.error(out_json['error'])
        except KeyError:
            pass

    @classmethod
    def mbps(cls, num):
        return cls.str_round(num / 10.0**6)

    @staticmethod
    def str_round(num, decimal=2):
        return '{:.{}f}'.format(num, decimal)


#######################################################################################################################
# Single stream scenarios
#######################################################################################################################


class Iperf3Stream(GenericIPerf3Stream, SingleStreamGeneric):
    def init_test(self, path, size):
        iperf_test = Iperf3MPStat(
            client=path.their_ip.ip, bind=path.mine_ip.ip, time=self.test_length, len=size, interval=self.interval
        )
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


#######################################################################################################################
# Mutli stream scenarios
#######################################################################################################################


class Iperf3MultiStream(GenericIPerf3Stream, MultiStreamsGeneric):
    def init_all_tests(self, path, size):
        tests = []
        cpu_pinning_list = path.cpu_pinning if path.cpu_pinning else self.cpu_pinning
        for port, cpu_pinning in zip(range(self.base_port, self.base_port + len(cpu_pinning_list)), cpu_pinning_list):
            new_test = Iperf3Test(
                client=path.their_ip.ip,
                bind=path.mine_ip.ip,
                time=self.test_length,
                len=size,
                port=port,
                interval=self.interval,
                parallel=self.parallel,
            )
            new_test.affinity = ','.join([str(x) for x in cpu_pinning])
            tests.append(new_test)

        tests.append(
            MPStat(interval=self.test_length, count=1, cpu_list=','.join([str(x[0]) for x in cpu_pinning_list]))
        )
        tests.append(
            RemoteMPStat(
                host=path.their_ip.ip,
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


class Iperf3DuplexStream(DuplexStreamGeneric, Iperf3MultiStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for i in range(1, len(tests) - 2, 2):
            tests[i].reverse = True
        return tests

    @info_log_func_output
    @catch_and_log_exception
    def parse_all_results(self, tests):
        result_dict = OrderedDict()
        mpstats = tests[-2:]
        tests = tests[:-2]

        stream_test_result = sum([test.get_result() for test in tests[::2]])
        stream_test_result.set_data_formatter(self.str_round)
        reversed_test_result = sum([test.get_result() for test in tests[1::2]])
        reversed_test_result.set_data_formatter(self.str_round)

        total = stream_test_result + reversed_test_result
        total.add_mpstat_sum(*mpstats)
        result_dict['up_throughput'] = stream_test_result['throughput']
        result_dict['down_throughput'] = reversed_test_result['throughput']
        result_dict.update({'total_' + key: value for key, value in total})
        return result_dict
