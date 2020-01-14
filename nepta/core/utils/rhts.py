import os
import logging

from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class Rhts(object):
    _env = os.environ
    whiteboard = _env['BEAKER_JOB_WHITEBOARD']
    job_id = _env['JOBID']
    arch = _env['ARCH']
    in_rhts = 'TEST' in _env.keys()

    @classmethod
    def is_in_rhts(cls):
        return cls.in_rhts

    def get_distro(self):
        if 'DISTRO' in self._env:
            return self._env['DISTRO']

    @classmethod
    def report_result(cls, success=True, filename='/dev/null'):
        if not cls.is_in_rhts():
            return
        logger.info('reporting rhts results: %s filename: %s', success, filename)

        if success:
            result_string = 'PASS'
        else:
            result_string = 'FAILS'

        c = Command('rhts-report-result %s %s %s' % (cls._env['TEST'], result_string, filename)).run()
        c.get_output()

        if 'RECIPETESTID' in cls._env.keys() and 'RESULT_SERVER' in cls._env.keys():
            # FIXME: call self.submit_log here
            # FIXME: -T and -S are deprecated when using restraint harness!
            c2 = Command(
                'rhts-submit-log -T %s -S %s -l %s' % (cls._env['RECIPETESTID'], cls._env['RESULT_SERVER'], filename))
            c2.run()
            c2.get_output()

    @classmethod
    def submit_log(cls, filename):
        if not cls.is_in_rhts():
            return

        logger.info('submiting log using rhts: %s', filename)

        c = Command('rhts-submit-log -l %s' % filename).run()
        c.watch_output()

    @staticmethod
    def sync_set(state):
        logger.info('rhts synchronization: setting synchronization state: %s', state)
        c = Command('rhts-sync-set -s %s' % state)
        c.run()
        c.watch_output()

    @staticmethod
    def sync_block(states, hosts):
        logger.info('rhts synchronization: waiting for all hosts: %s to be in one of %s states', hosts, states)
        hosts_list = ' '.join(hosts)
        states_list = ' -s '.join([''] + states)
        c = Command('rhts-sync-block %s %s' % (states_list, hosts_list))
        c.run()
        c.watch_output()
