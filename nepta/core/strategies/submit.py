import logging

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution.components import Command
from nepta.core.model.schedule import RsyncHost

logger = logging.getLogger(__name__)


class Submit(Strategy):
    _RSYNC_TEMPLATE = jinja2.Template("""rsync -avz --no-owner --no-group --recursive --chmod=a+r,a+w,a+X {{ path }} \
{{ rsync.server }}::{{ rsync.destination }}""")

    def __init__(self, configuration, package):
        super().__init__()
        self.configuration = configuration
        self.package = package

    @Strategy.schedule
    def submit(self):
        logger.info('Starting rsync results')
        for rsync in self.configuration.get_subset(m_class=RsyncHost):
            logger.info('rsyncing results to %s', ":".join([rsync.server, rsync.destination]))
            c = Command(self._RSYNC_TEMPLATE.render(path=self.package.path, rsync=rsync))
            c.run()
            out, ret = c.watch_output()
            if not ret:
                logger.info("Rsync successful")
            else:
                logger.error("Rsync failed")
                logger.error(out)
