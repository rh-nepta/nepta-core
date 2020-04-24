import logging

from nepta.core import model, scenarios
from nepta.core.distribution.utils.network import Tuna
from nepta.core.distribution.utils.virt import Docker
from nepta.core.tests.iperf3 import Iperf3Server
from nepta.core.strategies.generic import Strategy

logger = logging.getLogger(__name__)


class Prepare(Strategy):

    def __init__(self, configuration):
        super().__init__()
        self.conf = configuration

    @Strategy.schedule
    def bind_irq(self):
        interfaces = self.conf.get_subset(m_type=model.network.EthernetInterface)

        for intf in interfaces:
            cores = intf.bind_cores
            if cores is not None:
                cores = "".join([str(x) for x in cores])
                logger.info('Setting all irq of %s to %s cores' % (intf.get_name(), cores))
                Tuna.set_irq_cpu_binding(intf.get_name(), cores)

    @Strategy.schedule
    def start_iperf3_services(self):
        logger.info("Starting necessary iPerf3 services")
        sync_objs = self.conf.get_subset(m_class=model.bundles.SyncHost)

        # if there is no host for Sync, we are not able to find out how many iPerf3 services we should start
        if not len(sync_objs):
            logger.info("There is no host for synchronization")
            return

        oposite_host_hostname = sync_objs[0].hostname
        oposite_host_configuration = model.bundles.HostBundle.find(oposite_host_hostname, self.conf.conf_name)
        oposite_scenarios = oposite_host_configuration.get_subset(m_class=scenarios.iperf3.stream.GenericIPerf3Stream)

        max_iperf3_instances = 0
        base_port = 0

        for scenario in oposite_scenarios:
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
    def start_docker_container(self):
        logger.info("Starting containers")
        containers = self.conf.get_subset(m_class=model.docker.Containter)
        for cont in containers:
            Docker.run(cont)
