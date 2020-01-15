import logging
import os

from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class Docker(object):
    CMD = 'docker'

    class Network(object):
        CMD = 'network'

        @staticmethod
        def create(network):
            cmd_prototype = '{} {} create'.format(Docker.CMD, Docker.Network.CMD)
            if network.v4:
                cmd_prototype += ' --subnet {} --gateway {}'.format(network.v4, network.v4.gw_ip)
            if network.v6:
                cmd_prototype += ' --ipv6 --subnet {} --gateway {}'.format(network.v6, network.v6.gw_ip)
            cmd_prototype += ' ' + network.name

            cmd = Command(cmd_prototype)
            cmd.run()
            out, retcode = cmd.watch_output()
            if retcode:
                logger.error(out)

    class Volume(object):
        CMD = 'volume'

        @staticmethod
        def create(volume):
            cmd_protype = '{} {} create {}'.format(Docker.CMD, Docker.Volume.CMD, volume.name)
            cmd = Command(cmd_protype)
            cmd.run()
            out, retcode = cmd.watch_output()
            if retcode:
                logger.error(out)

    def __init__(self):
        super(Docker, self).__init__()
        self.network = Docker.Network()
        self.volume = Docker.Volume()

    @staticmethod
    def build(image):
        # TODO f string
        cmd_prototype = '{} build {} -f {} -t {}'.format(Docker.CMD, image.context, image.dockerfile, image.name)
        cmd = Command(cmd_prototype)
        cmd.run()
        out, retcode = cmd.watch_output()
        if retcode:
            logger.error(out)

    @staticmethod
    def run(container, inherit_arguments_from_master_proc=True):
        # TODO jinja2 ?
        cmd_prototype = '{} run'.format(Docker.CMD)
        if container.hostname:
            cmd_prototype += ' -h {}'.format(container.hostname)
        if container.network:
            cmd_prototype += ' --network {}'.format(container.network.name)
        if container.volumes:
            for vol in container.volumes:
                cmd_prototype += ' --volume {}:/{}'.format(vol.name, vol.name)
        if container.v4_conf:
            cmd_prototype += ' --ip {}'.format(container.v4_conf.addresses[0].ip)
        if container.v6_conf:
            cmd_prototype += ' --ip6 {}'.format(container.v6_conf.addresses[0].ip)

        if container.inherit_env:
            for env_var in container.inherit_env:
                cmd_prototype += ' -e {}'.format(env_var)

        cmd_prototype += ' ' + container.image.name

        if inherit_arguments_from_master_proc:
            import sys
            if len(sys.argv) > 1:
                cmd_prototype += ' ' + ' '.join(sys.argv[1:])
            else:
                cmd_prototype += ' ' + os.environ['NETWORK_PERFTEST_ARGS']

        if container.extra_arguments:
            cmd_prototype += container.extra_arguments

        cmd = Command(cmd_prototype)
        cmd.run()
        out, ret_code = cmd.watch_output()
        if ret_code:
            logger.error(out)


