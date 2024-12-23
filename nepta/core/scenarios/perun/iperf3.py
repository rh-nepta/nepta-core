import logging
import os.path

from nepta.core.scenarios.perun.generic import PerunMixin
from nepta.core.scenarios.iperf3.tcp import Iperf3TCPStream, Iperf3TCPMultiStream

from nepta.core.tests.iperf3 import Iperf3Perf
from nepta.dataformat import Section

logger = logging.getLogger(__name__)


class Iperf3TCPStreamPerun(PerunMixin, Iperf3TCPStream):

    def init_test(self, path, size):
        iperf_test = Iperf3Perf(
            client=path.their_ip.ip,
            bind=path.mine_ip.ip,
            time=self.test_length,
            len=size,
            interval=self.interval,
            perun_output_file=os.path.join(self.perun_directory, f"{path.id}_{size}.perf.data"),
        )
        if path.cpu_pinning:
            iperf_test.affinity = ",".join([str(x) for x in path.cpu_pinning[0]])
        elif self.cpu_pinning:
            iperf_test.affinity = ",".join([str(x) for x in self.cpu_pinning[0]])
        return iperf_test

    def store_instance(self, section, test):
        section.subsections.append(Section("item", key="perun_data", value=test.perun_output_file))
        return super().store_instance(section, test)


class Iperf3TCPReversedPerun(Iperf3TCPStreamPerun):
    def init_test(self, path, size):
        iperf_test = super().init_test(path, size)
        iperf_test.reverse = True
        return iperf_test
