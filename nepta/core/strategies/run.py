import logging
import os
from typing import Optional

from nepta.dataformat import Section

from nepta.core.strategies.generic import Strategy
from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.model.system import PCPConfiguration
from nepta.core.distribution.command import Command
from nepta.core.model.attachments import Directory

logger = logging.getLogger(__name__)


class RunScenarios(Strategy):
    def __init__(self, conf, package, filter_scenarios=None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.filter_scenarios = filter_scenarios
        self.aggregated_result = True  # result is Pass in default
        self._pmlogger_cmd: Optional[Command] = None
        self.pcp_conf = self.init_pcp_conf()

    def init_pcp_conf(self):
        pcp_confs = self.conf.get_subset(m_type=PCPConfiguration)
        if len(pcp_confs):
            self.conf.attachments.scenarios.pcp = Directory(pcp_confs[0].log_path, 'pcp')
            return pcp_confs[0]
        else:
            return None

    def start_pmlogger(self, archive_name):
        if self.pcp_conf:
            self._pmlogger_cmd = Command(
                f'pmlogger -c {self.pcp_conf.config_path} -t {self.pcp_conf.interval} '
                f'{os.path.join(self.pcp_conf.log_path, archive_name)}'
            ).run()

    def stop_pmlogger(self):
        if self._pmlogger_cmd and self.pcp_conf:
            self._pmlogger_cmd.terminate()

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

        return [x for x in scenarios if x.__class__.__name__ in override_names]

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
