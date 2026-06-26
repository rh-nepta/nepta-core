from nepta.core.scenarios.iperf3.generic import Iperf3Stream
from nepta.core.scenarios.iperf3.modifiers import make_alias, make_single_stream, sctp

Iperf3SCTPStream = make_single_stream('Iperf3SCTPStream', Iperf3Stream, [sctp])
Iperf3SCTPSanity = make_alias('Iperf3SCTPSanity', Iperf3SCTPStream)
