import logging
import time

from testing.scenarios.generic.scenario import SingleStreamGeneric
from testing.distribution.components import Attero
from libres.store import Section


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


class NetemConstricted(SingleStreamGeneric):
    """
    This scenario runs several test stream over network emulator and turns on attero emulator during execution.
    The bandwidth chart should look like this ---___--- -> '-' means untouched network; '_' turn on impairment
    """

    def __init__(self, paths, constricted_bw, init_time, constricted_time, direction, **kwargs):
        super().__init__(paths, **kwargs)
        self.constricted_bw = constricted_bw
        self.init_time = init_time
        self.constricted_time = constricted_time
        self.direction = direction

    def store_msg_size(self, section, size, cpu_pinning=None):
        super().store_msg_size(section, size, cpu_pinning)
        test_settings_sec = section.subsections.filter('test_settings')[0]
        test_settings_sec.add_sub_section(Section('item', key='constricted_bw',  value=self.constricted_bw))
        test_settings_sec.add_sub_section(Section('item', key='direction',  value=self.direction))
        test_settings_sec.add_sub_section(Section(
            'item', key='constricted_time[%]',  value="{:.2f}%".format(self.constricted_time/self.test_length*100)))
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
