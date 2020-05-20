from ipaddress import IPv4Interface
from nepta.core import scenarios
from nepta.core.model import bundles, tag
from nepta.core.model.network import IPv4Configuration, EthernetInterface
from nepta.core.model.schedule import Path as P

from example_config.defaults import net4, net6, dns, gw
from example_config.host_settings import host_settings

host_1 = bundles.HostBundle('host_1.testlab.org', 'Default')
host_1.default_settings.host = host_settings.clone()

host_2 = bundles.HostBundle('host_2.testlab.org', 'Default')
host_2.default_settings.host = host_settings.clone()

# Create sync configuration via SyncHost
host_1.sync_host = bundles.SyncHost(host_2.get_hostname())
host_2.sync_host = bundles.SyncHost(host_1.get_hostname())

# Create interfaces configuration for first host
# statically assign IP addresses to non test interface
host_1.interfaces.eth.eth_0 = EthernetInterface(
    'eth_0',
    '1F:5A:22:2B:21:80',
    IPv4Configuration([IPv4Interface('172.16.0.1/24'), IPv4Interface('172.16.0.2/24')], gw, dns),
)

# assign test IP address from network configuration generator
host_1.interfaces.eth.eth_1 = EthernetInterface('eth_1', 'A2:A0:8B:4B:B5:C7', net4.new_config(), net6.new_config())

# Create interfaces configuration for second host
# statically assign IP addresses to non test interface
host_2.interfaces.eth.eth_0 = EthernetInterface(
    'eth_0',
    '1F:5A:22:2B:21:81',
    IPv4Configuration([IPv4Interface('172.16.0.11/24'), IPv4Interface('172.16.0.12/24')], gw, dns),
)

# assign test IP address from network configuration generator
host_2.interfaces.eth.eth_1 = EthernetInterface('eth_1', 'A2:A0:8B:4B:B5:C8', net4.new_config(), net6.new_config())

paths = [
    P(
        host_1.interfaces.eth.eth_1.v4_conf[0],
        host_2.interfaces.eth.eth_1.v4_conf[0],
        [tag.SoftwareInventoryTag('IPv4')],
    ),
    P(
        host_1.interfaces.eth.eth_1.v6_conf[0],
        host_2.interfaces.eth.eth_1.v6_conf[0],
        [tag.SoftwareInventoryTag('IPv6')],
    ),
]

# for detailed description of constructor arguments see definition of constructor
host_1.scenarios += scenarios.Iperf3TCPSanity(paths, 5, 2, [1024, 8192, 65536], (0, 0), 5201)
host_1.scenarios += scenarios.Iperf3TCPStream(paths, 60, 2, [1024, 8192, 65536], (0, 0), 5201)
host_1.scenarios += scenarios.Iperf3TCPReversed(paths, 60, 2, [1024, 8192, 65536], (0, 0), 5201)
# in TCP Multistream len of cpu_pinning list sets number of parallel TCP stream
host_1.scenarios += scenarios.Iperf3TCPMultiStream(
    paths, 2, 2, 60, 2, [1024, 8192, 65536], [(x, x) for x in range(8)], 5201
)
