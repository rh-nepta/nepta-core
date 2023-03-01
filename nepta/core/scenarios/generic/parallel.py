import logging
import time
import uuid
import functools
from typing import Tuple, List, Union
from nepta.dataformat import Section

from nepta.core.model.schedule import ParallelPathList, PathList
from nepta.core.scenarios.generic.scenario import ScenarioGeneric

logger = logging.getLogger(__name__)


class ParallelPathGeneric(ScenarioGeneric):
    def __init__(
            self,
            paths: ParallelPathList,
            test_length: int,
            test_runs: int,
            msg_sizes: List[int],
            cpu_pinning,
            base_port: int,
            result: bool = True,
    ):
        self.paths = paths
        self.test_length = test_length
        self.test_runs = test_runs
        self.msg_sizes = msg_sizes
        self.cpu_pinning = cpu_pinning
        self.base_port = base_port
        self.result = result

    def __str__(self):
        ret_str = super().__str__()
        for k, v in self.__dict__.items():
            ret_str += '\n\t{}: {}'.format(k, v)
        return ret_str

    def run_scenario(self):
        logger.info('Running scenario: %s' % self)

        root_sec = Section('scenario')
        self.store_scenario(root_sec)

        paths_section = Section('paths')
        root_sec.subsections.append(paths_section)

        for path_list in self.paths:
            paths_section.subsections.append(self.run_paths(path_list))
        return root_sec, self.result

    def store_scenario(self, section):
        section.params['scenario_name'] = self.__class__.__name__
        section.params['uuid'] = uuid.uuid5(uuid.NAMESPACE_DNS, self.__class__.__name__)
        return section

    def run_paths(self, paths: PathList):
        logger.info('Running path: %s' % paths)
        path_sec = Section('path')
        self.store_path(path_sec, paths)

        test_cases_sec = Section('test_cases')
        path_sec.subsections.append(test_cases_sec)

        for size in self.msg_sizes:
            test_cases_sec.subsections.append(self.run_msg_size(paths, size))
        return path_sec

    def store_path(self, section, paths: PathList):
        section.params.update(paths.dict())
        hw_inv_sec = Section('hardware_inventory')
        sw_inv_sec = Section('software_inventory')

        for tag in paths.hw_inventory:
            hw_inv_sec.subsections.append(Section('tag', value=tag))

        for tag in paths.sw_inventory:
            sw_inv_sec.subsections.append(Section('tag', value=tag))

        section.subsections.append(hw_inv_sec)
        section.subsections.append(sw_inv_sec)
        return section

    def run_msg_size(self, path, size):
        test_case_section = Section('test_case')
        runs_section = Section('runs')

        self.store_msg_size(test_case_section, size)
        test_case_section.subsections.append(runs_section)
        for _ in range(self.test_runs):
            runs_section.subsections.append(self.run_instance(path, size))
        return test_case_section

    def store_msg_size(self, section, size):
        section.params['uuid'] = uuid.uuid5(uuid.NAMESPACE_DNS, 'msg_size=%s test_length=%s' % (size, self.test_length))
        test_settings_sec = Section('test_settings')
        test_settings_sec.subsections.append(Section('item', key='msg_size', value=size))
        test_settings_sec.subsections.append(Section('item', key='test_length', value=self.test_length))
        section.subsections.append(test_settings_sec)
        return section

    def run_instance(self, path, size):
        raise NotImplementedError

    def store_instance(self, section, test):
        raise NotImplementedError
