import logging
import time

from nepta.dataformat import Section
from nepta.core.scenarios.perun.generic import GenericPerun
from nepta.core.scenarios.iperf3.tcp import Iperf3TCPStream, Iperf3TCPMultiStream

from nepta.core.distribution.utils.perf import Perf
from nepta.core.model.schedule import PathList, Path
from nepta.core.tests.iperf3 import Iperf3Test

logger = logging.getLogger(__name__)


class Iperf3TCPStreamPerun(Iperf3TCPStream):
    def run_instance(self, path, size):
        test = self.init_test(path, size)

        for _ in range(self.attempt_count):
            output_file = f"{path.uuid}_{size}.perf.data"
            out, ret = Perf.record(test._make_cmd(), extra_options="--call-graph fp -a", output_file=output_file)
            if ret:
                return self.store_instance(Section("run"), test, output_file)

            logger.info("Measurements was unsuccessful. Trying again...")
            test.clear()
            time.sleep(self.attempt_pause)

        logger.error("Measurement fails. Returning results with zeros.")
        self.result = False
        return Section("failed-test")

    def store_instance(self, section, test, perf_file):
        Perf.fold_output(perf_file, f"{perf_file}.folded")
        return super().store_instance(section, test)


class Iperf3TCPMultiStreamPerun(PerunMixin, Iperf3TCPMultiStream):
    pass
