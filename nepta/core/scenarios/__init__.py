import inspect
import sys

from .generic.scenario import ScenarioGeneric
# Standard streams
from .iperf3.stream import Iperf3TCPStream, Iperf3TCPReversed, Iperf3TCPDuplexStream, Iperf3TCPMultiStream, \
    Iperf3TCPSanity, Iperf3SCTPStream, Iperf3SCTPSanity
from .netperf.stream import NetperfTCPStream, NetperfTCPMaerts, NetperfTCPDuplexStream, NetperfTCPMultiStream, \
    NetperfTCPSanity, NetperfSCTPStream

# impariments
from .iperf3.stream import Iperf3NetemConstricted, Iperf3TCPStaticCongestion

# zerocopy
from .iperf3.stream import Iperf3TCPStreamZeroCopy, Iperf3TCPReversedZeroCopy, Iperf3TCPMultiStreamZeroCopy, \
    Iperf3TCPDuplexStreamZeroCopy


def get_scenario_by_name(scenario_name):
    scenario_class = None
    scenario_classes = inspect.getmembers(sys.modules['testing.scenarios'], inspect.isclass)
    for cls in scenario_classes:
        if cls[0] == scenario_name:
            scenario_class = cls[1]
            break
    return scenario_class