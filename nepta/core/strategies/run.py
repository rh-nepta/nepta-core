import logging
import os
from typing import Optional, List

from nepta.dataformat import Section, Compression

from nepta.core.strategies.generic import Strategy
from nepta.core.model.system import PCPConfiguration
from nepta.core.distribution.command import Command
from nepta.core.model.attachments import Directory
from nepta.core.scenarios.generic.scenario import ScenarioGeneric, StreamGeneric

logger = logging.getLogger(__name__)


class RunScenarios(Strategy):
    def __init__(self, conf, package, filter_scenarios=None, path_tags=None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.filter_scenarios = filter_scenarios
        self.path_tags = set(path_tags) if path_tags else set()
        self.aggregated_result = True  # result is Pass in default

    def filter_paths(self, scenarios: List[StreamGeneric]):
        """
        Cycle through all paths of each scenario and checks if path contains at least one of specifies tags. If not,
        remove path from the list.
        Warning: Modifying input list directly!
        :param scenarios: List of running scenarios
        :return:  modified list of scenarios
        """
        if self.path_tags:
            for scenario in scenarios:
                if isinstance(scenario, StreamGeneric):
                    for path in list(scenario.paths):
                        current_path_tags = set([tag.name for tag in path.sw_inventory + path.hw_inventory])
                        # if union of these sets is zero, none tag is not matched and the path is removed
                        if not self.path_tags & current_path_tags:
                            scenario.paths.remove(path)
        return scenarios

    def get_running_scenarios(self):
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

        return self.filter_paths([x for x in scenarios if x.__class__.__name__ in override_names])

    @Strategy.schedule
    def run_scenarios(self):
        # creating data section and running filtered scenarios
        scenarios_section = Section('scenarios')
        self.package.store.root.subsections.append(scenarios_section)

        for item in self.get_running_scenarios():
            logger.info('\n\nRunning scenario: %s', item)
            data, result = item()
            scenarios_section.subsections.append(data)
            self.aggregated_result &= result


class RunScenariosPCP(RunScenarios):
    def __init__(self, conf, package, filter_scenarios=None, path_tags=None):
        super().__init__(conf, package, filter_scenarios, path_tags)
        self._pmlogger_cmd: Optional[Command] = None
        self.pcp_conf = self.init_pcp_conf()

    def init_pcp_conf(self):
        pcp_confs = self.conf.get_subset(m_type=PCPConfiguration)
        if len(pcp_confs):
            self.conf.attachments.scenarios.pcp = Directory(pcp_confs[0].log_path, 'pcp', compression=Compression.XZ)
            return pcp_confs[0]
        else:
            logger.error('PCP configuration is missing!!! Cannot continue in testing. Please define PCPConfiguration!')
            raise ValueError('PCP config is missing!')

    def start_pmlogger(self, archive_name):
        self._pmlogger_cmd = Command(
            f'pmlogger -c {self.pcp_conf.config_path} -t {self.pcp_conf.interval} '
            f'{os.path.join(self.pcp_conf.log_path, archive_name)}'
        ).run()

    def stop_pmlogger(self):
        if self._pmlogger_cmd:
            self._pmlogger_cmd.terminate()

    @Strategy.schedule
    def run_scenarios(self):
        # creating data section and running filtered scenarios
        scenarios_section = Section('scenarios')
        self.package.store.root.subsections.append(scenarios_section)

        for item in self.get_running_scenarios():
            logger.info('\n\nRunning scenario: %s', item)
            logger.info('Running pmlogger')
            self.start_pmlogger(item.__class__.__name__)
            data, result = item()
            self.stop_pmlogger()
            scenarios_section.subsections.append(data)
            self.aggregated_result &= result
