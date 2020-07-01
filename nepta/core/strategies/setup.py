import os
import logging
import time
from jinja2 import Template
from collections import defaultdict

from nepta.core.strategies.generic import Strategy
from nepta.core import model
from nepta.core.distribution import conf_files, env
from nepta.core.distribution.command import Command
from nepta.core.distribution.utils.system import Tuned, SysVInit, SystemD, KernelModuleUtils
from nepta.core.distribution.utils.fs import Fs
from nepta.core.distribution.utils.network import IpCommand, LldpTool, OvsVsctl
from nepta.core.distribution.utils.virt import Docker, Virsh

logger = logging.getLogger(__name__)


class Setup(Strategy):
    SETTLE_TIME = 30

    _INSTALLER = 'yum -y install '
    _INSTALLER_COMMAND_TEMPLATE = Template(
        """{{ installer }} {{ pkg.name }} \
{% for repo in pkg.disable_repos %}--disablerepo {{ repo.key }} {% endfor %}\
{% for repo in pkg.enable_repos %}--enablerepo {{ repo.key }} {% endfor %}"""
    )

    def __init__(self, conf):
        super().__init__()
        self.conf = conf

    @Strategy.schedule
    def add_repositories(self):
        logger.info('Adding repositories')
        repos = self.conf.get_subset(m_class=model.system.Repository)
        for repo in repos:
            logger.info('Adding repo %s', repo)
            conf_files.RepositoryFile(repo).apply()

    @Strategy.schedule
    def install_packages(self):
        pkgs = self.conf.get_subset(m_type=model.system.Package)
        install_cmd = self._INSTALLER + ' '.join([str(pkg.value) for pkg in pkgs])
        c = Command(install_cmd)
        c.run()
        out, retcode = c.watch_output()
        logger.info(out)

    @Strategy.schedule
    def install_special_packages(self):
        spec_pkgs = self.conf.get_subset(m_type=model.system.SpecialPackage)
        for pkg in spec_pkgs:
            install_cmd = self._INSTALLER_COMMAND_TEMPLATE.render(installer=self._INSTALLER, pkg=pkg)
            c = Command(install_cmd)
            c.run()
            out, retcode = c.watch_output()
            logger.info(out)

    @Strategy.schedule
    def configure_ssh(self):
        logger.info('Configuring SSH client')
        pub_keys = self.conf.get_subset(m_class=model.system.SSHAuthorizedKey)
        conf_files.SSHAuthorizedKeysFile(pub_keys).apply()

        identities = self.conf.get_subset(m_class=model.system.SSHIdentity)
        for ident in identities:
            conf_files.SSHPrivateKey(ident).apply()
            conf_files.SSHPublicKey(ident).apply()

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
        c = Command('sysctl --system')
        c.run()
        c.watch_output()

    @Strategy.schedule
    def configure_tuned_profile(self):
        profile = self.conf.get_subset(m_type=model.system.TunedAdmProfile)
        if len(profile):
            if len(profile) > 1:
                logger.warning('Too many tuned profiles in configuration \n%s' % self.conf)
            profile = profile[0]
            logger.info('Setting tuned-adm profile: %s' % profile)
            out, retcode = Tuned.set_profile(profile.value)
            if retcode:
                logger.error(out)

    @Strategy.schedule
    def configure_services(self):
        for service in self.conf.get_subset(model.system.SystemService):
            SysVInit.configure_service(service)

    @Strategy.schedule
    def configure_kernel_modules(self):
        logger.info('Configuring kernel modules')
        for mod in self.conf.get_subset(m_class=model.system.KernelModule):
            logger.info(f'Configuring module {mod}')
            conf_files.KernelLoadModuleConfig(mod).apply()
            conf_files.KernelModuleOptions(mod).apply()
            logger.info(f'Inserting module {mod}')
            KernelModuleUtils.modprobe(mod)

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
            ls_dir = Fs.list_path(conf_files.IPsecConnFile.IPSEC_CONF_DIR)
            for conn_file in [x for x in ls_dir if x.startswith(conf_files.IPsecConnFile.IPSEC_CONF_PREFIX)]:
                logging.debug('Deleting : {}'.format(conn_file))
                Fs.rm(os.path.join(conf_files.IPsecConnFile.IPSEC_CONF_DIR, conn_file))

    @Strategy.schedule
    def setup_ipsec(self):
        logger.info('Setting up ipsec subsystem')
        ipsec_service = model.system.SystemService('ipsec')
        SystemD.stop_service(ipsec_service)

        tuns = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tun in tuns:
            conf_files.IPsecConnFile(tun).apply()
            conf_files.IPsecSecretsFile(tun).apply()

        SystemD.start_service(ipsec_service)

    @Strategy.schedule
    def delete_old_wireguard_conf(self):
        logging.info('Deleting old wireguard tunnel conf-files')

        if os.path.exists(conf_files.WireGuardConnectionFile.CONF_DIR):
            ls_dir = Fs.list_path(conf_files.WireGuardConnectionFile.CONF_DIR)
            for conn_file in [x for x in ls_dir if x.endswith(conf_files.WireGuardConnectionFile.SUFFIX)]:
                logging.debug('Deleting : {}'.format(conn_file))
                Fs.rm(os.path.join(conf_files.WireGuardConnectionFile.CONF_DIR, conn_file))

    @Strategy.schedule
    def setup_wireguard(self):
        logger.info('Setting up WireGuard subsystem')

        tuns = self.conf.get_subset(m_class=model.network.WireGuardTunnel)
        for tun in tuns:
            # We must stop&start wg-quick for *every* connection
            svc = model.system.SystemService(f'wg-quick@{tun.name}')
            SystemD.stop_service(svc)
            conf_files.WireGuardConnectionFile(tun).apply()
            SystemD.start_service(svc)
            SystemD.enable_service(svc)

    @staticmethod
    def wipe_interfaces_config():
        logger.info('Wiping old interfaces configuration')
        wipe_list = []
        ifcfg_dir = conf_files.IfcfgFile.IFCFG_DIRECTORY
        ifcfg_files = Fs.list_path(ifcfg_dir)
        for f in ifcfg_files:
            if f.startswith('ifcfg-') and not f.startswith('ifcfg-lo'):
                wipe_list.append(os.path.join(ifcfg_dir, f))
        if Fs.path_exists(conf_files.UdevRulesFile.RULES_FILE):
            wipe_list.append(conf_files.UdevRulesFile.RULES_FILE)
        logger.info('Files to be wiped: %s', wipe_list)
        for w in wipe_list:
            Fs.rm_path(w)

    def rename_ifaces_runtime(self):
        ifaces = self.conf.get_subset(m_type=model.network.EthernetInterface)
        for iface in ifaces:
            old_name = IpCommand.Link.get_interface_name(iface.mac)
            new_name = iface.name
            if old_name is not None and old_name != new_name:
                IpCommand.Link.down_interface(old_name)
                IpCommand.Link.rename_interface(old_name, new_name)
                IpCommand.Link.up_interface(new_name)

    def store_persistent_cfg(self):
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
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
        ifcfg_files = Fs.list_path(ifcfg_dir)
        for f in ifcfg_files:
            if f.startswith('route-') or f.startswith('route6-'):
                wipe_list.append(os.path.join(ifcfg_dir, f))
        logger.info('Files to be wiped: %s', wipe_list)
        for w in wipe_list:
            Fs.rm_path(w)

    def setup_routes(self):
        logger.info('Setting up routes')
        self.wipe_routes()
        for route_class, route_cfg in [
            [model.network.Route4, conf_files.Route4File],
            [model.network.Route6, conf_files.Route6File],
        ]:
            routes = self.conf.get_subset(m_class=route_class)
            routes_per_interface = defaultdict(list)
            for r in routes:
                routes_per_interface[r.interface.name].append(r)

            for int_routes in routes_per_interface.items():
                route_cfg(int_routes).apply()

    @Strategy.schedule
    def setup_hostname(self):
        hostname = self.conf.get_hostname()
        logger.info('Setting up hostname %s', hostname)
        cf = conf_files.HostnameConfFile(hostname)
        cf.apply()
        c = Command('hostname -F %s' % cf.get_path())
        c.run()
        c.watch_output()

    @Strategy.schedule
    def setup_ovswitch(self):
        logger.info('Setting up ovswitch configuration')
        ovswitches = self.conf.get_subset(m_class=model.network.OVSwitch)
        for ovs in ovswitches:
            interfaces = ovs.interfaces
            tunnels = ovs.tunnels
            OvsVsctl.add_bridge(ovs)
            for iface in interfaces:
                OvsVsctl.add_port(ovs, iface)
            for tun in tunnels:
                OvsVsctl.add_tunnel_port(ovs, tun)

    @Strategy.schedule
    def setup_lldpad(self):
        logger.info('Enabling lldp on all ethernet interfaces')
        ethernet_masters = self.conf.get_subset(m_type=model.network.EthernetInterface)
        LldpTool.restart_lldpad()
        LldpTool.enable_on_interfaces(ethernet_masters)
        logger.info(LldpTool.discover_topology(ethernet_masters))

    @Strategy.schedule
    def setup_virtual_guest(self):
        logger.info('Configuring virtual hardware for virtual guests')
        virtual_guests = self.conf.get_subset(m_class=model.system.VirtualGuest)

        for guest in virtual_guests:
            logger.info('Configuring guest %s' % str(guest))

            Virsh.destroy(guest)

            Virsh.set_persistent_max_cpus(guest)
            Virsh.set_cpus(guest)
            Virsh.set_persistent_max_mem(guest)
            Virsh.set_mem(guest)
            Virsh.set_cpu_pinning(guest)

    @Strategy.schedule
    def delete_guest_interfaces(self):
        logger.info('Deleting interfaces of virtual guests')
        guests = self.conf.get_subset(m_class=model.system.VirtualGuest)
        for g in guests:
            ifaces = Virsh.domiflist(g)
            for i in ifaces:
                Virsh.detach_interface(g, i['type'], i['mac'])

    @Strategy.schedule
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

    @Strategy.schedule
    def setup_ntp(self):
        raise NotImplementedError

    @Strategy.schedule
    def setup_docker(self):
        logger.info('Configuring docker components')

        docker_settings = self.conf.get_subset(m_type=model.docker.DockerDaemonSettings)
        for setting in docker_settings:
            docker_conf_file = conf_files.DockerDaemonJson(setting)
            docker_conf_file.update()
        # after changing docker settings, daemon needs to be restarted
        SystemD.restart_service(model.system.SystemService('docker'))

        images = self.conf.get_subset(m_type=model.docker.Image)
        for img in images:
            Docker.build(img)

        docker_networks = self.conf.get_subset(m_type=model.docker.Network)
        for net in docker_networks:
            Docker.Network.create(net)

        docker_volumes = self.conf.get_subset(m_type=model.docker.Volume)
        for vol in docker_volumes:
            Docker.Volume.create(vol)

    @Strategy.schedule
    def generate_pcp_config(self):
        for pcp in self.conf.get_subset(m_type=model.system.PCPConfiguration):
            logger.info(f'Generating PCP configuration: {pcp}')
            if os.path.exists(pcp.config_path):
                logger.info('PCP config already exists >> Deleting ')
                os.remove(pcp.config_path)

            cmd = Command(f'pmlogconf -c {pcp.config_path}').run()
            out, ret_code = cmd.watch_output()
            if ret_code:
                logger.error(f'PCP cannot generate configuration! Log: {out}')

    @Strategy.schedule
    def wait(self):
        logger.info('Sleeping for %s secs, to give background processes time to settle' % self.SETTLE_TIME)
        time.sleep(self.SETTLE_TIME)


