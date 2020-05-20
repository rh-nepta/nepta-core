import json
import abc
import numpy as np
from statistics import stdev
from enum import Enum
from singledispatchmethod import singledispatchmethod

from nepta.core.distribution.command import Command
from nepta.core.tests.cmd_tool import CommandTool, CommandArgument


class Iperf3TestResult(object):
    """
    This class represents parsed result of iPerf3 test based on
    its JSON output. It also allows data formatting, result
    objects addition and iteration.
    """

    class ThroughputFormat(Enum):
        BPS = 1
        KBPS = 1e3
        MBPS = 1e6
        GBPS = 1e9

    # _DIMENSIONS variables stores mapping key -> variable in object numpy array
    _DIMENSIONS = {}

    @classmethod
    @abc.abstractmethod
    def from_json(cls, json_data):
        """
        Parse important results from iPerf3 test output in JSON format.
        :param json_data: parsed JSON
        :return: Iperf3TestResult object with parsed data
        """
        pass

    def __init__(self, array, formatter=None):
        self._array = array
        self._format_func = formatter if formatter is not None else lambda x: x

    # decorator needed to enable polymorphism
    @singledispatchmethod
    def __add__(self, other):
        """
        Add two np.arrays together and create new result object. Pass the formatting
        function ass well.
        :param other: Iperf3TestResultObject object
        :return: new instance of Iperf3TestResultObject containing self + other
        """
        return self.__class__(self._array + other._array, self._format_func)

    @__add__.register(int)
    def _(self, other):
        """
        Add number to each part of Iperf3TestResult object.
        Needed by builtin sum().
        :param other: int
        :return:
        """
        return self.__class__(self._array + other, self._format_func)

    # addition operation is commutative
    def __radd__(self, other):
        return self.__add__(other)

    def set_data_formatter(self, func):
        self._format_func = func
        return self

    def __iter__(self):
        return iter({k: self._format_func(v) for k, v in zip(self._DIMENSIONS, self._array)}.items())

    def __getitem__(self, item):
        return self._format_func(self._array[self._DIMENSIONS[item]])


class Iperf3TCPTestResult(Iperf3TestResult):
    _DIMENSIONS = {name: order for order, name in enumerate(['throughput', 'local_cpu', 'remote_cpu', 'stddev'])}

    @classmethod
    def from_json(cls, json_data):
        end = json_data['end']
        std_dev = stdev([x['sum']['bits_per_second'] for x in json_data['intervals']])

        return cls(
            np.array(
                [
                    end['sum_received']['bits_per_second'],
                    end['cpu_utilization_percent']['host_total'],
                    end['cpu_utilization_percent']['remote_total'],
                    std_dev,
                ]
            )
        )


class Iperf3UDPTestResult(Iperf3TestResult):
    _DIMENSIONS = {
        name: order
        for order, name in enumerate(['sender_throughput', 'receiver_throughput', 'local_cpu', 'remote_cpu', 'stddev'])
    }

    @classmethod
    def from_json(cls, json_data):
        end = json_data['end']
        std_dev = stdev([x['sum']['bits_per_second'] for x in json_data['intervals']])

        return cls(
            np.array(
                [
                    end['sum']['bits_per_second'],
                    end['sum']['bits_per_second'] * (1 - end['sum']['lost_percent'] / 100),
                    end['cpu_utilization_percent']['host_total'],
                    end['cpu_utilization_percent']['remote_total'],
                    std_dev,
                ]
            )
        )


class Iperf3(CommandTool):
    """
    This is definition of global arguments for CLI tool called iPerf3.
    You should NOT create objects from this class. It is just abstract
    definition of iPerf3 program.
    """

    PROGRAM_NAME = 'iperf3'
    MAPPING = [
        CommandArgument('port', '--port'),
        CommandArgument('bind', '--bind'),
        CommandArgument('json', '--json', default_value=True, argument_type=bool),
        CommandArgument('affinity', '--affinity'),
    ]


class Iperf3Server(Iperf3):
    """
    This child class of iPerf3 class serves for creation of iPerf3
    services running on servers. It should be run on second server
    of test pair, to enable iPerf3 test listener.
    """

    MAPPING = Iperf3.MAPPING + [
        CommandArgument('server', '--server', argument_type=bool, default_value=True),
        CommandArgument('daemon', '--daemon', argument_type=bool, default_value=True),
    ]


class Iperf3Test(Iperf3Server):
    """
    This is definition of arguments for iPerf3 client specific
    arguments. It also ingerits global arguments.
    Output for each test case is returned to caller, because
    there are various different requirements for test output.
    """

    MAPPING = Iperf3.MAPPING + [
        CommandArgument('interval', '--interval'),
        CommandArgument('client', '--client', required=True),
        CommandArgument('time', ' --time'),
        CommandArgument('len', '--len'),
        CommandArgument('sctp', '--sctp', argument_type=bool),
        CommandArgument('udp', '--udp', argument_type=bool),
        CommandArgument('bitrate', '--bitrate'),
        CommandArgument('parallel', '--parallel'),
        CommandArgument('reverse', '--reverse', argument_type=bool),
        CommandArgument('congestion', '--congestion'),
        CommandArgument('zerocopy', '--zerocopy', argument_type=bool),
    ]

    def run(self):
        """
        Execute current command with no debug logs.
        """
        self._cmd = Command(self._make_cmd(), enable_debug_log=False)
        self._cmd.run()

    def get_json_out(self):
        if self._output is None:
            self.watch_output()
        json_start = self._output.find('{')
        return json.loads(self._output[json_start:])

    def get_result(self, throughput_format=Iperf3TestResult.ThroughputFormat.MBPS):
        if self.udp:
            test = Iperf3UDPTestResult.from_json(self.get_json_out())
            test._array[test._DIMENSIONS['sender_throughput']] = test['sender_throughput'] / throughput_format.value
            test._array[test._DIMENSIONS['receiver_throughput']] = test['receiver_throughput'] / throughput_format.value
        else:
            test = Iperf3TCPTestResult.from_json(self.get_json_out())
            test._array[test._DIMENSIONS['throughput']] = test['throughput'] / throughput_format.value
        test._array[test._DIMENSIONS['stddev']] = test['stddev'] / throughput_format.value
        return test
