import logging
import json
from nepta.core.tests.cmd_tool import CommandArgument, CommandTool

logger = logging.getLogger(__name__)


class MPStat(CommandTool):
    PROGRAM_NAME = 'mpstat'

    MAPPING = [
        CommandArgument(
            'node_list',
            '-N',
        ),
        CommandArgument('output', '-o', default_value='JSON'),
        CommandArgument(
            'cpu_list',
            '-P',
        ),
        CommandArgument('interval', '', argument_type=int),
        CommandArgument('count', '', argument_type=int),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.count is not None and self.interval is None:
            raise ValueError('Count parameter can be specifies only with interval argument')

    def parse_json(self) -> dict:
        if self.output != 'JSON':
            raise ValueError('For json output specify output parameter as JSON')
        return json.loads(self.watch_output()[0])

    def cpu_loads(self) -> list:
        data = self.parse_json()
        cpu_loads = data['sysstat']['hosts'][0]['statistics']
        return [x['cpu-load'][0] for x in cpu_loads]

    def last_cpu_load(self) -> dict:
        return self.cpu_loads()[-1]


class RemoteMPStat(MPStat):
    def __init__(self, host: str, **kwargs):
        self._host = host
        super().__init__(**kwargs)

    def run(self):
        return self.remote_run(self._host)