class Virsh(object):
    # TODO clean asserts and warnings -> unify

    def __init__(self):
        super(Virsh, self).__init__()

    def attach_device(self, guest, dfile, persistent=True):
        guest_name = guest.get_name()
        logger.info('Attaching device specified in %s to guest %s', guest_name, dfile)
        cmd = 'virsh attach-device %s %s' % (guest_name, dfile)
        if persistent:
            cmd += ' --persistent'
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        return retcode

    def domiflist(self, guest):
        guest_name = guest.get_name()
        cmd = 'virsh domiflist %s' % guest_name
        c = Command(cmd)
        c.run()
        out, _ = c.get_output()
        out_lines = out.split('\n')
        out_lines = out_lines[2:-2]
        ret = []
        for line in out_lines:
            parts = line.split()
            ret.append(
                {'interface': parts[0], 'type': parts[1], 'source': parts[2], 'model': parts[3], 'mac': parts[4]})
        return ret

    def detach_interface(self, guest, itype, mac, persistent=True):
        guest_name = guest.get_name()
        logger.info('Detaching interface type %s with mac %s from guest %s', guest_name, itype, mac)
        cmd = 'virsh detach-interface %s %s' % (guest_name, itype)
        if mac:
            cmd += ' --mac %s' % mac
        if persistent:
            cmd += ' --persistent'
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        return retcode

    def set_persistent_max_cpus(self, guest):
        guest_name = guest.get_name()
        num_of_cpus = guest.get_cpu_count()
        logger.info('Setting persistent maximum cpus : %s on guest %s' % (num_of_cpus, guest_name))
        cmd = 'virsh setvcpus %s %s --config --maximum' % (guest_name, num_of_cpus)
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        assert not retcode
        return retcode

    def set_cpus(self, guest):
        guest_name = guest.get_name()
        num_of_cpus = guest.get_cpu_count()
        logger.info('Setting number of cpus : %s on guest %s' % (num_of_cpus, guest_name))
        cmd_config = 'virsh setvcpus %s %s --config' % (guest_name, num_of_cpus)
        cmd_live = 'virsh setvcpus %s %s --live' % (guest_name, num_of_cpus)
        c_conf = Command(cmd_config)
        c_live = Command(cmd_live)
        c_conf.run()
        c_live.run()

        _, ret_conf = c_conf.get_output()
        _, ret_live = c_live.get_output()
        assert not ret_conf
        return ret_conf and ret_live

    def set_persistent_max_mem(self, guest):
        guest_name = guest.get_name()
        mem_size = guest.get_mem_size() * 1024  # conversion from MB to Kb because of virsh
        logger.info('Setting persistent maximum memory size : %s kB on guest %s' % (mem_size, guest_name))
        cmd = 'virsh setmaxmem %s %s --config' % (guest_name, mem_size)
        c = Command(cmd)
        c.run()
        output, retcode = c.get_output()
        assert not retcode
        return retcode

    def set_mem(self, guest):
        guest_name = guest.get_name()
        mem_size = guest.get_mem_size() * 1024  # conversion from MB to Kb because of virsh
        logger.info('Setting allocated memory : %s kB on guest %s' % (mem_size, guest_name))
        cmd_config = 'virsh setmem %s %s --config' % (guest_name, mem_size)
        cmd_live = 'virsh setmem %s %s --live' % (guest_name, mem_size)
        c_conf = Command(cmd_config)
        c_live = Command(cmd_live)

        c_conf.run()
        c_live.run()

        _, ret_conf = c_conf.get_output()
        _, ret_live = c_live.get_output()
        assert not ret_conf
        return ret_conf and ret_live

    def set_cpu_pinning(self, guest):
        return_value = False
        guest_name = guest.get_name()
        cpu_pinning = guest.get_cpu_pinning()
        logger.info('Setting cpu pinning %s on guest %s' % (cpu_pinning, guest_name))
        if cpu_pinning:
            for real, virtual in cpu_pinning:
                logger.info('%s >> real cpu : %s , virtual cpu : %s' % (guest_name, real, virtual))
                cmd_conf = 'virsh vcpupin %s %s %s --config' % (guest_name, virtual, real)
                cmd_live = 'virsh vcpupin %s %s %s --live' % (guest_name, virtual, real)
                c_conf = Command(cmd_conf)
                c_live = Command(cmd_live)
                c_conf.run()
                c_live.run()
                _, ret_conf = c_conf.get_output()
                _, ret_live = c_live.get_output()
                assert not ret_conf
                return_value = ret_conf or ret_live or return_value
        return return_value

    def destroy(self, guest):
        guest_name = guest.get_name()
        logger.info('Destroying guest : %s!' % guest_name)
        cmd = 'virsh destroy %s' % guest_name
        c = Command(cmd)
        c.run()
        output, return_code = c.get_output()
        if return_code:
            logger.warning(output)
        else:
            logger.info(output)
        return return_code

    def start(self, guest):
        guest_name = guest.get_name()
        logger.info('Starting guest %s!' % guest_name)
        cmd = 'virsh start %s' % guest_name
        c = Command(cmd)
        c.run()
        output, return_code = c.get_output()
        if return_code:
            logger.error("Virsh >> %s" % output)
        else:
            logger.info("Virsh >> %s" % output)
        return return_code
