import logging

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution import components

logger = logging.getLogger(__name__)


class Report(Strategy):

    def __init__(self, package):
        super().__init__()
        self.package = package

    @Strategy.schedule
    def report(self):
        logger.info('reporting results to beaker')
        # TODO: manager should return all results and attachments packed in a tgz archive and return here its path
        components.rhts.submit_log(self.package.meta.location)
        components.rhts.report_result(success=True, filename=self.package.store.location)