class Rhel6(Setup):
    def stop_net(self):
        SysVInit.stop_service(model.system.SystemService('network'))

    def start_net(self):
        SysVInit.start_service(model.system.SystemService('network'))

    def setup_udev_rules(self):
        return  # no udev rules needed on rhel6

    @Strategy.schedule
    def setup_ntp(self):
        logger.info('Setting chrony ntp configuration')
        return


class Rhel7(Setup):
    @Strategy.schedule
    def configure_services(self):
        for service in self.conf.get_subset(model.system.SystemService):
            SystemD.configure_service(service)

    def stop_net(self):
        SystemD.stop_service(model.system.SystemService('NetworkManager'))

    def start_net(self):
        SystemD.start_service(model.system.SystemService('NetworkManager'))
        c0 = Command('nmcli connection reload')
        c0.run()
        c0.watch_output()
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        for iface in ifaces:
            c1 = Command('ifdown %s' % iface.name)
            c1.run()
            c1.watch_output()
            c2 = Command('ifup %s' % iface.name)
            c2.run()
            c2.watch_output()

    def setup_udev_rules(self):
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        conf_files.UdevRulesFile(ifaces).apply()

    @Strategy.schedule
    def setup_ntp(self):
        servers = self.conf.get_subset(m_class=model.system.NTPServer)
        conf_files.ChronyConf(servers).apply()


class Rhel8(Rhel7):
    _INSTALLER = 'dnf -y --allowerasing install '

    @Strategy.schedule
    def setup_ipsec(self):
        logger.info('Setting up ipsec subsystem')
        SystemD.stop_service(model.system.SystemService('ipsec'))

        tuns = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tun in tuns:
            conf_files.IPsecRHEL8ConnFile(tun).apply()
            conf_files.IPsecSecretsFile(tun).apply()

        SystemD.start_service(model.system.SystemService('ipsec'))

    def stop_net(self):
        # FIXME: check if this WA is still necessary
        # ifdown all interfaces in the system
        for iface in IpCommand.Link.get_all_interfaces():
            cmd = Command('ifdown %s' % iface)
            cmd.run()
            cmd.watch_output()

        super().stop_net()


def get_strategy(conf):
    if env.RedhatRelease.version.startswith('6'):
        return Rhel6(conf)
    elif env.RedhatRelease.version.startswith('7'):
        return Rhel7(conf)
    else:
        return Rhel8(conf)
