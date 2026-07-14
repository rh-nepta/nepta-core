from nepta.core.scenarios.iperf3.generic import Iperf3Stream, Iperf3MultiStream, Iperf3DuplexStream
from nepta.core.scenarios.iperf3.modifiers import make_alias, make_single_stream, make_multi_stream, udp, reversed_dir

Iperf3UDPStream = make_single_stream('Iperf3UDPStream', Iperf3Stream, [udp])
Iperf3UDPSanity = make_alias('Iperf3UDPSanity', Iperf3UDPStream)
Iperf3UDPReversed = make_single_stream('Iperf3UDPReversed', Iperf3Stream, [udp, reversed_dir])
Iperf3UDPMultiStream = make_multi_stream('Iperf3UDPMultiStream', Iperf3MultiStream, [udp])
Iperf3UDPDuplexStream = make_multi_stream('Iperf3UDPDuplexStream', Iperf3DuplexStream, [udp])
