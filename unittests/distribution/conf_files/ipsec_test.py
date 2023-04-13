from unittest import TestCase

from nepta.core.model.network import IPsecTunnel
from nepta.core.distribution.conf_files import IPsecConnFile, IPsecSecretsFile

from ipaddress import IPv4Interface


class IpsecCOonnJinjaTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_basic_ipsec_tunnel_conn(self):
        ipsec_tunnel = IPsecTunnel(
            IPv4Interface('192.168.1.1/24'), IPv4Interface('192.168.1.2/24'), 'aes128-sha1', 'SUPER_PASS_IPSEC'
        )
        conn_file_obj = IPsecConnFile(ipsec_tunnel)
        conn_file_obj.template = 'ipsec_conn.jinja2'

        excpexted_output = """\
conn IPv4_transport_aes128-sha1_encap-no_192.168.1.1_192.168.1.2
\ttype=transport
\tconnaddrfamily=IPv4
\tauthby=secret
\tleft=192.168.1.1
\tright=192.168.1.2
\tphase2=esp
\tesp=aes128-sha1
\tauto=start
\tencapsulation=no
\tnic-offload=no
"""
        self.assertEqual(excpexted_output, conn_file_obj._make_content())

    def test_ipsec_with_specific_arg_test(self):
        ipsec_tunnel = IPsecTunnel(
            IPv4Interface('192.168.1.1/24'),
            IPv4Interface('192.168.1.2/24'),
            'aes128-sha2',
            'SUPER_PASS_IPSEC',
            IPsecTunnel.Mode.TUNNEL,
            replay_window=128,
            encapsulation=IPsecTunnel.Encapsulation.YES,
            nic_offload=IPsecTunnel.Offload.YES,
        )
        conn_file_obj = IPsecConnFile(ipsec_tunnel)
        conn_file_obj.template = 'ipsec_conn.jinja2'

        excpexted_output = """\
conn IPv4_tunnel_aes128-sha2_encap-yes_192.168.1.1_192.168.1.2
\ttype=tunnel
\tconnaddrfamily=IPv4
\tauthby=secret
\tleft=192.168.1.1
\tright=192.168.1.2
\tphase2=esp
\tesp=aes128-sha2
\tauto=start
\tencapsulation=yes
\treplay-window=128
\tnic-offload=yes
"""
        self.assertEqual(excpexted_output, conn_file_obj._make_content())

    def test_ipsec_rhel8_with_specific_arg_test(self):
        ipsec_tunnel = IPsecTunnel(
            IPv4Interface('192.168.1.1/24'),
            IPv4Interface('192.168.1.2/24'),
            'aes128-sha2',
            'SUPER_PASS_IPSEC',
            IPsecTunnel.Mode.TUNNEL,
            replay_window=128,
            encapsulation=IPsecTunnel.Encapsulation.YES,
            nic_offload=IPsecTunnel.Offload.YES,
        )
        conn_file_obj = IPsecConnFile(ipsec_tunnel)

        excpexted_output = """\
conn IPv4_tunnel_aes128-sha2_encap-yes_192.168.1.1_192.168.1.2
\ttype=tunnel
\tauthby=secret
\tleft=192.168.1.1
\tright=192.168.1.2
\tphase2=esp
\tesp=aes128-sha2
\tauto=start
\tencapsulation=yes
\treplay-window=128
\tnic-offload=yes
"""
        self.assertEqual(excpexted_output, conn_file_obj._make_content())


class IPsecSecretJinjaTest(TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.maxDiff = None

    def test_secret_content(self):
        psw = 'wertyuiop;kdszxcvbn'
        ipsec_tunnel = IPsecTunnel(IPv4Interface('192.168.1.1/24'), IPv4Interface('192.168.1.2/24'), 'aes128-sha1', psw)
        ipsec_secret_obj = IPsecSecretsFile(ipsec_tunnel)

        expected_output = "%s %s : PSK \"%s\"\n" % (ipsec_tunnel.left_ip.ip, ipsec_tunnel.right_ip.ip, psw)

        self.assertEqual(expected_output, ipsec_secret_obj._make_content())
