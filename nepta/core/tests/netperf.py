import logging
from collections import Counter
from nepta.core.tests.cmd_tool import CommandArgument, CommandTool

logger = logging.getLogger(__name__)


class NetperfStreamResult(dict):
    def __init__(self, *args, **kwargs):
        super(NetperfStreamResult, self).__init__(*args, **kwargs)
        self._format_func = lambda x: f'{x:.2f}'

    def __add__(self, other):
        result = self.__class__()
        for k, v in self.items():
            if isinstance(other, int):
                result[k] = v + other
            else:
                result[k] = v + other[k]
        return result

    def __radd__(self, other):
        return self.__add__(other)

    def __iter__(self):
        return iter({k: self._format_func(v) for k, v in self.items()}.items())


class GenericNetperfTest(CommandTool):
    PROGRAM_NAME = 'netperf'

    MAPPING = [
        CommandArgument(
            'src_ip',
            '-L',
        ),
        CommandArgument('dst_ip', '-H', True),
        CommandArgument('length', '-l'),
        CommandArgument('report_local_cpu', '-c', argument_type=bool, default_value=True),
        CommandArgument('report_remote_cpu', '-C', argument_type=bool, default_value=True),
        CommandArgument('headers', '-P', default_value='0'),
        CommandArgument('local_cpu', '-T'),
        CommandArgument('remote_cpu', '-T ,'),
        CommandArgument('test', '-t'),
    ]

    TEST_MAPPING = [  # this is used for definition of specific arguments for each test TCP_STEAM/UDP_STREAM/TCP_MAERTS
        CommandArgument('local_send', '-m'),
        CommandArgument('remote_send', '-m ,'),
        CommandArgument('local_recv', '-M'),
        CommandArgument('remote_recv', '-M ,'),
        CommandArgument('request_size', '-r'),
    ]

    def _init_class_attr(self):
        """
        Create object attributes for each argument defined in MAPPING.
        """
        for arg in self.MAPPING + self.TEST_MAPPING:
            self.__dict__[arg.class_name] = arg.default_value

    def _make_cmd(self):
        return super()._make_cmd() + ' -- ' + self._make_cli_args(self.TEST_MAPPING)


class NetperStreamfTest(GenericNetperfTest):
    ALL_LABELS = [
        'rcv_socket_size',
        'snd_socket_size',
        'msg_size',
        'time',
        'throughput',
        'loc_cpu',
        'rem_cpu',
        'service_local',
        'service_remote',
    ]

    RESULT_LABELS = [
        'throughput',
        'loc_cpu',
        'rem_cpu',
    ]

    def get_results(self):
        ret = {}
        if self._exit_code != 0:
            ret['return_code'] = str(self._exit_code)
            ret['output'] = str(self._output)
            logger.warning('TEST FAILED, with exitcode: %s\noutput: %s', ret['return_code'], ret['output'])
            return ret

        # netperf result sometimes contain warinning string:
        # catcher: timer popped with times_up != 0
        # this is workaround for that case

        warning_string = 'catcher: timer popped with times_up != 0'
        if self._output.find(warning_string) >= 0:
            output_parts = self._output[len(warning_string) :].split()
            ret['warning'] = warning_string
        else:
            output_parts = self._output.split()

        ret.update({k: float(v) for k, v in zip(self.ALL_LABELS, output_parts)})

        logger.info('test results: %s', ret)
        return NetperfStreamResult({k: v for k, v in ret.items() if k in self.RESULT_LABELS})


class NetperfRrTest(NetperStreamfTest):
    ALL_LABELS = [
        'rcv_socket_size',
        'snd_socket_size',
        'req_size',
        'rep_size',
        'time',
        'transactions',
        'loc_cpu',
        'rem_cpu',
        'service_local',
        'service_remote',
    ]

    RESULT_LABELS = [
        'transactions',
        'loc_cpu',
        'rem_cpu',
    ]
