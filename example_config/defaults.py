from ipaddress import IPv4Network, IPv6Network, IPv4Address
from nepta.core.model.network import NetperfNet4, NetperfNet6

net4 = NetperfNet4(IPv4Network('192.168.0.0/24'))
net6 = NetperfNet6(IPv6Network('fe80::/64'))
gw = IPv4Address('172.16.0.254')
dns = [
    IPv4Address('172.16.0.253'),
    IPv4Address('8.8.8.8'),
]
