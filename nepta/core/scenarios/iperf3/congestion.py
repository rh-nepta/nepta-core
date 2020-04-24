from nepta.core.scenarios.generic.congestion import NetemConstricted, StaticCongestion
from nepta.core.scenarios.iperf3.tcp import Iperf3TCPStream, Iperf3TCPMultiStream


class Iperf3SingleStreamNetemConstricted(NetemConstricted, Iperf3TCPStream):
    pass


class Iperf3MultiStreamNetemConstricted(NetemConstricted, Iperf3TCPMultiStream):
    pass


class Iperf3TCPStaticCongestion(StaticCongestion, Iperf3TCPStream):
    def init_test(self, path, size):
        test = super().init_test(path, size)
        test.congestion = path.cca
        return test
