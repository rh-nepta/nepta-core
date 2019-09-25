import os
import logging
import time
from jinja2 import Template

from nepta.core.strategies.generic import Strategy
from nepta.core import model
from nepta.core.distribution import components, conf_files, env

logger = logging.getLogger(__name__)


class Setup(Strategy):
    SETTLE_TIME = 30

    _INSTALLER = 'yum -y install '
    _INSTALLER_COMMAND_TEMPLATE = Template("""{{ installer }} {{ pkg.value }} \
{% for repo in pkg.disable_repos %}--disablerepo {{ repo.key }} {% endfor %}\
{% for repo in pkg.enable_repos %}--enablerepo {{ repo.key }} {% endfor %}""")

    def __init__(self, conf):
        super().__init__()
        self.conf = conf

    @Strategy.schedule
    def add_repositories(self):
        logger.info('Adding repositories')
        repos = self.conf.get_subset(m_class=model.system.Repository)
        for repo in repos:
            logger.info('Adding repo %s', repo.get_key())
            conf_files.RepositoryFile(repo).apply()

    @Strategy.schedule
    def install_packages(self):
        pkgs = self.conf.get_subset(m_type=model.system.Package)
        install_cmd = self._INSTALLER + " ".join([str(pkg.value) for pkg in pkgs])
        c = components.Command(install_cmd)
        c.run()
        out, retcode = c.watch_output()
        logger.info(out)

    @Strategy.schedule
    def install_special_packages(self):
        spec_pkgs = self.conf.get_subset(m_type=model.system.SpecialPackage)
        for pkg in spec_pkgs:
            install_cmd = self._INSTALLER_COMMAND_TEMPLATE.render(installer=self._INSTALLER, pkg=pkg)
            c = components.Command(install_cmd)
            c.run()
            out, retcode = c.watch_output()
            logger.info(out)

    @Strategy.schedule
    def configure_ssh(self):
        logger.info('Configuring SSH client')
        pubkeys = self.conf.get_subset(m_class=model.system.SSHAuthorizedKey)
        if len(pubkeys) > 0:
            conf_files.SSHAuthorizedKeysFile(pubkeys).apply()

        identities = self.conf.get_subset(m_class=model.system.SSHIdentity)
        if len(identities) > 0:
            # TODO : support more public keys
            # curently only one private key is supported
            first_identity = identities[0]

            # install the SSH private key and corresponding public key
            conf_files.SSHPrivateKey(first_identity).apply()
            conf_files.SSHPublicKey(first_identity).apply()

        confs = self.conf.get_subset(m_class=model.system.SSHConfigItem)
        conf_files.SSHConfig(confs).apply()

    # Use /kernel/networking/kdump task instead of configuring KDump in our
    # test framework.
    @Strategy.schedule
    def configure_kdump(self):
        logger.info('Configuring KDump')
        confs = self.conf.get_subset(m_class=model.system.KDumpOption)
        conf_files.KDump(confs).apply()

    @Strategy.schedule
    def configure_kernel_variables(self):
        logger.info('Configuring sysctl variables')
        kvars = self.conf.get_subset(m_class=model.system.SysctlVariable)
        conf_files.SysctlFile(kvars).apply()
        sysctl_cmd = 'sysctl --system'
        c = components.Command(sysctl_cmd)
        c.run()
        c.watch_output()

    @Strategy.schedule
    def configure_tuned_profile(self):
        profile = self.conf.get_subset(m_type=model.system.TunedAdmProfile)
        if len(profile):
            if len(profile) > 1:
                logger.warning('Too many tuned profiles in configuration \n%s' % self.conf)
            profile = profile[0]
            logger.info("Setting tuned-adm profile: %s" % profile)
            out, retcode = components.Tuned.set_profile(profile.value)
            if retcode:
                logger.error(out)

    @Strategy.schedule
    def configure_services(self):
        sysv_services = self.conf.get_subset(model.system.SysVInitService)
        systemd_services = self.conf.get_subset(model.system.SystemdService)
        sysvinit_component = components.sysvinit

        for vs in sysv_services:
            sysvinit_component.configure_service(vs)

        # to be rewrited using systemd component
        for ss in systemd_services:
            sysvinit_component.configure_service(ss)

    def stop_net(self):
        raise NotImplementedError

    def start_net(self):
        raise NotImplementedError

    def setup_udev_rules(self):
        raise NotImplementedError

    @Strategy.schedule
    def delete_old_ipsec_conf(self):
        logging.info('Deleting old ipsec tunnel conf-files')

        if os.path.exists(conf_files.IPsecConnFile.IPSEC_CONF_DIR):
            ls_dir = components.fs.list_path(conf_files.IPsecConnFile.IPSEC_CONF_DIR)
            for conn_file in [x for x in ls_dir if x.startswith(conf_files.IPsecConnFile.IPSEC_CONF_PREFIX)]:
                logging.debug("Deleting : {}".format(conn_file))
                components.fs.rm(os.path.join(conf_files.IPsecConnFile.IPSEC_CONF_DIR, conn_file))

    @Strategy.schedule
    def setup_ipsec(self):
        logger.info('Setting up ipsec subsystem')
        sysvinit_component = components.sysvinit
        sysvinit_component.stop_service('ipsec')

        tuns = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tun in tuns:
            conf_files.IPsecConnFile(tun).apply()
            conf_files.IPsecSecretsFile(tun).apply()

        sysvinit_component.start_service('ipsec')

    @staticmethod
    def wipe_interfaces_config():
        logger.info('Wiping old interfaces configuration')
        wipe_list = []
        ifcfg_dir = conf_files.IfcfgFile.IFCFG_DIRECTORY
        fs_component = components.fs
        ifcfg_files = fs_component.list_path(ifcfg_dir)
        for f in ifcfg_files:
            if f.startswith('ifcfg-') and not f.startswith('ifcfg-lo'):
                wipe_list.append(os.path.join(ifcfg_dir, f))
        if fs_component.path_exists(conf_files.UdevRulesFile.RULES_FILE):
            wipe_list.append(conf_files.UdevRulesFile.RULES_FILE)
        logger.info('Files to be wiped: %s', wipe_list)
        for w in wipe_list:
            fs_component.rm_path(w)

    def rename_ifaces_runtime(self):
        ip_tool = components.ip
        ifaces = self.conf.get_subset(m_type=model.network.EthernetInterface)
        for iface in ifaces:
            old_name = ip_tool.link.get_interface_name(iface.mac)
            new_name = iface.name
            if old_name is not None and old_name != new_name:
                ip_tool.link.down_interface(old_name)
                ip_tool.link.rename_interface(old_name, new_name)
                ip_tool.link.up_interface(new_name)

    def store_persistent_cfg(self):
        ifaces = self.conf.get_subset(m_class=model.network.EthernetInterface)
        for iface in ifaces:
            cf = conf_files.IfcfgFile(iface)
            cf.apply()

    @Strategy.schedule
    def setup_interfaces(self):
        logger.info('Setting up interfaces')
        self.stop_net()
        self.wipe_interfaces_config()
        self.wipe_routes()
        self.setup_udev_rules()
        self.rename_ifaces_runtime()
        self.store_persistent_cfg()
        self.setup_routes()
        self.start_net()

    @staticmethod
    def wipe_routes():
        logger.info('Wiping old routes configuration')
        wipe_list = []
        ifcfg_dir = conf_files.Route4File.ROUTE_DIRECTORY
        fs_component = components.fs
        ifcfg_files = fs_component.list_path(ifcfg_dir)
        for f in ifcfg_files:
            if f.startswith('route-') or f.startswith('route6-'):
                wipe_list.append(os.path.join(ifcfg_dir, f))
        logger.info('Files to be wiped: %s', wipe_list)
        for w in wipe_list:
            fs_component.rm_path(w)

    def setup_routes(self):
        logger.info('Setting up routes')
        self.wipe_routes()
        routes4 = self.conf.get_subset(m_class=model.network.Route4)
        devs4 = {}
        for r in routes4:
            if_name = r.get_interface().name
            if if_name not in devs4.keys():
                devs4[if_name] = [r]
            else:
                devs4[if_name].append(r)

        routes6 = self.conf.get_subset(m_class=model.network.Route6)
        devs6 = {}
        for r in routes6:
            if_name = r.get_interface().name
            if if_name not in devs6.keys():
                devs6[if_name] = [r]
            else:
                devs6[if_name].append(r)

        for dev in devs4.keys():
            conf_files.Route4File(routes=devs4[dev]).apply()

        for dev in devs6.keys():
            conf_files.Route6File(routes=devs6[dev]).apply()

    @Strategy.schedule
    def setup_hostname(self):
        hostname = self.conf.get_hostname()
        logger.info('Setting up hostname %s', hostname)
        cf = conf_files.HostnameConfFile(hostname)
        cf.apply()
        c = components.Command('hostname -F %s' % cf.get_path())
        c.run()
        c.watch_output()

    @Strategy.schedule
    def setup_ovswitch(self):
        logger.info('Setting up ovswitch configuration')
        ovswitches = self.conf.get_subset(m_class=model.network.OVSwitch)
        vsctl_component = components.ovs_vsctl
        for ovs in ovswitches:
            interfaces = ovs.interfaces
            tunnels = ovs.tunnel_interfaces
            vsctl_component.add_bridge(ovs)
            for iface in interfaces:
                vsctl_component.add_port(ovs, iface)
            for tun in tunnels:
                vsctl_component.add_tunnel_port(ovs, tun)

    @Strategy.schedule
    def setup_lldpad(self):
        logger.info('Enabling lldp on all ethernet interfaces')
        ethernet_masters = self.conf.get_subset(m_type=model.network.EthernetInterface)
        components.lldptool.restart_lldpad()
        components.lldptool.enable_on_interfaces(ethernet_masters)
        logger.info(components.lldptool.discover_topology(ethernet_masters))

    @Strategy.schedule
    def setup_virtual_guest(self):
        logger.info('Configuring virtual hardware for virtual guests')
        virtual_guests = self.conf.get_subset(m_class=model.system.VirtualGuest)
        virsh_component = components.virsh

        for guest in virtual_guests:
            logger.info('Configuring guest %s' % str(guest))

            virsh_component.destroy(guest)

            virsh_component.set_persistent_max_cpus(guest)
            virsh_component.set_cpus(guest)
            virsh_component.set_persistent_max_mem(guest)
            virsh_component.set_mem(guest)
            virsh_component.set_cpu_pinning(guest)

    @Strategy.schedule
    def delete_guest_interfaces(self):
        logger.info('Deleting interfaces of virtual guests')
        virsh_component = components.virsh
        guests = self.conf.get_subset(m_class=model.system.VirtualGuest)
        for g in guests:
            ifaces = virsh_component.domiflist(g)
            for i in ifaces:
                virsh_component.detach_interface(g, i['type'], i['mac'])

    @Strategy.schedule
    def setup_virt_taps(self):
        logger.info('Setting up virtual guest taps')
        tap_interfaces = self.conf.get_subset(m_class=model.network.GenericGuestTap)
        logger.info(tap_interfaces)
        virsh = components.virsh

        for tap_int in tap_interfaces:
            logger.info(str(tap_int))
            tap_conf = conf_files.GuestTap(tap_int)
            tap_conf.apply()
            tap_conf_path = tap_conf.get_path()
            virsh.attach_device(tap_int.guest, tap_conf_path)

    @Strategy.schedule
    def setup_ntp(self):
        raise NotImplementedError

    @Strategy.schedule
    def setup_docker(self):
        logger.info('Configuring docker components')
        docker = components.docker

        docker_settings = self.conf.get_subset(m_type=model.docker.DockerDaemonSettings)
        for setting in docker_settings:
            docker_conf_file = conf_files.DockerDaemonJson(setting)
            docker_conf_file.update()
        # after changing docker settings, daemon needs to be restarted
        components.sysvinit.restart_service('docker')

        images = self.conf.get_subset(m_type=model.docker.Image)
        for img in images:
            docker.build(img)

        docker_networks = self.conf.get_subset(m_type=model.docker.Network)
        for net in docker_networks:
            docker.network.create(net)

        docker_volumes = self.conf.get_subset(m_type=model.docker.Volume)
        for vol in docker_volumes:
            docker.volume.create(vol)

    @Strategy.schedule
    def wait(self):
        logger.info('Sleeping for %s secs, to give background processes time to settle' % self.SETTLE_TIME)
        time.sleep(self.SETTLE_TIME)


