import json
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
        KBPS = 10e3
        MBPS = 10e6
        GBPS = 10e9

    _DIMENSIONS = {
        'throughput': 0,
        'local_cpu': 1,
        'remote_cpu': 2,
        'stddev': 3,
    }

    @classmethod
    def from_json(cls, json_data):
        """
        Parse important results from iPerf3 test output in JSON format.
        :param json_data: parsed JSON
        :return: Iperf3TestResult object with parsed data
        """
        end = json_data['end']
        std_dev = stdev(
            [x['sum']['bits_per_second'] for x in json_data['intervals']]
        )

        return cls(np.array([
            end['sum_received']['bits_per_second'],
            end['cpu_utilization_percent']['host_total'],
            end['cpu_utilization_percent']['remote_total'],
            std_dev]))

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
        return self.__class__(
            self._array + other._array, self._format_func
        )

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
        return iter({k: v for k, v in zip(self._DIMENSIONS, self._array)}.items())

    def __getattr__(self, item):
        if item in self._DIMENSIONS:
            return self._format_func(self._array[self._DIMENSIONS[item]])
        else:
            return super().__getattribute__(item)

    def __getitem__(self, item):
        return self._format_func(self._array[self._DIMENSIONS[item]])


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
        CommandArgument('zerocopy', '--zerocopy', argument_type=bool)
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
        return json.loads(self._output)

    def get_result(self, throughput_format=Iperf3TestResult.ThroughputFormat.MBPS):
        test = Iperf3TestResult.from_json(self.get_json_out())
        test.throughput = test.throughput / throughput_format.value
        return test
