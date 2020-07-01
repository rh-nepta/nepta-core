import inspect
import sys

from .generic.scenario import ScenarioGeneric
from .generic.interrupts import IRQBalanceCheck

# Standard streams
from .iperf3.tcp import Iperf3TCPStream, Iperf3TCPReversed, Iperf3TCPDuplexStream, Iperf3TCPMultiStream, Iperf3TCPSanity
from .netperf.stream import (
    NetperfTCPStream,
    NetperfTCPMaerts,
    NetperfTCPDuplexStream,
    NetperfTCPMultiStream,
    NetperfTCPSanity,
    NetperfSCTPStream,
)

# SCTP
from .iperf3.sctp import Iperf3SCTPSanity, Iperf3SCTPStream

# impariments
from .iperf3.congestion import Iperf3TCPStaticCongestion
from .iperf3.congestion import Iperf3SingleStreamNetemConstricted, Iperf3MultiStreamNetemConstricted

# zerocopy
from .iperf3.zero_copy import (
    Iperf3TCPStreamZeroCopy,
    Iperf3TCPReversedZeroCopy,
    Iperf3TCPMultiStreamZeroCopy,
    Iperf3TCPDuplexStreamZeroCopy,
)

# UDP
from .iperf3.udp import Iperf3UDPStream, Iperf3UDPReversed, Iperf3UDPMultiStream, Iperf3UDPDuplexStream, Iperf3UDPSanity


def get_scenario_by_name(scenario_name):
    scenario_class = None
    scenario_classes = inspect.getmembers(sys.modules['testing.scenarios'], inspect.isclass)
    for cls in scenario_classes:
        if cls[0] == scenario_name:
            scenario_class = cls[1]
            break
    return scenario_class
