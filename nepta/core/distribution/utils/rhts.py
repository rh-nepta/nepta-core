import os
import logging

from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class Rhts(object):
    _env = os.environ

    @classmethod
    def is_in_rhts(cls):
        logger.warning('Deprecated method, do not use!!!')
        return 'TEST' in cls._env.keys()

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
    @classmethod
    def sync_set(cls, state):
        if not cls.is_in_rstrnt():
            logger.warning('Skipping method, NOT in rstrnt environment!!!')
            return

        logger.info('rstrnt synchronization: setting synchronization state: %s', state)
        c = Command('rstrnt-sync-set -s %s' % state).run()
        print(c.get_output())

    @classmethod
    def sync_block(cls, states, hosts):
        if not cls.is_in_rstrnt():
            logger.warning('Skipping method, NOT in rstrnt environment!!!')
            return

        logger.info('rstrnt synchronization: waiting for all hosts: %s to be in one of %s states', hosts, states)
        hosts_list = ' '.join(hosts)
        states_list = ' -s '.join([''] + states)
        c = Command(f'rstrnt-sync-block {states_list} {hosts_list}').run()
        print(c.get_output())
