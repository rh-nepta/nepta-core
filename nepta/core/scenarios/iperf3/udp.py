from nepta.core.scenarios.iperf3.tcp import Iperf3TCPStream, Iperf3TCPReversed, Iperf3TCPMultiStream, \
    Iperf3TCPDuplexStream


class Iperf3UDPStream(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.udp = True
        iperf_test.bitrate = 0
        return iperf_test


class Iperf3UDPSanity(Iperf3UDPStream):
    pass


class Iperf3UDPReversed(Iperf3TCPReversed, Iperf3UDPStream):
    pass


class Iperf3UDPMultiStream(Iperf3TCPMultiStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for test in tests:
            test.udp = True
            test.bitrate = 0
        return tests


class Iperf3UDPDuplexStream(Iperf3TCPDuplexStream, Iperf3UDPMultiStream):
    pass
