import logging
import time
import os
from testing import distribution

logger = logging.getLogger(__name__)


class Synchronization(object):
    
    def set_sync_condition(self, condition):
        raise NotImplementedError

    def sync_for_condition(self, hosts, condition):
        raise NotImplementedError

    def barier(self, hosts, condition):
        raise NotImplementedError


class NoSynchronization(Synchronization):
    def __init__(self):
        logger.info('Synchronization is not enabled')

    def set_sync_condition(self, condition):
        pass

    def sync_for_condition(self, hosts, condition):
        pass

    def barier(self, hosts, condition):
        pass


class BeakerSynchronization(Synchronization):
    
    def __init__(self):
        logger.info('Beaker synchronization enabled')
        self._rhts_component = distribution.components.rhts

    def set_sync_condition(self, condition):
        logger.info('setting my sychronization condition to %s' % condition)
        self._rhts_component.sync_set(condition)

    def sync_for_condition(self, hosts, condition):
        self._rhts_component.sync_block(condition, hosts)

    def barier(self, hosts, condition):
        self.set_sync_condition(condition)
        self.sync_for_condition(hosts, condition=[condition])


class PerfSynchronization(Synchronization):
    
    def __init__(self, sync_server, poll_inerval=1):
        import synchronization
        self._sync_server = sync_server
        self._poll_interval = poll_inerval
        self._client = synchronization.client.SyncClient(self._sync_server)
        if 'JOBID' not in os.environ:
            raise ValueError('JOBID environment variable must be specified when using PerfSynchonization')
        self._jobid = os.environ['JOBID']
        logger.info('PerfSync synchronization enabled, sync server is %s', sync_server)

    def set_sync_condition(self, condition):
        logger.info('setting my synchronization condition to %s' % condition)
        self._client.set_state(self._jobid, condition)

    def sync_for_condition(self, hosts, condition):
        logger.info('waiting for hosts %s to be in condition %s' % (hosts, condition))
        for host in hosts:
            self._client.wait_for_state(host, self._jobid, condition, poll=self._poll_interval)

    def barier(self, hosts, condition):
        self.set_sync_condition(condition)
        self.sync_for_condition(hosts, condition=[condition])
        time.sleep((len(hosts) + 2) * self._poll_interval)
