import logging

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution.utils.rhts import Rhts

logger = logging.getLogger(__name__)


class Report(Strategy):

    def __init__(self, package):
        super().__init__()
        self.package = package

    @Strategy.schedule
    def report(self):
        logger.info('reporting results to beaker')
        # TODO: manager should return all results and attachments packed in a tgz archive and return here its path
        Rhts.submit_log(self.package.metas._xml_file.path)
        Rhts.report_result(success=True, filename=self.package.store.path)
