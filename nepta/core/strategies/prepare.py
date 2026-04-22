import logging
from time import sleep

from nepta.core import model
from nepta.core.distribution import env
from nepta.core.distribution.utils.virt import Docker
from nepta.core.distribution.utils.system import SystemD
from nepta.core.distribution.utils.network import IpCommand, TcpDump
from nepta.core.tests.iperf3 import Iperf3Server
from nepta.core.tests.sockperf import SockPerfServer
from nepta.core.strategies.generic import Strategy
from nepta.core.scenarios.iperf3.generic import GenericIPerf3Stream
from nepta.core.scenarios.generic.scenario import ScenarioGeneric
from nepta.core.scenarios.sockperf.generic import SockPerfGeneric
from nepta.core.distribution.command import ShellCommand, Command
from nepta.core import scenarios

logger = logging.getLogger(__name__)


class Prepare(Strategy):
    IPSEC_SLEEP = 60 * 10  # 10 minutes to settle
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
        base_port = 5201

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
        logger.info("Starting necessary sockperf services")

        if 'sockperf' not in self.conf.conf_name.lower():
            logger.info("No sockperf streams found, skipping sockperf server start")
            return

        sync_objs = self.conf.get_subset(m_class=model.bundles.SyncHost)
        if not len(sync_objs):
            logger.info("There is no host for synchronization")
            return

        remote_scenarios = []
        for host in sync_objs:
            host_conf = model.bundles.HostBundle.find(host.hostname, self.conf.conf_name)

            if host_conf:
                if hasattr(host_conf, 'scenarios'):
                    remote_scenarios.extend(host_conf.scenarios)
            else:
                logger.error(f'Synchronized host {host} does not have configuration for current testcase.')

        logger.info(f"Found {len(remote_scenarios)} total scenarios on remote hosts.")

        servers_to_start = set()

        for scenario in remote_scenarios:

            logger.info(f"Scenario name is {scenario.__class__.__name__}")
            if "SockPerf" in scenario.__class__.__name__:
                for path in scenario.paths:
                    server_ip = path.their_ip.ip
                    core_string = None

                    if getattr(path, 'server_affinities', None):
                        server_cores = [str(core) for core in path.server_affinities]
                        
                        if server_cores:
                            unique_cores = list(dict.fromkeys(server_cores))
                            core_string = ",".join(unique_cores)
                            logger.info(f"Server cores (from server_affinities) are: {core_string}.")

                    else:
                        pinning_source = getattr(path, 'cpu_pinning', None)
                        if not pinning_source:
                            pinning_source = getattr(scenario, 'cpu_pinning', None)

                        if pinning_source:
                            server_cores = [str(flow[1]) for flow in pinning_source if len(flow) > 1]

                            if server_cores:
                                unique_cores = list(dict.fromkeys(server_cores))
                                core_string = ",".join(unique_cores)
                                logger.info(f"Server cores (from cpu_pinning) are: {core_string}.")

                    servers_to_start.add((server_ip, core_string))

        for ip, core in servers_to_start:
            if core:
                logger.info(f"Starting sockperf server on IP {ip} pinned to core(s) {core}")
                srv = SockPerfServer(ip=ip, daemonize=True, cpu_affinity=core)
            else:
                logger.info(f"Starting unpinned sockperf server on IP {ip}")
                srv = SockPerfServer(ip=ip, daemonize=True)

            srv.start()

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
            logger.warning(f"WA: Restarting IPsec service and sleeping for {self.IPSEC_SLEEP} seconds!!!")
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
        else:
            logger.info(f"IPsec tunnel count matches, all tunnels are up. Number of tunnels: {len(tunnels)}")

    @Strategy.schedule
    def check_ipsec_encryption(self):
        tunnels = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tunnel in tunnels:
            logger.info(f'Checking encryption for tunnel {tunnel}')
            left_ping = Command(
                f'ping -c {self.IPSEC_PING_COUNT} -i {self.IPSEC_PING_INTERVAL} -I {tunnel.right_ip.ip} {tunnel.left_ip.ip}'
            ).run()
            right_ping = Command(
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

            left_out, left_ping_result = left_ping.watch_output()
            right_out, right_ping_result = right_ping.watch_output()
            # Check ping results, exact one must succeed, others must fail
            logger.info(f'Checking ping results for tunnel {tunnel}')
            if not (bool(left_ping_result) ^ bool(right_ping_result)):
                logger.error(f'Ping test failed for tunnel {tunnel}')
                logger.error(f'Left ping return code: {left_ping_result}, output: {left_out}')
                logger.error(f'Right ping return code: {right_ping_result}, output: {right_out}')
                raise RuntimeError('Ping test failed')

    @Strategy.schedule
    def run_shell_commands(self):
        commands = self.conf.get_subset(m_class=model.system.PrepareCommand)
        for cmd in commands:
            logger.info(f'Running >> {cmd}')
            c = ShellCommand(cmd.value).run()
            c.watch_and_log_error()
