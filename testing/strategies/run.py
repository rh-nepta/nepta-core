import logging

from libres.store import Section

from testing.strategies.generic import Strategy
from testing.scenarios.generic.scenario import StreamGeneric

logger = logging.getLogger(__name__)


class RunScenarios(Strategy):

    def __init__(self, conf, package, filter_scenarios=None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.filter_scenarios = filter_scenarios

    @Strategy.schedule
    def run_scenarios(self):
        scenarios = self.conf.get_subset(m_class=StreamGeneric)
        scenario_names = [item.__class__.__name__ for item in scenarios]
        override_names = self.filter_scenarios if self.filter_scenarios is not None else scenario_names
        # these sets are informational only
        run_names = set(scenario_names) & set(override_names)
        unmatched_names = set(override_names) - set(run_names)
        excluded_names = set(scenario_names) - set(run_names)

        logger.info('\n\nWe will run following scenarios: %s\n', run_names)
        if len(unmatched_names) > 0:
            logger.warning('Scenarios %s are not defined in configuration. They won\'t be run.' % unmatched_names)
        if len(excluded_names) > 0:
            logger.warning('Scenarios %s are disabled by commandline options. They won\'t be run.' % excluded_names)

        # creating data section and running filtered scenarios
        root_section = self.package.store.root_section
        scenarios_section = root_section.add_sub_section(Section('scenarios'))

        run_items = [x for x in scenarios if x.__class__.__name__ in override_names]
        for item in run_items:
            logger.info('\n\nRunning scenario: %s', item)
            result = item()
            if result:
                scenarios_section.add_sub_section(result)
