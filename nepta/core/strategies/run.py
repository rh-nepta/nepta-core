import logging
from typing import List

from nepta.dataformat import Section

from nepta.core.strategies.generic import Strategy
from nepta.core.scenarios.generic.scenario import ScenarioGeneric, StreamGeneric

logger = logging.getLogger(__name__)


class RunScenarios(Strategy):
    def __init__(self, conf, package, filter_scenarios=None, path_tags=None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.filter_scenarios = filter_scenarios
        self.path_tags = set(path_tags)
        self.aggregated_result = True  # result is Pass in default

    def filter_paths(self, scenarios: List[StreamGeneric]):
        """
        Cycle through all paths of each scenario and checks if path contains at least one of specifies tags. If not,
        remove path from the list.
        :param scenarios: List of running scenarios
        :return: None -> modifying scenarios directly
        """
        if self.path_tags:
            for scenario in scenarios:
                if isinstance(scenario, StreamGeneric):
                    for path in list(scenario.paths):
                        current_path_tags = set([tag.name for tag in path.sw_inventory + path.hw_inventory])
                        # if union of these sets is zero, none tag is not matched and the path is removed
                        if not self.path_tags & current_path_tags:
                            scenario.paths.remove(path)

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

        run_items = [x for x in scenarios if x.__class__.__name__ in override_names]
        self.filter_paths(run_items)
        for item in run_items:
            logger.info('\n\nRunning scenario: %s', item)
            data, result = item()
            scenarios_section.subsections.append(data)
            self.aggregated_result &= result
