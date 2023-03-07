import logging

from nepta.core import model
from nepta.core.distribution.utils.virt import Docker
from nepta.core.distribution.utils.system import SystemD
from nepta.core.tests.iperf3 import Iperf3Server
from nepta.core.strategies.generic import Strategy
from nepta.core.scenarios.iperf3.generic import GenericIPerf3Stream
from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class Prepare(Strategy):
    def __init__(self, configuration):
        super().__init__()
        self.conf = configuration

    @Strategy.schedule
    def start_iperf3_services(self):
        logger.info('Starting necessary iPerf3 services')
        sync_objs = self.conf.get_subset(m_class=model.bundles.SyncHost)

        # if there is no host for Sync, we are not able to find out how many iPerf3 services we should start
        if not len(sync_objs):
            logger.info('There is no host for synchronization')
            return

        remote_scenarios = model.bundles.Bundle()
        for host in sync_objs:
            host_conf = model.bundles.HostBundle.find(host.hostname, self.conf.conf_name)
            if host_conf:
                remote_scenarios += host_conf.get_subset(m_class=GenericIPerf3Stream)
            else:
                logger.error(f'Synchronized host {host} does not have configuration for current testcase.')

        # spawn at least 100 iPerf3 instances due to laziness
        max_iperf3_instances = 100
        base_port = 0

        for scenario in remote_scenarios:
            base_port = scenario.base_port
            instances = [max_iperf3_instances, len(scenario.cpu_pinning)]
            for path in scenario.paths:
                if path.cpu_pinning:
                    instances.append(len(path.cpu_pinning))

            max_iperf3_instances = max(instances)

        for port in range(base_port, base_port + max_iperf3_instances):
            srv = Iperf3Server(port=port)
            srv.run()

    @Strategy.schedule
    def start_netperf_service(self):
        logger.info('Start netserver for netperf test')
        sync_objs = self.conf.get_subset(m_class=model.bundles.SyncHost)

        # if there is no host for Sync, we are not able to find out how many iPerf3 services we should start
        if not len(sync_objs):
            logger.info('There is no host for synchronization')
            return

        remote_scenarios = model.bundles.Bundle()
        for host in sync_objs:
            host_conf = model.bundles.HostBundle.find(host.hostname, self.conf.conf_name)
            if host_conf:
                remote_scenarios += host_conf.get_subset(m_class=ScenarioGeneric)
            else:
                logger.error(f'Synchronized host {host} does not have configuration for current testcase.')

        if any(map(lambda x: x.__class__.__name__.find('Netperf') > -1, remote_scenarios)):
            logger.info('Starting netserver')
            cmd = Command('netserver')
            cmd.run()
            if cmd.get_output()[1] != 0:
                logger.error('Cannot start netperf server !!!')

    @Strategy.schedule
    def start_docker_container(self):
        logger.info('Starting containers')
        containers = self.conf.get_subset(m_class=model.docker.Container)
        for cont in containers:
            Docker.run(cont)

    @Strategy.schedule
    def restart_ipsec_service(self):
        """
        This is hotfix for issue, when ipsec service stars earlier than IP addresses are assigned. This causes ipsec
        tunnels malfunctions. As a simple solution is just restart IPsec service before test.
        Ref: https://gitlab.cee.redhat.com/kernel-performance/testplans/issues/3
        """
        SystemD.restart_service(model.system.SystemService('ipsec'))

    @Strategy.schedule
    def run_shell_commands(self):
        commands = self.conf.get_subset(m_class=model.system.PrepareCommand)
        for cmd in commands:
            logger.info(f'Running >> {cmd}')
            c = Command(cmd.value).run()
            c.watch_and_log_error()
