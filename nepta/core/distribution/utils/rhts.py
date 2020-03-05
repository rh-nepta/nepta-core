import os
import logging

from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class Rhts(object):
    _env = os.environ
    _state = {
        True: 'PASS',
        False: 'FAIL',
    }

    @classmethod
    def is_in_rstrnt(cls):
        logger.warning('Deprecated method, do not use!!!')
        return 'TEST' in cls._env.keys()

    @classmethod
    def report_result(cls, success=True, filename='/dev/null'):
        if not cls.is_in_rstrnt():
            logger.warning('Skipping method, NOT in rstrnt environment!!!')
            return

        logger.info(f'reporting rstrnt results: {cls._state[success]} filename: {filename}')
        c = Command(f'rstrnt-report-result {cls._env["TEST"]} {cls._state[success]} -o {filename}').run()
        print(c.get_output())

    @classmethod
    def submit_log(cls, filename):
        if not cls.is_in_rstrnt():
            logger.warning('Skipping method, NOT in rstrnt environment!!!')
            return

        logger.info(f'submiting log using rstrnt: {filename}')
        c = Command(f'rstrnt-report-log --filename {filename}').run()
        print(c.get_output())

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
