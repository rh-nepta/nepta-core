from nepta.core.scenarios.generic.congestion import NetemConstricted, StaticCongestion
from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3MultiStream


class Iperf3SingleStreamNetemConstricted(NetemConstricted, Iperf3Stream):
    pass


class Iperf3MultiStreamNetemConstricted(NetemConstricted, Iperf3MultiStream):
    pass


class Iperf3TCPStaticCongestion(StaticCongestion, Iperf3Stream):
    def init_test(self, path, size):
        test = super().init_test(path, size)
        test.congestion = path.cca
        return test
