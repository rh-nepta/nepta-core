import logging
import json
from functools import reduce
from typing import Dict, List
from subprocess import TimeoutExpired
from nepta.core.tests.cmd_tool import CommandArgument, CommandTool

logger = logging.getLogger(__name__)


class SockPerf(CommandTool):
    PROGRAM_NAME = "sockperf"

    MAPPING = [
        CommandArgument("ip", "--ip"),
        CommandArgument("tcp", "--tcp", argument_type=bool),
    ]


class SockPerfServer(SockPerf):
    PROGRAM_NAME = "sockperf server"

    MAPPING = SockPerf.MAPPING + [
        CommandArgument("daemonize", "--daemonize", argument_type=bool),
    ]

    def start(self):
        logger.info("Starting sockperf server")

        try:
            # The command freezes on the correct startup
            self.run()
            out, errs = self._cmd.communicate(timeout=5)
            out = out.decode()
        except TimeoutExpired:
            logger.warning("Sockperf server communicate timed out, probably running OK.")
            self._cmd.terminate()
            self.clear()
        else:
            if 'errno=' in out:
                logger.warning(out)
                logger.error(
                    "Cannot start sockperf server !!! " "To restart the server use \"killall sockperf\" and try again."
                )


class SockPerfPingPong(SockPerf):
    PROGRAM_NAME = "sockperf pp"

    MAPPING = SockPerf.MAPPING + [
        CommandArgument("time", "--time", argument_type=int, default_value=1),
        CommandArgument("full_log", "--full-log", argument_type=bool),
    ]

    def get_result(self) -> dict:
        if self.full_log:
            return self._parse_csv()
        else:
            raise RuntimeError("Full log is not enabled, cannot parse results")

    def _parse_csv(self) -> dict:
        raise NotImplementedError()
