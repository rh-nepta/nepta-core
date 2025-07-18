import logging
from time import sleep

from nepta.core import model
from nepta.core.distribution import env
from nepta.core.distribution.utils.virt import Docker
from nepta.core.distribution.utils.system import SystemD
from nepta.core.distribution.utils.network import IpCommand, TcpDump
from nepta.core.tests.iperf3 import Iperf3Server
from nepta.core.strategies.generic import Strategy
from nepta.core.scenarios.iperf3.generic import GenericIPerf3Stream
from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.distribution.command import ShellCommand, Command

logger = logging.getLogger(__name__)


class Prepare(Strategy):
    IPSEC_SLEEP = 60
    IPSEC_PING_INTERVAL = 0.1
    IPSEC_PING_COUNT = 50

    def __init__(self, configuration):
        super().__init__()
        self.conf = configuration

    @Strategy.schedule
    def start_iperf3_services(self):
        logger.info("Starting necessary iPerf3 services")
        sync_objs = self.conf.get_subset(m_class=model.bundles.SyncHost)

        # if there is no host for Sync, we are not able to find out how many iPerf3 services we should start
        if not len(sync_objs):
            logger.info("There is no host for synchronization")
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
            instances = [max_iperf3_instances, scenario.num_instances]
            for path in scenario.paths:
                if path.cpu_pinning:
                    instances.append(len(path.cpu_pinning))

            max_iperf3_instances = max(instances)

        for port in range(base_port, base_port + max_iperf3_instances):
            srv = Iperf3Server(port=port)
            srv.run()

    @Strategy.schedule
    def start_netperf_service(self):
        logger.info("Start netserver for netperf test")
        sync_objs = self.conf.get_subset(m_class=model.bundles.SyncHost)

        # if there is no host for Sync, we are not able to find out how many iPerf3 services we should start
        if not len(sync_objs):
            logger.info("There is no host for synchronization")
            return

        remote_scenarios = model.bundles.Bundle()
        for host in sync_objs:
            host_conf = model.bundles.HostBundle.find(host.hostname, self.conf.conf_name)
            if host_conf:
                remote_scenarios += host_conf.get_subset(m_class=ScenarioGeneric)
            else:
                logger.error(f'Synchronized host {host} does not have configuration for current testcase.')

        if any(map(lambda x: x.__class__.__name__.find("Netperf") > -1, remote_scenarios)):
            logger.info("Starting netserver")
            cmd = Command("netserver")
            cmd.run()
            if cmd.get_output()[1] != 0:
                logger.error("Cannot start netperf server !!!")

    @Strategy.schedule
    def start_sockperf_service(self):
        # TODO: implement this method
        raise NotImplementedError('start_sockperf_service is not implemented yet')

    @Strategy.schedule
    def start_docker_container(self):
        logger.info("Starting containers")
        containers = self.conf.get_subset(m_class=model.docker.Container)
        for cont in containers:
            Docker.run(cont)

    @Strategy.schedule
    def restart_ipsec_service(self):
        """
        This is hotfix for issue, when ipsec service stars earlier than IP addresses are assigned. This causes ipsec
        tunnels malfunctions. As a simple solution is just restart IPsec service before test.
        Ref:
          - https://gitlab.cee.redhat.com/kernel-performance/testplans/issues/3
          - https://issues.redhat.com/browse/RHEL-30796
        """
        if (not env.RedhatRelease.version.startswith("8")) and str(self.conf.conf_name).startswith("IPsec"):
            logger.warning("WA: Restarting IPsec service and sleeping for 60 seconds!!!")
            sleep(self.IPSEC_SLEEP)
            SystemD.restart_service(model.system.SystemService("ipsec"))
            sleep(self.IPSEC_SLEEP)
        else:
            logger.warning("IPsec WA is not applied!")

    @Strategy.schedule
    def check_ipsec_tunnels(self):
        tunnels = self.conf.get_subset(m_class=model.network.IPsecTunnel)

        # each tunnel has two entries, for each direction
        if len(tunnels) * 2 != IpCommand.Xfrm.number_of_tunnel():
            logger.error(
                f'IPsec tunnel count mismatch: {len(tunnels) * 2} tunnels expected, {IpCommand.Xfrm.number_of_tunnel()} found.'
            )
            raise RuntimeError("IPsec tunnel count mismatch")

    @Strategy.schedule
    def check_ipsec_encryption(self):
        tunnels = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tunnel in tunnels:
            logger.info(f'Checking encryption for tunnel {tunnel}')
            Command(
                f'ping -c {self.IPSEC_PING_COUNT} -i {self.IPSEC_PING_INTERVAL} -I {tunnel.right_ip.ip} {tunnel.left_ip.ip}'
            ).run()
            Command(
                f'ping -c {self.IPSEC_PING_COUNT} -i {self.IPSEC_PING_INTERVAL} -I {tunnel.left_ip.ip} {tunnel.right_ip.ip}'
            ).run()

            interface = IpCommand.Route.get_outgoing_interface(tunnel.right_ip.ip)
            if interface == "lo":
                interface = IpCommand.Route.get_outgoing_interface(tunnel.left_ip.ip)

            logger.info(f'Checking interface {interface} for ESP packets.')
            if (
                TcpDump.count(
                    "esp or udp port 4500",
                    timeout=int(self.IPSEC_PING_COUNT * self.IPSEC_PING_INTERVAL),
                    interface=interface,
                )
                == 0
            ):
                logger.error(f'No ESP packets found for tunnel {tunnel}')
                raise RuntimeError("No ESP packets found")

    @Strategy.schedule
    def run_shell_commands(self):
        commands = self.conf.get_subset(m_class=model.system.PrepareCommand)
        for cmd in commands:
            logger.info(f'Running >> {cmd}')
            c = ShellCommand(cmd.value).run()
            c.watch_and_log_error()
