from nepta.core.scenarios.perun.generic import PerunBpfMixin
from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3MultiStream
from nepta.core.scenarios.iperf3.modifiers import make_perun_single_stream, make_perun_multi_stream, reversed_dir
from nepta.core.tests.iperf3 import Iperf3BPF

Iperf3TCPStreamBpf = make_perun_single_stream('Iperf3TCPStreamBpf', PerunBpfMixin, Iperf3BPF, Iperf3Stream)
Iperf3TCPReversedBpf = make_perun_single_stream(
    'Iperf3TCPReversedBpf', PerunBpfMixin, Iperf3BPF, Iperf3Stream, [reversed_dir]
)
Iperf3TCPMultiStreamBpf = make_perun_multi_stream(
    'Iperf3TCPMultiStreamBpf', PerunBpfMixin, Iperf3BPF, Iperf3MultiStream
)
Iperf3TCPMultiStreamReversedBpf = make_perun_multi_stream(
    'Iperf3TCPMultiStreamReversedBpf', PerunBpfMixin, Iperf3BPF, Iperf3MultiStream, [reversed_dir]
)
