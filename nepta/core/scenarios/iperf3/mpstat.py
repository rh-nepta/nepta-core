from nepta.core.tests import Iperf3MPStat
from nepta.core.scenarios.iperf3.tcp import (
    Iperf3TCPStream,
    Iperf3TCPReversed,
    Iperf3DuplexStream,
    Iperf3MultiStream,
)


class Iperf3TCPStreamMPStat(Iperf3TCPStream):

    def init_test(self, path, size):
        test = super().init_test(path, size)
        return Iperf3MPStat(**test.__dict__)


class Iperf3TCPReversedMPStat(Iperf3TCPReversed, Iperf3TCPStreamMPStat):
    pass


class Iperf3TCPMultiMPStat(Iperf3MultiStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        return [Iperf3MPStat(**test.__dict__) for test in tests]


class Iperf3TCPDuplexMPStat(Iperf3DuplexStream, Iperf3TCPMultiMPStat):
    pass
