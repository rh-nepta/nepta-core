import logging
import json
from functools import reduce
from typing import Dict, List
from nepta.core.tests.cmd_tool import CommandArgument, CommandTool

logger = logging.getLogger(__name__)


class SockPerf(CommandTool):
    PROGRAM_NAME = "sockperf"


class SockPerfServer(SockPerf):
    PROGRAM_NAME = "sockperf sr"

    MAPPING = [
        CommandArgument("daemonize", "--daemonize", argument_type=bool),
        CommandArgument("ip", "--ip"),
        CommandArgument("tcp", "--tcp", argument_type=bool),
    ]


class SockPerfPingPong(SockPerf):
    PROGRAM_NAME = "sockperf pp"

    MAPPING = [
        CommandArgument("ip", "--ip", required=True),
        CommandArgument("time", "--time", argument_type=int, default_value=1),
        CommandArgument("full_log", "--full-log", argument_type=bool),
        CommandArgument("tcp", "--tcp", argument_type=bool),
    ]

    def get_result(self) -> dict:
        if self.full_log:
            return self._parse_csv()
        else:
            raise RuntimeError("Full log is not enabled, cannot parse results")

    def _parse_csv(self) -> dict:
        raise NotImplementedError()
