import logging
from time import sleep

from nepta.core.distribution.command import Command
from nepta.core.model.system import VirtualGuest
from nepta.core.model.docker import RemoteImage, LocalImage, DockerCredentials
from nepta.core.model.docker import Container, Network, Volume

logger = logging.getLogger(__name__)


class Docker:
    CMD = 'docker'

    class Network:
        CMD = 'docker network'

        @classmethod
        def create(cls, network: Network):
            cmd_prototype = f'{cls.CMD} create'
            if network.v4:
                cmd_prototype += ' --subnet {} --gateway {}'.format(network.v4, network.v4.gw_ip)
            if network.v6:
                cmd_prototype += ' --ipv6 --subnet {} --gateway {}'.format(network.v6, network.v6.gw_ip)
            cmd_prototype += ' ' + network.name

            cmd = Command(cmd_prototype)
            cmd.run()
            cmd.watch_and_log_error()

    class Volume:
        CMD = 'docker volume'

        @classmethod
        def create(cls, volume: Volume):
            cmd_prototype = f'{cls.CMD} create {volume.name}'
            cmd = Command(cmd_prototype)
            cmd.run()
            cmd.watch_and_log_error()

    def __init__(self):
        super(Docker, self).__init__()
        self.network = Docker.Network()
        self.volume = Docker.Volume()

    @classmethod
    def login(cls, cred: DockerCredentials):
        cmd_proto = f'{cls.CMD} login --username {cred.username} --password {cred.password}'
        if cred.registry:
            cmd_proto += ' ' + cred.registry
        cmd = Command(cmd_proto)
        cmd.run()
        cmd.watch_and_log_error()

    @classmethod
    def pull(cls, image: RemoteImage):
        cmd_proto = f'{cls.CMD} pull {image.repository}'
        if image.tag:
            cmd_proto += ':' + image.tag
        cmd = Command(cmd_proto)
        cmd.run()
        cmd.watch_and_log_error()

    @classmethod
    def build(cls, image: LocalImage):
        cmd_prototype = f'{cls.CMD} build {image.context} -f {image.dockerfile} -t {image.name}'
        cmd = Command(cmd_prototype)
        cmd.run()
        cmd.watch_and_log_error()

    @classmethod
    def run(cls, container: Container):
        # TODO jinja2 ?
        cmd_prototype = f'{cls.CMD} run'

        if container.privileged:
            cmd_prototype += ' --privileged'

        if container.user:
            cmd_prototype += f' -u {container.user}'

        if container.hostname:
            cmd_prototype += f' -h {container.hostname}'

        if container.volumes:
            for vol in container.volumes:
                cmd_prototype += vol.as_arg()

        if container.network:
            cmd_prototype += ' --network {}'.format(container.network.name)
            if container.v4_conf:
                cmd_prototype += ' --ip {}'.format(container.v4_conf.addresses[0].ip)
            if container.v6_conf:
                cmd_prototype += ' --ip6 {}'.format(container.v6_conf.addresses[0].ip)

        if container.env:
            for env_var in container.env:
                cmd_prototype += f' -e {env_var}'

        cmd_prototype += ' ' + container.image.image_name()

        if container.args:
            cmd_prototype += ' ' + ' '.join(container.args)

        cmd = Command(cmd_prototype)
        logger.info(f'Starting container: {cmd}')
        cmd.run()

        sleep(1)
        if cmd.poll() is not None:
            logger.error(cmd.get_output())
        else:
            logger.info('Container is running on background.')