class Rhel6(Setup):

    def stop_net(self):
        sysvinit_component = components.sysvinit
        sysvinit_component.stop_service('network')

    def start_net(self):
        sysvinit_component = components.sysvinit
        sysvinit_component.start_service('network')

    def setup_udev_rules(self):
        return  # no udev rules needed on rhel6

    @Strategy.schedule
    def setup_ntp(self):
        logger.info('Setting chrony ntp configuration')
        return


class Rhel7(Setup):

    def stop_net(self):
        sysvinit_component = components.sysvinit
        sysvinit_component.stop_service('NetworkManager')

    def start_net(self):
        sysvinit_component = components.sysvinit
        sysvinit_component.start_service('NetworkManager')
        c0 = components.Command('nmcli connection reload')
        c0.run()
        c0.watch_output()
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        for iface in ifaces:
            c1 = components.Command('ifdown %s' % iface.name)
            c1.run()
            c1.watch_output()
            c2 = components.Command('ifup %s' % iface.name)
            c2.run()
            c2.watch_output()

    def setup_udev_rules(self):
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        conf_files.UdevRulesFile(ifaces).apply()

    @Strategy.schedule
    def setup_ntp(self):
        servers = self.conf.get_subset(m_class=model.system.NTPServer)
        if len(servers) > 0:
            conf_files.ChronyConf(servers[0]).apply()


class Rhel8(Rhel7):

    _INSTALLER = 'dnf -y --allowerasing install '

    @Strategy.schedule
    def setup_ipsec(self):
        logger.info('Setting up ipsec subsystem')
        sysvinit_component = components.sysvinit
        sysvinit_component.stop_service('ipsec')

        tuns = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tun in tuns:
            conf_files.IPsecRHEL8ConnFile(tun).apply()
            conf_files.IPsecSecretsFile(tun).apply()

        sysvinit_component.start_service('ipsec')

    def stop_net(self):
        # FIXME: check if this WA is still necessary
        # ifdown all interfaces in the system
        for iface in components.IpCommand.Link.get_all_interfaces():
            cmd = components.Command('ifdown %s' % iface)
            cmd.run()
            cmd.watch_output()

        super().stop_net()


def get_strategy(conf):
    if env.rh_release.get_version().startswith('6'):
        return Rhel6(conf)
    elif env.rh_release.get_version().startswith('7'):
        return Rhel7(conf)
    else:
        return Rhel8(conf)
