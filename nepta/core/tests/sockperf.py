import re
import logging
from typing import Dict, Optional
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
        CommandArgument('message_size', '--msg-size', argument_type=int),
        CommandArgument("full_log", "--full-log"),
    ]

    def get_result(self) -> dict:
        if self.full_log:
            return self._parse_csv()
        else:
            return self._parse_stdout()

    def _parse_stdout(self) -> Optional[Dict[str, float]]:
        out, code = self.watch_output()
        # Regex to find all lines starting with '--->' and capture the
        # percentile (or MAX/MIN) and its corresponding value.
        if code != 0:
            logger.error("Sockperf server failed with code: %d" % code)
            logger.error("Sockperf server stdout:\n%s" % out)
            raise RuntimeError(f"Sockperf server exited with code {code}")

        percentile_matches = re.findall(
            r"--->\s(?:percentile|<MAX>|<MIN>)\s+(?P<percentile>[\d\.]+|MAX|MIN)\s+=\s+(?P<value>[\d\.]+)", out
        )

        # Convert the list of (key, value) tuples into a dictionary
        if percentile_matches:
            return {p: float(v) for p, v in percentile_matches}
        else:
            logger.error(out)
            ValueError('Cannot parse results')

    def _parse_csv(self) -> dict:
        raise NotImplementedError()
