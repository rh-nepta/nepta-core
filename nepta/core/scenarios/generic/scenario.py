import logging
import time
import uuid
import functools
from typing import Tuple, List, Union
from nepta.dataformat import Section

from nepta.core.model.schedule import PathList, Path

logger = logging.getLogger(__name__)


def info_log_func_output(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        output = f(*args, **kwargs)
        logger.info(f'function output >>> {output}')
        return output

    return wrapper


class ScenarioGeneric:
    def __str__(self):
        return self.__class__.__name__

    def __call__(self) -> Section:
        return self.run_scenario()

    def run_scenario(self) -> Tuple[Section, bool]:
        raise NotImplementedError


class StreamGeneric(ScenarioGeneric):
    def __init__(
        self,
        paths: Union[List[Path], PathList],
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

        for path in self.paths:
            paths_section.subsections.append(self.run_path(path))
        return root_sec, self.result

    def store_scenario(self, section):
        section.params['scenario_name'] = self.__class__.__name__
        section.params['uuid'] = uuid.uuid5(uuid.NAMESPACE_DNS, self.__class__.__name__)
        return section

    def run_path(self, path):
        logger.info('Running path: %s' % path)
        path_sec = Section('path')
        self.store_path(path_sec, path)

        test_cases_sec = Section('test_cases')
        path_sec.subsections.append(test_cases_sec)

        for size in self.msg_sizes:
            test_cases_sec.subsections.append(self.run_msg_size(path, size))
        return path_sec

    def store_path(self, section, path):
        section.params.update(path.dict())
        hw_inv_sec = Section('hardware_inventory')
        sw_inv_sec = Section('software_inventory')

        for tag in path.hw_inventory:
            hw_inv_sec.subsections.append(Section('tag', value=tag))

        for tag in path.sw_inventory:
            sw_inv_sec.subsections.append(Section('tag', value=tag))

        section.subsections.append(hw_inv_sec)
        section.subsections.append(sw_inv_sec)
        return section

    def run_msg_size(self, path, size):
        test_case_section = Section('test_case')
        runs_section = Section('runs')

        cpu = path.cpu_pinning if path.cpu_pinning else self.cpu_pinning
        self.store_msg_size(test_case_section, size, cpu)
        test_case_section.subsections.append(runs_section)
        for _ in range(self.test_runs):
            runs_section.subsections.append(self.run_instance(path, size))
        return test_case_section

    def store_msg_size(self, section, size, cpu_pinning=None):
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


class SingleStreamGeneric(StreamGeneric):
    def init_test(self, path, size):
        raise NotImplementedError

    def parse_results(self, test):
        raise NotImplementedError

    def store_msg_size(self, section, size, cpu_pinning=None):
        super().store_msg_size(section, size)
        if cpu_pinning:
            test_settings_sec = section.subsections.filter('test_settings')[0]
            test_settings_sec.subsections.append(Section('item', key='local_cpu_bind', value=cpu_pinning[0][0]))
            test_settings_sec.subsections.append(Section('item', key='remote_cpu_bind', value=cpu_pinning[0][1]))

        return section

    def run_instance(self, path, size):
        test = self.init_test(path, size)
        test.run()
        test.watch_output()
        if test.success():
            return self.store_instance(Section('run'), test)
        else:
            logger.error('Measurement fails. Returning results with zeros.')
            self.result = False
            return Section('failed-test')

    def store_instance(self, section, test):
        for k, v in self.parse_results(test).items():
            section.subsections.append(Section('item', key=k, value=v))
        return section


class MultiStreamsGeneric(StreamGeneric):
    def __init__(
        self,
        paths,
        attempt_count,
        attempt_pause,
        test_length,
        test_runs,
        msg_sizes,
        cpu_pinning,
        base_port,
        result=True,
    ):
        super().__init__(paths, test_length, test_runs, msg_sizes, cpu_pinning, base_port, result)
        self.attempt_count = attempt_count
        self.attempt_pause = attempt_pause

    def init_all_tests(self, path, size):
        raise NotImplementedError

    @info_log_func_output
    def parse_all_results(self, tests):
        raise NotImplementedError

    def store_msg_size(self, section, size, cpu_pinning=None):
        super().store_msg_size(section, size)
        if cpu_pinning:
            test_settings_sec = section.subsections.filter('test_settings')[0]
            test_settings_sec.subsections.append(Section('item', key='instances', value=len(cpu_pinning)))
        return section

    def run_instance(self, path, size):
        tests = self.init_all_tests(path, size)

        for _ in range(self.attempt_count):
            success = True
            for test in tests:
                test.run()

            for test in tests:
                test.watch_output()

            for test in tests:
                success &= test.success()

            if success:
                break

            logger.info('Measurements was unsuccessful. Trying again...')
            for test in tests:
                test.clear()
            time.sleep(self.attempt_pause)

        else:  # if every attempt fails
            logger.error('Each measurement fails. Returning results with zeros.')
            self.result = False
            return Section('failed-test')

        return self.store_instance(Section('run'), tests)

    def store_instance(self, section, tests):
        for k, v in self.parse_all_results(tests).items():
            section.subsections.append(Section('item', key=k, value=v))
        return section


class DuplexStreamGeneric(MultiStreamsGeneric):
    def store_msg_size(self, section, size, cpu_pinning=None):
        super().store_msg_size(section, size)
        if cpu_pinning:
            test_settings_sec = section.subsections.filter('test_settings')[0]
            test_settings_sec.subsections.append(Section('item', key='bind_stream', value=cpu_pinning[0][0]))
            test_settings_sec.subsections.append(Section('item', key='bind_reversed', value=cpu_pinning[0][1]))
        return section
