import os
import logging
from collections import defaultdict
from typing import Type

from nepta.core import model
from nepta.core.model.system import SystemService
from nepta.core.distribution import conf_files, env
from nepta.core.distribution.utils.fs import Fs
from nepta.core.distribution.utils.system import SystemD
from nepta.core.distribution.utils.network import IpCommand, LldpTool, OvsVsctl, NmCli
from nepta.core.strategies.setup.generic import _GenericSetup as Setup

logger = logging.getLogger(__name__)


class OldNetwork(Setup):
    def __init__(self, conf):
        super().__init__(conf)
        self.network_service = SystemService('NetworkManager')

    @Setup.schedule
    def stop_net(self):
        for iface in IpCommand.Link.get_all_interfaces():
            NmCli.Con.down(model.network.Interface(iface))
        SystemD.stop_service(self.network_service)

    @Setup.schedule
    def wipe_interfaces_config(self):
        logger.info('Wiping old interfaces configuration')
        wipe_list = []
        ifcfg_dir = conf_files.IfcfgFile.CFG_DIRECTORY
        ifcfg_files = Fs.list_path(ifcfg_dir)
        for f in ifcfg_files:
            if f.startswith('ifcfg-') and not f.startswith('ifcfg-lo'):
                wipe_list.append(os.path.join(ifcfg_dir, f))
        if Fs.path_exists(conf_files.UdevRulesFile.RULES_FILE):
            wipe_list.append(conf_files.UdevRulesFile.RULES_FILE)
        logger.info('Files to be wiped: %s', wipe_list)
        for w in wipe_list:
            Fs.rm_path(w)

    @Setup.schedule
    def wipe_routes(self):
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

    @Setup.schedule
    def setup_udev_rules(self):
        ifaces = self.conf.get_subset(m_class=model.network.EthernetInterface)
        conf_files.UdevRulesFile(ifaces).apply()

    @Setup.schedule
    def rename_ifaces_runtime(self):
        ifaces = self.conf.get_subset(m_class=model.network.EthernetInterface)
        for iface in ifaces:
            old_name = IpCommand.Link.get_interface_name(iface.mac)
            new_name = iface.name
            if old_name is not None and old_name != new_name:
                IpCommand.Link.down_interface(old_name)
                IpCommand.Link.rename_interface(old_name, new_name)
                IpCommand.Link.up_interface(new_name)

    @Setup.schedule
    def store_persistent_cfg(self):
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        for iface in ifaces:
            cf = conf_files.IfcfgFile(iface)
            cf.apply()

    @Setup.schedule
    def setup_routes(self):
        logger.info('Setting up routes')
        for route_class, route_cfg in [
            [model.network.Route4, conf_files.Route4File],
            [model.network.Route6, conf_files.Route6File],
        ]:
            routes = self.conf.get_subset(m_class=route_class)
            routes_per_interface = defaultdict(list)
            for r in routes:
                routes_per_interface[r.interface.name].append(r)

            for int_routes in routes_per_interface.values():
                route_cfg(int_routes).apply()

    @Setup.schedule
    def start_net(self):
        SystemD.start_service(self.network_service)
        NmCli.Con.reload()

        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        for iface in ifaces:
            NmCli.Con.down(iface)
            NmCli.Con.up(iface)

    @Setup.schedule
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

    @Setup.schedule
    def setup_lldpad(self):
        logger.info('Enabling lldp on all ethernet interfaces')
        ethernet_masters = self.conf.get_subset(m_type=model.network.EthernetInterface)
        LldpTool.restart_lldpad()
        LldpTool.enable_on_interfaces(ethernet_masters)
        logger.info(LldpTool.discover_topology(ethernet_masters))


class Crypto(Setup):
    @Setup.schedule
    def delete_old_ipsec_conf(self):
        logging.info('Deleting old ipsec tunnel conf-files')

        if os.path.exists(conf_files.IPsecConnFile.IPSEC_CONF_DIR):
            ls_dir = Fs.list_path(conf_files.IPsecConnFile.IPSEC_CONF_DIR)
            for conn_file in [x for x in ls_dir if x.startswith(conf_files.IPsecConnFile.IPSEC_CONF_PREFIX)]:
                logging.debug('Deleting : {}'.format(conn_file))
                Fs.rm(os.path.join(conf_files.IPsecConnFile.IPSEC_CONF_DIR, conn_file))

    @Setup.schedule
    def setup_ipsec(self):
        logger.info('Setting up ipsec subsystem')
        ipsec_service = model.system.SystemService('ipsec')
        SystemD.stop_service(ipsec_service)

        tuns = self.conf.get_subset(m_class=model.network.IPsecTunnel)
        for tun in tuns:
            conf_files.IPsecConnFile(tun).apply()
            conf_files.IPsecSecretsFile(tun).apply()

        SystemD.start_service(ipsec_service)

    @Setup.schedule
    def delete_old_wireguard_conf(self):
        logging.info('Deleting old wireguard tunnel conf-files')

        if os.path.exists(conf_files.WireGuardConnectionFile.CONF_DIR):
            ls_dir = Fs.list_path(conf_files.WireGuardConnectionFile.CONF_DIR)
            for conn_file in [x for x in ls_dir if x.endswith(conf_files.WireGuardConnectionFile.SUFFIX)]:
                logging.debug('Deleting : {}'.format(conn_file))
                Fs.rm(os.path.join(conf_files.WireGuardConnectionFile.CONF_DIR, conn_file))

    @Setup.schedule
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


class NewNetwork(OldNetwork):
    @Setup.schedule
    def wipe_interfaces_config(self):
        logger.info('Wiping old interfaces configuration')
        wipe_list = []
        cfg_dir = conf_files.NmcliKeyFile.CFG_DIRECTORY
        cfg_files = Fs.list_path(cfg_dir)
        for f in cfg_files:
            if f.endswith(conf_files.NmcliKeyFile.SUFFIX):
                wipe_list.append(os.path.join(cfg_dir, f))
        if Fs.path_exists(conf_files.UdevRulesFile.RULES_FILE):
            wipe_list.append(conf_files.UdevRulesFile.RULES_FILE)
        logger.info('Files to be wiped: %s', wipe_list)
        for w in wipe_list:
            Fs.rm_path(w)

    @Setup.schedule
    def store_persistent_cfg(self):
        ifaces = self.conf.get_subset(m_class=model.network.Interface)
        for iface in ifaces:
            cf = conf_files.NmcliKeyFile(iface)
            cf.apply()

    def setup_routes(self):
        pass

    def wipe_routes(self):
        pass


if (
    env.RedhatRelease.brand == 'Fedora' or env.RedhatRelease.version.startswith('9')
) and env.Environment.conf != 'LinuxBridge':
    Network: Type[Setup] = NewNetwork
else:
    Network = OldNetwork
