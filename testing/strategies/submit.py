import logging

from testing.strategies.generic import Strategy
from testing.distribution import components
from testing.model.schedule import RsyncHost

logger = logging.getLogger(__name__)


class Submit(Strategy):

    def __init__(self, configuration, package):
        super().__init__()
        self.configuration = configuration
        self.package = package

    @Strategy.schedule
    def submit(self):
        logger.info('Starting rsync results')
        for rsync in self.configuration.get_subset(m_class=RsyncHost):
            logger.info('rsyncing results to %s', ":".join([rsync.server, rsync.destination]))
            results_path = str(self.package.save.location)
            cmd = 'rsync -avz --no-owner --no-group --recursive --chmod=a+r,a+w,a+X %s %s::%s' \
                  % (results_path, rsync.server, rsync.destination)
            c = components.Command(cmd)
            c.run()
            out, ret = c.watch_output()
            if not ret:
                logger.info("Rsync successful")
            else:
                logger.error("Rsync failed")
                logger.error(out)
