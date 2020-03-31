from nepta.core.scenarios.iperf3.stream import Iperf3TCPStream, Iperf3TCPReversed, Iperf3TCPMultiStream, \
    Iperf3TCPDuplexStream


class Iperf3SCTPStream(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.sctp = True
        return iperf_test


class Iperf3SCTPSanity(Iperf3SCTPStream):
    pass
