from . import network


class Image(object):

    def __init__(self, name, context, dockerfile):
        self.name = name
        self.context = context
        self.dockerfile = dockerfile


class Volume(object):

    def __init__(self, name):
        self.name = name


class Network(object):

    def __init__(self, name, v4=None, v6=None):
        self.name = name
        self.v4 = v4 if v4 is None else DockerSubnetV4(v4)
        self.v6 = v6 if v6 is None else DockerSubnetV6(v6)

    def __str__(self):
        return "Docker network: {}\n" \
               "\tV4: {}\n" \
               "\tV6: {}\n".format(self.name, self.v4, self.v6)


class GenericDockerSubnet(object):

    def __init__(self, net):
        super(GenericDockerSubnet, self).__init__(net)
        self.gw = self.new_addr()

    @property
    def gw_ip(self):
        return self.gw.ip


class DockerSubnetV4(GenericDockerSubnet, network.NetperfNet4):
    pass


class DockerSubnetV6(GenericDockerSubnet, network.NetperfNet6):
    pass


class Containter(object):

    DEFAULT_INHERIT_ENV = ['JOBID', 'TEST', 'ARCH', 'DISTRO', 'BEAKER_JOB_WHITEBOARD', 'LAB_CONTROLLER', 'RECIPEID',]

    def __init__(self, image, hostname=None, network=None, volumes=None, extra_arguments=None, inherit_env=None):
        self.image = image
        self.hostname = hostname
        self.network = network
        self.volumes = volumes
        self.v4_conf = network.v4.new_config() if network is not None else None
        self.v6_conf = network.v6.new_config() if network is not None else None
        self.extra_arguments = extra_arguments
        self.inherit_env = inherit_env if inherit_env is not None else self.DEFAULT_INHERIT_ENV


class DockerDaemonSettings(dict):

    def __hash__(self):
        return hash(frozenset(self))


if __name__ == "__main__":
    net = Network('dickernetq', network.NetperfNet4('192.168.22.0/24'), network.NetperfNet6('fd01::/64'))
    print(net)
    print(DockerSubnetV4.__mro__)
    print(net.v4)
    print(net.v4.gw)
    print(net.v6.gw)
    print(net.v4.new_config())
    print(net.v6.new_config())
