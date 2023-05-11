import logging

from nepta.core import model
from nepta.core.distribution import conf_files
from nepta.core.strategies.setup.generic import _GenericSetup as Setup
from nepta.core.distribution.utils.system import SystemD
from nepta.core.distribution.utils.virt import Docker, Virsh

logger = logging.getLogger(__name__)


class Virtualization(Setup):
    @Setup.schedule
    def setup_virtual_guest(self):
        logger.info('Configuring virtual hardware for virtual guests')
        virtual_guests = self.conf.get_subset(m_class=model.system.VirtualGuest)

        for guest in virtual_guests:
            logger.info(f'Configuring guest {guest}')

            Virsh.destroy(guest)

            Virsh.set_persistent_max_cpus(guest)
            Virsh.set_cpus(guest)
            Virsh.set_cpu_pinning(guest)

            Virsh.set_persistent_max_mem(guest)
            Virsh.set_mem(guest)

    @Setup.schedule
    def delete_guest_interfaces(self):
        logger.info('Deleting interfaces of virtual guests')
        guests = self.conf.get_subset(m_class=model.system.VirtualGuest)
        for g in guests:
            for i in Virsh.domiflist(g):
                Virsh.detach_interface(g, i['type'], i['mac'])

    @Setup.schedule
    def setup_virt_taps(self):
        logger.info('Setting up virtual guest taps')
        tap_interfaces = self.conf.get_subset(m_class=model.network.GenericGuestTap)
        logger.info(tap_interfaces)

        for tap_int in tap_interfaces:
            logger.info(str(tap_int))
            tap_conf = conf_files.GuestTap(tap_int)
            tap_conf.apply()
            tap_conf_path = tap_conf.get_path()
            Virsh.attach_device(tap_int.guest, tap_conf_path)

    @Setup.schedule
    def setup_docker(self):
        logger.info('Configuring docker components')

        docker_settings = self.conf.get_subset(m_type=model.docker.DockerDaemonSettings)
        for setting in docker_settings:
            docker_conf_file = conf_files.DockerDaemonJson(setting)
            docker_conf_file.update()
        # after changing docker settings, daemon needs to be restarted
        SystemD.restart_service(model.system.SystemService('docker'))

        creds = self.conf.get_subset(m_type=model.docker.DockerCredentials)
        for cred in creds:
            Docker.login(cred)

        images = self.conf.get_subset(m_type=model.docker.RemoteImage)
        for image in images:
            Docker.pull(image)

        images = self.conf.get_subset(m_type=model.docker.LocalImage)
        for img in images:
            Docker.build(img)

        docker_networks = self.conf.get_subset(m_type=model.docker.Network)
        for net in docker_networks:
            Docker.Network.create(net)
