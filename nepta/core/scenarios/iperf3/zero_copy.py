from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3MultiStream, Iperf3DuplexStream
from nepta.core.scenarios.iperf3.modifiers import make_single_stream, make_multi_stream, zerocopy_mod, reversed_dir

Iperf3TCPStreamZeroCopy = make_single_stream('Iperf3TCPStreamZeroCopy', Iperf3Stream, [zerocopy_mod])
Iperf3TCPReversedZeroCopy = make_single_stream('Iperf3TCPReversedZeroCopy', Iperf3Stream, [zerocopy_mod, reversed_dir])
Iperf3TCPMultiStreamZeroCopy = make_multi_stream('Iperf3TCPMultiStreamZeroCopy', Iperf3MultiStream, [zerocopy_mod])
Iperf3TCPDuplexStreamZeroCopy = make_multi_stream('Iperf3TCPDuplexStreamZeroCopy', Iperf3DuplexStream, [zerocopy_mod])
