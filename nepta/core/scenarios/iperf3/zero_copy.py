from nepta.core.scenarios.iperf3.stream import Iperf3TCPStream, Iperf3TCPReversed, Iperf3TCPMultiStream, \
    Iperf3TCPDuplexStream


class Iperf3TCPStreamZeroCopy(Iperf3TCPStream):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.zerocopy = True
        return iperf_test


class Iperf3TCPReversedZeroCopy(Iperf3TCPStreamZeroCopy, Iperf3TCPReversed):
    pass


class Iperf3TCPDuplexStreamZeroCopy(Iperf3TCPDuplexStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for test in tests:
            test.zerocopy = True
        return tests


class Iperf3TCPMultiStreamZeroCopy(Iperf3TCPMultiStream):
    def init_all_tests(self, path, size):
        tests = super().init_all_tests(path, size)
        for test in tests:
            test.zerocopy = True
        return tests
