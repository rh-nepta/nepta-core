import logging
import time
import uuid
import functools
from typing import Tuple, List, Union, Optional

from nepta.core.scenarios.sockperf.generic import SockPerfGeneric
from nepta.core.scenarios.generic.scenario import StreamGeneric, SingleStreamGeneric
from nepta.core.model.schedule import PathList, Path
from nepta.core.tests.sockperf import SockPerfPingPong

logger = logging.getLogger(__name__)

class SockPerfUdpPingPong(SingleStreamGeneric, SockPerfGeneric):

    def __init__(
        self,
        paths: Union[List[Path], PathList],
        test_length: int,
        test_runs: int,
        msg_sizes: List[int],
        cpu_pinning,
        attempt_count: int,
        attempt_pause: int,
        percentiles: Optional[List[str]] = None,
        result: bool = True,
    ):
        super().__init__(
            paths=paths,
            test_length=test_length,
            test_runs=test_runs,
            msg_sizes=msg_sizes,
            cpu_pinning=cpu_pinning,
            attempt_count=attempt_count,
            attempt_pause=attempt_pause,
            result=result,
        )
        self.percentiles = percentiles or ['25.000', '50.000', '75.000', '99.000', '99.999']

    def init_test(self, path, size):
        sockperf_test = SockPerfPingPong(
            ip=path.their_ip.ip,
            time=self.test_length,
            message_size=size,
        )
        sockperf_test.msg_size = size

        if getattr(path, 'client_affinities', None):
            sender_cores = list(path.client_affinities[0])
            receiver_cores = list(path.client_affinities[1])

            sockperf_test.sender_affinity = ",".join(str(c) for c in sender_cores)
            sockperf_test.receiver_affinity = ",".join(str(c) for c in receiver_cores)

        elif getattr(path, 'cpu_pinning', None):
            unique_cores = list(dict.fromkeys([str(x) for x in path.cpu_pinning[0]]))
            core_string = ",".join(unique_cores)

            sockperf_test.sender_affinity = core_string
            sockperf_test.receiver_affinity = core_string

        elif getattr(self, 'cpu_pinning', None):
            unique_cores = list(dict.fromkeys([str(x) for x in self.cpu_pinning[0]]))
            core_string = ",".join(unique_cores)

            sockperf_test.sender_affinity = core_string
            sockperf_test.receiver_affinity = core_string

        return sockperf_test

    def parse_results(self, test):
        results = test.get_result()
        return {k: results[k] for k in self.percentiles}
