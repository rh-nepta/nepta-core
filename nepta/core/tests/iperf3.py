import json
import logging
import abc
import numpy as np
from enum import Enum
from singledispatchmethod import singledispatchmethod
from typing import Dict, Callable
from functools import reduce

from nepta.core.distribution.command import Command
from nepta.core.tests.cmd_tool import CommandTool, CommandArgument
from nepta.core.tests.mpstat import MPStat

logger = logging.getLogger(__name__)


class Iperf3TestResult:
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
    _DIMENSIONS: Dict[str, int] = {}

    # additional dimensions for mpstat results
    _METRICS = ['sys', 'usr', 'irq', 'soft', 'nice', 'iowait', 'steal', 'guest', 'gnice', 'idle']
    _MPSTAT_DIMENSIONS = [
        f'mpstat_{j}_{i}' for i in _METRICS for j in ['local', 'remote']
    ]

    @classmethod
    @abc.abstractmethod
    def from_json(cls, json_data: dict) -> 'Iperf3TestResult':
        """
        Parse important results from iPerf3 test output in JSON format.
        :param json_data: parsed JSON
        :return: Iperf3TestResult object with parsed data
        """
        pass

    def __init__(self, array, formatter=None, dims=None):
        self._array: np.array = array
        self._dims: dict = dims if dims else self._DIMENSIONS
        self._format_func: Callable[[str], str] = formatter if formatter is not None else lambda x: x

    def __str__(self):
        return 'iPerf3 parsed test results >> ' + \
               ' | '.join([f'{k}->{v}' for k, v in self])

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
        return iter({k: self._format_func(v) for k, v in zip(self._dims, self._array)}.items())

    def __getitem__(self, item):
        return self._format_func(self._array[self._dims[item]])

    def __setitem__(self, key, value):
        self._array[self._dims[key]] = value

    def add_mpstat(self, local: MPStat, remote: MPStat) -> 'Iperf3TestResult':
        self['local_cpu'] = 100 - local.last_cpu_load()['idle']
        self['remote_cpu'] = 100 - remote.last_cpu_load()['idle']

        self._mpstat_from_dict(local.last_cpu_load(), remote.last_cpu_load())
        return self

    def add_mpstat_sum(self, local: MPStat, remote: MPStat) -> 'Iperf3TestResult':
        def add_dict(a: dict, b: dict):
            assert set(a.keys()) == set(b.keys())
            return {k: a[k] + b[k] for k in a.keys()}

        local_data = reduce(add_dict, local.cpu_loads())
        remote_data = reduce(add_dict, remote.cpu_loads())

        self['local_cpu'] = 100 - local_data['idle']
        self['remote_cpu'] = 100 - remote_data['idle']

        self._mpstat_from_dict(local_data, remote_data)
        return self

    def _mpstat_from_dict(self, local: dict, remote: dict) -> 'Iperf3TestResult':
        self._array = np.array(self._array.tolist() + [
            x[y]
            for y in self._METRICS
            for x in [local, remote]
        ])
        self._dims.update({
            k: v for v, k in enumerate(self._MPSTAT_DIMENSIONS, max(self._dims.values()) + 1)
        })
        return self


class Iperf3TCPTestResult(Iperf3TestResult):
    _DIMENSIONS = {name: order for order, name in enumerate(['throughput', 'local_cpu', 'remote_cpu'])}

    @classmethod
    def from_json(cls, json_data: dict) -> Iperf3TestResult:
        end = json_data['end']

        return cls(
            np.array(
                [
                    end['sum_received']['bits_per_second'],
                    end['cpu_utilization_percent']['host_total'],
                    end['cpu_utilization_percent']['remote_total'],
                ]
            )
        )


class Iperf3UDPTestResult(Iperf3TCPTestResult):
    _DIMENSIONS = {
        name: order
        for order, name in enumerate(['sender_throughput', 'receiver_throughput', 'local_cpu', 'remote_cpu'])
    }

    @classmethod
    def from_json(cls, json_data: dict):
        end = json_data['end']

        return cls(
            np.array(
                [
                    end['sum']['bits_per_second'],
                    end['sum']['bits_per_second'] * (1 - end['sum']['lost_percent'] / 100),
                    end['cpu_utilization_percent']['host_total'],
                    end['cpu_utilization_percent']['remote_total'],
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

    def get_json_out(self) -> dict:
        if self._output is None:
            self.watch_output()
        if self._output is not None:
            json_start = self._output.find('{')
            return json.loads(self._output[json_start:])
        else:
            raise RuntimeError('The iPerf3 JSON output is not available.')

    def get_result(self, throughput_format=Iperf3TestResult.ThroughputFormat.MBPS) -> Iperf3TestResult:
        if self.udp:
            test = Iperf3UDPTestResult.from_json(self.get_json_out())
            test['sender_throughput'] /= throughput_format.value
            test['receiver_throughput'] /= throughput_format.value
        else:
            test = Iperf3TCPTestResult.from_json(self.get_json_out())
            test['throughput'] /= throughput_format.value
        return test


class Iperf3MPStat(Iperf3Test):

    def __init__(self, **kwargs):
        super(Iperf3MPStat, self).__init__(**kwargs)
        self._loc_mpstat: MPStat = None
        self._rem_mpstat: MPStat = None

    def run(self):
        self._loc_mpstat = MPStat(interval=self.time, cpu_list=self.affinity.split(',')[0], count=1, output='JSON')
        self._rem_mpstat = MPStat(interval=self.time, cpu_list=self.affinity.split(',')[1], count=1, output='JSON')
        self._loc_mpstat.run()
        self._rem_mpstat.remote_run(self.client)
        super(Iperf3MPStat, self).run()

    def get_result(self, throughput_format=Iperf3TestResult.ThroughputFormat.MBPS):
        result = super(Iperf3MPStat, self).get_result()
        result.add_mpstat(self._loc_mpstat, self._rem_mpstat)
        return result
