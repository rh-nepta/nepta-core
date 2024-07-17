import logging
import json
from functools import reduce
from typing import Dict, List
from nepta.core.tests.cmd_tool import CommandArgument, CommandTool

logger = logging.getLogger(__name__)


class MPStat(CommandTool):
    PROGRAM_NAME = "mpstat"

    MAPPING = [
        CommandArgument(
            "node_list",
            "-N",
        ),
        CommandArgument("output", "-o", default_value="JSON"),
        CommandArgument(
            "cpu_list",
            "-P",
        ),
        CommandArgument("interval", "", argument_type=int),
        CommandArgument("count", "", argument_type=int),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.count is not None and self.interval is None:
            raise ValueError("Count parameter can be specifies only with interval argument")

    def parse_json(self) -> dict:
        if self.output != "JSON":
            raise ValueError("For json output specify output parameter as JSON")
        return json.loads(self.watch_output()[0])

    def cpu_loads(self) -> List[List[Dict]]:
        data = self.parse_json()
        cpu_loads = data["sysstat"]["hosts"][0]["statistics"]
        return [x["cpu-load"] for x in cpu_loads]

    def last_cpu_load(self) -> List[Dict]:
        return self.cpu_loads()[-1]

    def sum_last_cpu_load(self) -> dict:
        def add_dict(a: dict, b: dict) -> dict:
            assert set(a.keys()) == set(b.keys())
            return {k: a[k] + b[k] for k in a.keys()}

        loads = self.last_cpu_load()
        all(map(lambda x: x.pop("cpu"), loads))
        return reduce(add_dict, loads)


class RemoteMPStat(MPStat):
    def __init__(self, host: str, **kwargs):
        self._host = host
        super().__init__(**kwargs)

    def run(self):
        return self.remote_run(self._host)
