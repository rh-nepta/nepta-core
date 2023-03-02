import logging

from nepta.core.strategies.generic import Strategy
from nepta.core.model.bundles import HostBundle
from nepta.core.model.system import SetupCommand
from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class _GenericSetup(Strategy):
    def __init__(self, conf: HostBundle):
        super().__init__()
        self.conf = conf

    @Strategy.schedule
    def run_shell_commands(self):
        commands = self.conf.get_subset(m_class=SetupCommand)
        for cmd in commands:
            logger.info(f'Running >> {cmd}')
            c = Command(cmd)
            c.watch_and_log_error()
