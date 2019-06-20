from time import sleep
import logging

from nepta.core.strategies.generic import Strategy
from nepta.core.model.bundles import SyncHost

logger = logging.getLogger(__name__)


class Synchronize(Strategy):

    def __init__(self, configuration, synchronizer, condition):
        super().__init__()
        self.configuration = configuration
        self.synchronizer = synchronizer
        self.condition = condition

    @Strategy.schedule
    def sync(self):
        logger.info('synchronizing for condition %s' % self.condition)
        sync_hosts = self.configuration.get_subset(m_class=SyncHost)
        hostnames = [host.hostname for host in sync_hosts]
        self.synchronizer.barier(hostnames, self.condition)


class EndSyncBarriers(Strategy):

    SYNC_WAIT = 5

    def __init__(self, configuration, synchronizer, condition):
        super().__init__()
        self.configuration = configuration
        self.synchronizer = synchronizer
        self.condition = condition

    @Strategy.schedule
    def desync_oposite_host(self):
        logger.info("Setting state \'%s\' for every host waiting on the barrier" % self.condition)
        self.synchronizer.set_sync_condition(self.condition)
        sleep(EndSyncBarriers.SYNC_WAIT)
