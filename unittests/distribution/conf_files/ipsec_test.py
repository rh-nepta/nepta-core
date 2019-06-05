from unittest import TestCase

from testing.model.network import IPsecTunnel
from testing.distribution.conf_files import IPsecConnFile, IPsecSecretsFile, IPsecRHEL8ConnFile

from ipaddress import IPv4Interface


class IpsecCOonnJinjaTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_basic_ipsec_tunnel_conn(self):
        ipsec_tunnel = IPsecTunnel(IPv4Interface('192.168.1.1/24'), IPv4Interface('192.168.1.2/24'), 'aes128-sha1', 'SUPER_PASS_IPSEC')
        conn_file_obj = IPsecConnFile(ipsec_tunnel)

        excpexted_output = """\
conn transport_IPv4_aes128-sha1
\ttype=transport
\tconnaddrfamily=IPv4
\tauthby=secret
\tleft=192.168.1.1
\tright=192.168.1.2
\tphase2=esp
\tphase2alg=aes128-sha1
\tkeyexchange=ike
\tpfs=yes
\tauto=start
\tencapsulation=no
"""
        self.assertEqual(excpexted_output, conn_file_obj._make_content())


    def test_ipsec_with_specific_arg_test(self):
        ipsec_tunnel = IPsecTunnel(IPv4Interface('192.168.1.1/24'), IPv4Interface('192.168.1.2/24'), 'aes128-sha2',
                                   'SUPER_PASS_IPSEC', IPsecTunnel.MODE_TUNNEL, replay_window=128,
                                   nat_traversal=IPsecTunnel.NAT_TRAVERSAL_YES)
        conn_file_obj = IPsecConnFile(ipsec_tunnel)

        excpexted_output = """\
conn tunnel_IPv4_aes128-sha2
\ttype=tunnel
\tconnaddrfamily=IPv4
\tauthby=secret
\tleft=192.168.1.1
\tright=192.168.1.2
\tphase2=esp
\tphase2alg=aes128-sha2
\tkeyexchange=ike
\tpfs=yes
\tauto=start
\tencapsulation=yes
\treplay-window=128
"""
        self.assertEqual(excpexted_output, conn_file_obj._make_content())


    def test_ipsec_rhel8_with_specific_arg_test(self):
        ipsec_tunnel = IPsecTunnel(IPv4Interface('192.168.1.1/24'), IPv4Interface('192.168.1.2/24'), 'aes128-sha2',
                                   'SUPER_PASS_IPSEC', IPsecTunnel.MODE_TUNNEL, replay_window=128,
                                   nat_traversal=IPsecTunnel.NAT_TRAVERSAL_YES)
        conn_file_obj = IPsecRHEL8ConnFile(ipsec_tunnel)

        excpexted_output = """\
conn tunnel_IPv4_aes128-sha2
\ttype=tunnel
\tauthby=secret
\tleft=192.168.1.1
\tright=192.168.1.2
\tphase2=esp
\tphase2alg=aes128-sha2
\tkeyexchange=ike
\tpfs=yes
\tauto=start
\tencapsulation=yes
\treplay-window=128
"""
        self.assertEqual(excpexted_output, conn_file_obj._make_content())


class IPsecSecretJinjaTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_secret_content(self):
        psw = "wertyuiop;kdszxcvbn"
        ipsec_tunnel = IPsecTunnel(IPv4Interface('192.168.1.1/24'), IPv4Interface('192.168.1.2/24'), 'aes128-sha1', psw)
        ipsec_secret_obj = IPsecSecretsFile(ipsec_tunnel)

        expected_output = "%s %s : PSK \"%s\"\n" % (ipsec_tunnel.left_ip.ip, ipsec_tunnel.right_ip.ip, psw)

        self.assertEqual(expected_output, ipsec_secret_obj._make_content())
