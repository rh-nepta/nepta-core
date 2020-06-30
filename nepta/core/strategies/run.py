import logging

from nepta.dataformat import Section

from nepta.core.strategies.generic import Strategy
from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.model.system import PCPConfiguration
from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class RunScenarios(Strategy):
    def __init__(self, conf, package, filter_scenarios=None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.filter_scenarios = filter_scenarios
        self.aggregated_result = True  # result is Pass in default

    @Strategy.schedule
    def run_scenarios(self):
        scenarios = self.conf.get_subset(m_class=ScenarioGeneric)
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
        scenarios_section = Section('scenarios')
        self.package.store.root.subsections.append(scenarios_section)
        
        pcp_confs = self.conf.get_subset(m_type=PCPConfiguration)
        if len(pcp_confs):
            pcp_conf = pcp_confs[0]
        else:
            logger.error('PCP configuration is missing, using default values!!!')
            pcp_conf = PCPConfiguration()

        run_items = [x for x in scenarios if x.__class__.__name__ in override_names]
        for item in run_items:
            logger.info('\n\nRunning scenario: %s', item)
            logger.info('Running pmlogger')
            pmlogger = Command(f'pmlogger -c {pcp_conf.config_path} -t {pcp_conf.interval} /root/{item.__class__.__name__}').run()
            data, result = item()
            pmlogger.terminate()  # stop pmlogger
            scenarios_section.subsections.append(data)
            self.aggregated_result &= result
