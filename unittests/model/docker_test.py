from unittest import TestCase, skip
from nepta.core.model import docker, network
import ipaddress as ia


class DockerModelTest(TestCase):

    def test_images(self):
        local_image = docker.LocalImage('nepta', '.', '~/Dockerfile')
        self.assertEqual(local_image.image_name(), 'nepta')

        remote_image = docker.RemoteImage('quay.io/turbo_image', 'first')
        self.assertEqual(remote_image.image_name(), 'quay.io/turbo_image:first')

    def test_net(self):
        net = docker.Network(
            'net',
            network.NetperfNet4('192.168.0.0/24'),
            network.NetperfNet6('ff02:2::/64')
        )
        self.assertIsNotNone(net.v6)
        net = docker.Network(
            'net',
            network.NetperfNet4('192.168.0.0/24'),
        )
        self.assertIsNone(net.v6)

    def test_volume(self):
        vol1 = docker.Volume('jj', 'ff', 'ro')
        self.assertEqual('jj:ff:ro', vol1.as_arg())

        vol2 = docker.Volume('/test')
        self.assertEqual('/test:/test', vol2.as_arg())

    def test_container(self):
        cont = docker.Container(
            docker.RemoteImage('quay.io/centos', 'latest'),
            'centos', 'centos.lab.com',
            docker.Network(
                'net',
                network.NetperfNet4('172.26.0.0/28'),
            ),
            [
                docker.Volume('data'),
                docker.Volume('db'),
                docker.Volume('tmp'),
            ],
            [
                'JOBID',
                'NEPTA_CONF',
            ],
            privileged=True,
        )
        print('\n')
        print(cont)

        self.assertIsNotNone(cont.v4_conf)
        self.assertIsNone(cont.v6_conf)

        cont = docker.NeptaContainer(
            docker.RemoteImage('quay.io/centos', 'latest'),
            'centos', 'centos.lab.com',
            docker.Network(
                'net',
                network.NetperfNet4('172.26.0.0/28'),
            ),
            [
                docker.Volume('data'),
                docker.Volume('db'),
                docker.Volume('tmp'),
            ],
            [
                'JOBID',
                'NEPTA_CONF',
            ],
            privileged=True,
        )
        print('\n')
        print(cont)

        self.assertIsNotNone(cont.v4_conf)
        self.assertIsNone(cont.v6_conf)
