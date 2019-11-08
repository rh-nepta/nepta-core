import logging
import time

from nepta.core.scenarios.generic.scenario import SingleStreamGeneric
from nepta.core.distribution.components import Attero
from nepta.dataformat import Section


logger = logging.getLogger(__name__)


class StaticCongestion(SingleStreamGeneric):

    def run_scenario(self):
        """
        Cleaning Attero after end of this scenario.
        """
        sec = super().run_scenario()
        Attero.clear_existing_impairments()
        return sec

    @staticmethod
    def setup_attero(path):
        Attero.clear_existing_impairments()
        Attero.set_delay_and_bottleneck_bandwidth("AB", path.delay, path.limit_bandwidth)
        Attero.set_delay_and_bottleneck_bandwidth("BA", path.delay, path.limit_bandwidth)
        Attero.start()
        logger.info("Attero is set and running tests on this path")

    def run_path(self, path):
        """
        Before running tests on this path, Attero network emulator is set according to path attributes.
        """
        self.setup_attero(path)
        return super().run_path(path)


class NetemConstricted(StreamGeneric):
    """
    This scenario runs several test stream over network emulator and turns on attero emulator during execution.
    The constricted bandwidth is changed during test and is defined by "construction" parameter.
    """

    def __init__(self, paths, start_time, constrictions, direction, **kwargs):
        super().__init__(paths, **kwargs)
        self.start_time = start_time
        self.constrictions = constrictions
        self.direction = direction

    def store_msg_size(self, section, size, cpu_pinning=None):
        super().store_msg_size(section, size, cpu_pinning)
        test_settings_sec = section.subsections.filter('test_settings')[0]
        test_settings_sec.subsections.append(Section(
            'item', key='constrictions',  value=",".join([f"{x[1]}sec@{x[0]}Gpbs" for x in self.constrictions])))
        test_settings_sec.subsections.append(Section('item', key='direction',  value=self.direction))
        return section

    def run_scenario(self):
        logger.info("Clearing attero impairments")
        Attero.clear_existing_impairments()
        logger.info("Set attero to limit bandwidth: %s kbps" % self.constricted_bw)
        Attero.set_bandwidth(self.direction, self.constricted_bw)

        ret = super().run_scenario()

        logger.info("Clearing attero impairments")
        Attero.clear_existing_impairments()

        return ret

    def run_instance(self, path, size):
        test = self.init_test(path, size)       # init testing stream
        test.run()                              # start testing stream

        time.sleep(self.init_time)              # wait init time, after this time configure attero
        Attero.start()                          # limit bandwidth
        logger.debug("Attero enabled!")
        time.sleep(self.constricted_time)
        Attero.stop()                           # unlimit bandwidth
        logger.debug("Attero disabled!")

        test.watch_output()                     # wait untill test ends
        return self.store_instance(Section('run'), test)
