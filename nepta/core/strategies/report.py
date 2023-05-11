import logging
from typing import Optional

from nepta.core.strategies.generic import Strategy, CompoundStrategy
from nepta.core.strategies.run import RunScenarios
from nepta.core.distribution.utils.rstrnt import Rstrnt

logger = logging.getLogger(__name__)


class Report(Strategy):
    def __init__(self, package, all_strategies: Optional[CompoundStrategy] = None, result: bool = True):
        super().__init__()
        self.package = package
        self.all_strategies = all_strategies
        self.result = result

    @Strategy.schedule
    def report(self):
        if self.all_strategies:
            for strategy in self.all_strategies.strategies:
                if isinstance(strategy, RunScenarios):
                    self.result &= strategy.aggregated_result
        logger.info('reporting results to beaker')
        Rstrnt.submit_log(self.package.metas._xml_file.path)
        Rstrnt.submit_log(self.package.store.path)
        Rstrnt.report_result(success=self.result)


class Abort(Strategy):
    @Strategy.schedule
    def abort(self):
        Rstrnt.abort()
