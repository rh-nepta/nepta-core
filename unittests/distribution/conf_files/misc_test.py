from unittest import TestCase
from ipaddress import IPv4Interface, IPv6Interface, IPv4Network, IPv6Network, IPv4Address, IPv6Address

from testing.model.system import Repository
from testing.model.network import Route4, Route6, EthernetInterface
from testing.model.network import IPv4Configuration, IPv6Configuration
from testing.distribution.conf_files import RepositoryFile, Route4File, Route6File


class MiscTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_repo_conf(self):
        repo = Repository('rh-repo', 'https://gist.github.com/wrunk/1317933/d204be62e6001ea21e99ca0a90594200ade2511e')
        repo_file = RepositoryFile(repo)

        expected_out = """\
[{name}]
name={name}
enabled=1
gpgcheck=0
baseurl={baseurl}
""".format(name=repo.key, baseurl=repo.value)

        self.assertEqual(expected_out, repo_file._make_content())

    def test_4_routes(self):
        eth = EthernetInterface('bnxt', 'aa:bb:cc:dd:ee:ff', IPv4Configuration([IPv4Interface('192.168.0.1/24')]))
        route = Route4(IPv4Network('10.0.0.0/24'), eth, IPv4Address('10.0.0.2'))
        route_nogw = Route4(IPv4Network('10.0.0.0/24'), eth)
        route_file = Route4File([route, route_nogw])

        expected_output = '10.0.0.0/24 via 10.0.0.2 dev bnxt metric 0\n' \
                          '10.0.0.0/24 via 10.0.0.0/24 dev bnxt metric 0\n'

        self.assertEqual(expected_output, route_file.get_content())

    def test_6_routes(self):
        eth = EthernetInterface('bnxt', 'aa:bb:cc:dd:ee:ff', IPv6Configuration([IPv6Interface('fd00::1/64')]))
        route = Route4(IPv6Network('2001:32::/64'), eth, IPv6Address('fd00::ff'))
        route_nogw = Route4(IPv6Network('2001:32::/64'), eth)
        route_file = Route4File([route, route_nogw])

        expected_output = '2001:32::/64 via fd00::ff dev bnxt metric 0\n' \
                          '2001:32::/64 via 2001:32::/64 dev bnxt metric 0\n'

        self.assertEqual(expected_output, route_file.get_content())