class Virsh:
    # TODO clean asserts and warnings -> unify

    @staticmethod
    def attach_device(guest: VirtualGuest, dfile, persistent=True):
        logger.info('Attaching device specified in %s to guest %s', guest.name, dfile)
        cmd = 'virsh attach-device %s %s' % (guest.name, dfile)
        if persistent:
            cmd += ' --persistent'
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        return retcode

    @staticmethod
    def domiflist(guest: VirtualGuest):
        cmd = 'virsh domiflist %s' % guest.name
        c = Command(cmd)
        c.run()
        out, _ = c.get_output()
        out_lines = out.split('\n')
        out_lines = out_lines[2:-2]
        ret = []
        for line in out_lines:
            parts = line.split()
            ret.append(
                {'interface': parts[0], 'type': parts[1], 'source': parts[2], 'model': parts[3], 'mac': parts[4]}
            )
        return ret

    @staticmethod
    def detach_interface(guest: VirtualGuest, itype, mac, persistent=True):
        logger.info('Detaching interface type %s with mac %s from guest %s', guest.name, itype, mac)
        cmd = 'virsh detach-interface %s %s' % (guest.name, itype)
        if mac:
            cmd += ' --mac %s' % mac
        if persistent:
            cmd += ' --persistent'
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        return retcode

    @staticmethod
    def set_persistent_max_cpus(guest: VirtualGuest):
        logger.info('Setting persistent maximum cpus : %s on guest %s' % (guest.cpu_count, guest.name))
        cmd = 'virsh setvcpus %s %s --config --maximum' % (guest.name, guest.cpu_count)
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        assert not retcode
        return retcode

    @staticmethod
    def set_cpus(guest: VirtualGuest):
        logger.info('Setting number of cpus : %s on guest %s' % (guest.cpu_count, guest.name))
        cmd_config = 'virsh setvcpus %s %s --config' % (guest.name, guest.cpu_count)
        cmd_live = 'virsh setvcpus %s %s --live' % (guest.name, guest.cpu_count)
        c_conf = Command(cmd_config)
        c_live = Command(cmd_live)
        c_conf.run()
        c_live.run()

        _, ret_conf = c_conf.get_output()
        _, ret_live = c_live.get_output()
        assert not ret_conf
        return ret_conf and ret_live

    @staticmethod
    def set_persistent_max_mem(guest: VirtualGuest):
        mem_size = guest.mem_size * 1024  # conversion from MB to Kb because of virsh
        logger.info('Setting persistent maximum memory size : %s kB on guest %s' % (mem_size, guest.name))
        cmd = 'virsh setmaxmem %s %s --config' % (guest.name, mem_size)
        c = Command(cmd)
        c.run()
        output, retcode = c.get_output()
        assert not retcode
        return retcode

    @staticmethod
    def set_mem(guest: VirtualGuest):
        mem_size = guest.mem_size * 1024  # conversion from MB to Kb because of virsh
        logger.info('Setting allocated memory : %s kB on guest %s' % (mem_size, guest.name))
        cmd_config = 'virsh setmem %s %s --config' % (guest.name, mem_size)
        cmd_live = 'virsh setmem %s %s --live' % (guest.name, mem_size)
        c_conf = Command(cmd_config)
        c_live = Command(cmd_live)

        c_conf.run()
        c_live.run()

        _, ret_conf = c_conf.get_output()
        _, ret_live = c_live.get_output()
        assert not ret_conf
        return ret_conf and ret_live

    @staticmethod
    def set_cpu_pinning(guest: VirtualGuest):
        # TODO: refactor: try to aggregate vcpupinning to single cmd
        return_value = False
        logger.info('Setting cpu pinning %s on guest %s' % (guest.cpu_pinning, guest.name))
        for real, virtual in guest.cpu_pinning:
            logger.info('%s >> real cpu : %s , virtual cpu : %s' % (guest.name, real, virtual))
            cmd_conf = 'virsh vcpupin %s %s %s --config' % (guest.name, virtual, real)
            cmd_live = 'virsh vcpupin %s %s %s --live' % (guest.name, virtual, real)
            c_conf = Command(cmd_conf)
            c_live = Command(cmd_live)
            c_conf.run()
            c_live.run()
            _, ret_conf = c_conf.get_output()
            _, ret_live = c_live.get_output()
            assert not ret_conf
            return_value = ret_conf or ret_live or return_value
        return return_value

    @staticmethod
    def destroy(guest: VirtualGuest):
        logger.info('Destroying guest : %s!' % guest.name)
        cmd = 'virsh destroy %s' % guest.name
        c = Command(cmd)
        c.run()
        output, return_code = c.get_output()
        if return_code:
            logger.warning(output)
        else:
            logger.info(output)
        return return_code

    @staticmethod
    def start(guest: VirtualGuest):
        logger.info('Starting guest %s!' % guest.name)
        cmd = 'virsh start %s' % guest.name
        c = Command(cmd)
        c.run()
        output, return_code = c.get_output()
        if return_code:
            logger.error('Virsh >> %s' % output)
        else:
            logger.info('Virsh >> %s' % output)
        return return_code
