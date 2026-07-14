from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3DuplexStream, Iperf3MultiStream
from nepta.core.scenarios.iperf3.modifiers import make_alias, make_single_stream, reversed_dir

Iperf3TCPSanity = make_alias('Iperf3TCPSanity', Iperf3Stream)
Iperf3TCPStream = make_alias('Iperf3TCPStream', Iperf3Stream)
Iperf3TCPReversed = make_single_stream('Iperf3TCPReversed', Iperf3Stream, [reversed_dir])
Iperf3TCPMultiStream = make_alias('Iperf3TCPMultiStream', Iperf3MultiStream)
Iperf3TCPDuplexStream = make_alias('Iperf3TCPDuplexStream', Iperf3DuplexStream)
