import statistics
import time
import uuid
import logging
import json
from typing import Tuple, List, Optional, Dict, Any
from nepta.core.scenarios.generic.scenario import info_log_func_output
from nepta.core.scenarios.iperf3.generic import GenericIPerf3Stream, catch_and_log_exception

from nepta.dataformat.section import Section

from nepta.core.distribution.utils.tuna import Tuna
from nepta.core.model.schedule import UBenchPath
from nepta.core.scenarios import ScenarioGeneric
from nepta.core.tests import Iperf3Test, MPStat, RemoteMPStat

logger = logging.getLogger(__name__)


class UBenchGeneric(GenericIPerf3Stream, ScenarioGeneric):
    def __init__(
        self,
        paths: List[UBenchPath],
        base_port: int,
        interval: Optional[int],
        parallel: int = 8,
        test_length: int = 30,
        test_runs: int = 10,
        message_size: Optional[str] = None,
    ):
        self.paths = paths
        self.base_port = base_port
        self.parallel = parallel
        self.interval = interval
        self.test_length = test_length
        self.test_runs = test_runs
        self.message_size = message_size

        self.retries = 3  # FIXME: this should be parameter
        self.retry_pause = 5  # FIXME: this should be parameter

        self.throughputs: List[float] = []
        self.local_cpu_utils: List[float] = []
        self.remote_cpu_utils: List[float] = []
        self.summary: Dict[str, Dict] = {}

    def __str__(self):
        ret_str = super().__str__()
        for k, v in self.__dict__.items():
            ret_str += "\n\t{}: {}".format(k, v)
        return ret_str

    def run_scenario(self) -> Tuple[Section, bool]:
        logger.info("Running UBench scenario: %s" % self)

        root_section = Section("scenario")
        self.store_scenario(root_section)

        paths_section = Section("paths")
        root_section.subsections.append(paths_section)

        for path in self.paths:
            paths_section.subsections.append(self.run_path(path))

        logger.info(f'Summary {self}')
        for tags, instances in self.summary.items():
            logger.info(tags)
            logger.info("Instances\tThroughput\t\tLocal util\t\tRemote util")
            for k, v in instances.items():
                logger.info(
                    f'{k} instance\tmean {v[0]}\tstdev {v[1]}\tmean {v[2]}\tstdev {v[3]}\tmean {v[4]}\tstdev {v[5]}'
                )

        return root_section, True

    def store_scenario(self, section: Section):
        section.params["scenario_name"] = self.__class__.__name__
        section.params["uuid"] = uuid.uuid5(uuid.NAMESPACE_DNS, self.__class__.__name__)
        return section

    def store_path(self, section: Section, path):
        section.params.update(path.dict())
        hw_inv_sec = Section("hardware_inventory")
        sw_inv_sec = Section("software_inventory")

        for tag in path.hw_inventory:
            hw_inv_sec.subsections.append(Section("tag", value=tag))

        for tag in path.sw_inventory:
            sw_inv_sec.subsections.append(Section("tag", value=tag))

        section.subsections.append(hw_inv_sec)
        section.subsections.append(sw_inv_sec)
        return section

    def run_path(self, path: UBenchPath):
        logger.info("Running UBenchPath: %s" % path)

        path_section = Section("path")
        self.store_path(path_section, path)

        test_cases_section = Section("test_cases")
        path_section.subsections.append(test_cases_section)

        self.summary[str(path.tags)] = {}

        for cpu_pinning, irq_settings in zip(path.cpu_pinning, path.irq_settings):
            test_cases_section.subsections.append(self.run_streams(path, cpu_pinning, irq_settings))

        return path_section

    def run_streams(self, path: UBenchPath, cpu_pinning, irq_settings):
        test_case_section = Section("test_case")
        runs_section = Section("runs")

        self.store_stream(test_case_section, cpu_pinning)
        test_case_section.subsections.append(runs_section)

        tuna = Tuna()
        tuna.set_irq_spread_over_cpu_list(irq_settings[0], irq_settings[1])
        tuna.set_irq_spread_over_cpu_list(irq_settings[0], irq_settings[1], host=path.their_ip.ip)

        self.throughputs = []
        self.local_cpu_utils = []
        self.remote_cpu_utils = []

        for _ in range(self.test_runs):
            runs_section.subsections.append(self.run_instance(path, cpu_pinning))

        throughput_mean = statistics.mean(self.throughputs)
        throughput_std = round(statistics.stdev(self.throughputs))

        local_cpu_mean = round(statistics.mean(self.local_cpu_utils), 3)
        local_cpu_std = round(statistics.stdev(self.local_cpu_utils), 3)

        remote_cpu_mean = round(statistics.mean(self.remote_cpu_utils), 3)
        remote_cpu_std = round(statistics.stdev(self.remote_cpu_utils), 3)

        self.summary[str(path.tags)][len(cpu_pinning)] = (
            throughput_mean,
            throughput_std,
            local_cpu_mean,
            local_cpu_std,
            remote_cpu_mean,
            remote_cpu_std,
        )

        return test_case_section

    def store_stream(self, section, cpu_pinning):
        section.params["uuid"] = uuid.uuid5(
            uuid.NAMESPACE_DNS, "affinity=%s test_length=%s" % (cpu_pinning, self.test_length)
        )
        test_settings_sec = Section("test_settings")
        test_settings_sec.subsections.append(Section("item", key="affinity", value=cpu_pinning))
        test_settings_sec.subsections.append(Section("item", key="streams", value=len(cpu_pinning)))
        test_settings_sec.subsections.append(Section("item", key="test_length", value=self.test_length))
        section.subsections.append(test_settings_sec)
        return section

    def run_instance(self, path, cpu_pinning):
        tests = self.init_all_tests(path, cpu_pinning)

        for _ in range(self.retries):
            success = True
            for test in tests:
                test.run()

            for test in tests:
                test.watch_output()

            for test in tests:
                success &= test.success()

            if success:
                break

            logger.info("Measurements were unsuccessful. Trying again...")
            for test in tests:
                test.clear()
            time.sleep(self.retry_pause)

        else:  # if every attempt fails
            logger.error("All measurements failed. Returning results with zeros.")
            self.result = False
            return Section("failed-test")

        return self.store_instance(Section("run"), tests)

    def store_instance(self, section, tests):
        for k, v in self.parse_all_results(tests).items():
            if k == "throughput":
                self.throughputs.append(float(v))
            elif k == "local_cpu":
                self.local_cpu_utils.append(float(v))
            elif k == "remote_cpu":
                self.remote_cpu_utils.append(float(v))
            section.subsections.append(Section("item", key=k, value=v))
        return section

    def init_all_tests(self, path, cpu_pinning):
        tests = list()

        for port, affinity in zip(range(self.base_port, self.base_port + len(cpu_pinning)), cpu_pinning):
            test = Iperf3Test(
                client=path.their_ip.ip,
                bind=path.mine_ip.ip,
                time=self.test_length,
                port=port,
                interval=self.interval,
                parallel=self.parallel,
            )
            if self.message_size:
                test.len = self.message_size
            if affinity:
                test.affinity = ",".join([str(x) for x in affinity])
            tests.append(test)
        tests.append(MPStat(interval=self.test_length, count=1, cpu_list="ALL"))

        tests.append(RemoteMPStat(host=path.their_ip.ip, interval=self.test_length, count=1, cpu_list="ALL"))

        return tests

    @info_log_func_output
    @catch_and_log_exception
    def parse_all_results(self, tests):
        mpstat_tests = tests[-2:]
        tests = tests[:-2]
        total = sum([test.get_result() for test in tests])

        total.add_mpstat_sum(*mpstat_tests)
        total.set_data_formatter(self.str_round)

        local_cpu_loads = self.cpu_loads(mpstat_tests[0])
        total_local_cpu_loads = self.total_cpu_load(local_cpu_loads[1:])

        remote_cpu_loads = self.cpu_loads(mpstat_tests[1])
        total_remote_cpu_loads = self.total_cpu_load(remote_cpu_loads[1:])

        result = {key: value for key, value in total}

        result["local_efficiency"] = str(float(result["throughput"]) / (total_local_cpu_loads / 100))
        result["remote_efficiency"] = str(float(result["throughput"]) / (total_remote_cpu_loads / 100))

        # pretty print cpu stats
        logger.info(f'Local mpstat:\n{json.dumps(local_cpu_loads, indent=2)}')
        logger.info(f'Remote mpstat:\n{json.dumps(remote_cpu_loads, indent=2)}')

        return result

    def cpu_loads(self, mpstat_test):
        data = mpstat_test.parse_json()
        cpu_loads = data["sysstat"]["hosts"][0]["statistics"][-1][
            "cpu-load"
        ]  # always use the last one, might be first in some cases ;)
        return cpu_loads

    def total_cpu_load(self, cpu_loads):
        # mpstat with all statistics used to calculate efficiency
        total_load = 0
        for load in cpu_loads:
            total_load += 100 - load["idle"]
        return total_load


class UBenchBest(UBenchGeneric):
    pass


class UBenchNeighbour(UBenchGeneric):
    pass


class UBenchUnpinned(UBenchGeneric):
    pass
