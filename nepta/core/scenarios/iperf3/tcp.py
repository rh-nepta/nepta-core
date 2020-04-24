import logging
from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3DuplexStream, Iperf3MultiStream

logger = logging.getLogger(__name__)


class Iperf3TCPSanity(Iperf3Stream):
    pass


class Iperf3TCPStream(Iperf3TCPSanity):
    pass


class Iperf3TCPReversed(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.reverse = True
        return iperf_test


class Iperf3TCPMultiStream(Iperf3MultiStream):
    pass


class Iperf3TCPDuplexStream(Iperf3DuplexStream):
    pass
