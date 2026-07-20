from nepta.core.scenarios.perun.generic import PerunPerfMixin
from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3MultiStream
from nepta.core.scenarios.iperf3.modifiers import make_perun_single_stream, make_perun_multi_stream, udp, reversed_dir
from nepta.core.tests.iperf3 import Iperf3Perf

Iperf3TCPStreamPerf = make_perun_single_stream('Iperf3TCPStreamPerf', PerunPerfMixin, Iperf3Perf, Iperf3Stream)
Iperf3TCPReversedPerf = make_perun_single_stream(
    'Iperf3TCPReversedPerf', PerunPerfMixin, Iperf3Perf, Iperf3Stream, [reversed_dir]
)
Iperf3TCPMultiStreamPerf = make_perun_multi_stream(
    'Iperf3TCPMultiStreamPerf', PerunPerfMixin, Iperf3Perf, Iperf3MultiStream
)
Iperf3TCPMultiStreamReversedPerf = make_perun_multi_stream(
    'Iperf3TCPMultiStreamReversedPerf', PerunPerfMixin, Iperf3Perf, Iperf3MultiStream, [reversed_dir]
)
Iperf3UDPStreamPerf = make_perun_single_stream('Iperf3UDPStreamPerf', PerunPerfMixin, Iperf3Perf, Iperf3Stream, [udp])
Iperf3UDPReversedPerf = make_perun_single_stream(
    'Iperf3UDPReversedPerf', PerunPerfMixin, Iperf3Perf, Iperf3Stream, [udp, reversed_dir]
)
Iperf3UDPMultiStreamPerf = make_perun_multi_stream(
    'Iperf3UDPMultiStreamPerf', PerunPerfMixin, Iperf3Perf, Iperf3MultiStream, [udp]
)
Iperf3UDPMultiStreamReversedPerf = make_perun_multi_stream(
    'Iperf3UDPMultiStreamReversedPerf', PerunPerfMixin, Iperf3Perf, Iperf3MultiStream, [udp, reversed_dir]
)
