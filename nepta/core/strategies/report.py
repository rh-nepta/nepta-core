import logging

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution.utils.rstrnt import Rstrnt

logger = logging.getLogger(__name__)


class Report(Strategy):

    def __init__(self, package, success):
        super().__init__()
        self.package = package
        self.success = success

    @Strategy.schedule
    def report(self):
        logger.info('reporting results to beaker')
        Rstrnt.submit_log(self.package.metas._xml_file.path)
        Rstrnt.report_result(success=self.success, filename=self.package.store.path)
