# TODO: remove 'File' from class names
# TODO: remove extra words from constants names: IPSEC_CONF_FILE  => CONF_FILE, etc
# TODO: [ipsec] configure ipsec using network manager and network scripts (this should be possible starting from RHEL-5)

import os
import logging
import json
from jinja2 import Environment, FileSystemLoader
from typing import List
from abc import ABC, abstractmethod

from nepta.core import model
from nepta.core.model import network as net_model
from nepta.core.distribution import env
from nepta.core.distribution.utils.fs import Fs

logger = logging.getLogger(__name__)


class ConfigFile(ABC):
    REWRITE_STRATEGY = 1
    APPEND_STRATEGY = 2

    ACCESS_RIGHTS = 0o755
    STRATEGY = REWRITE_STRATEGY

    def __str__(self):
        type_name_str = self.__class__.__name__
        path_str = self._make_path()
        content_str = self._make_content()

        strategy_str = 'will be written to'
        if self.STRATEGY == self.APPEND_STRATEGY:
            strategy_str = 'will be apended to'

        return '%s, file content %s path: %s,\nFile content:\n%s' % (type_name_str, strategy_str, path_str, content_str)

    @abstractmethod
    def _make_path(self):
        pass

    @abstractmethod
    def _make_content(self):
        pass

    def get_path(self):
        return self._make_path()

    def get_content(self):
        return self._make_content()

    def restore_access_rights(self):
        path_str = self._make_path()
        Fs.chmod_path(path_str, self.ACCESS_RIGHTS)

    def apply(self):
        logger.info('Creating configuration file.\n%s' % str(self))
        path_str = self._make_path()
        content_str = self._make_content()
        if self.STRATEGY == self.REWRITE_STRATEGY:
            Fs.write_to_path(path_str, content_str)
        elif self.STRATEGY == self.APPEND_STRATEGY:
            Fs.append_to_path(path_str, content_str)
        self.restore_access_rights()


class JinjaConfFile(ConfigFile, ABC):
    TEMPLATE: str = ''
    TEMPLATE_DIR: str = 'templates/conf_templates'

    def __init__(self):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), self.TEMPLATE_DIR)
        self.jinja_environment = Environment(
            loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True
        )
        self.template = self.TEMPLATE

    def _make_jinja_context(self):
        raise NotImplementedError

    def _make_content(self):
        return self.jinja_environment.get_template(self.template).render(self._make_jinja_context())


# CAUTION: IPsec configuration
# We do not want to overwrite main IPsec configuration files! These main
# conf. files get sometimes changed with new libreswan/openswan release. We
# want to just add configurations for connections/secrets.
#
# Same thing applies to IPsec secrets files
class GenericIPsecFile(JinjaConfFile, ABC):
    IPSEC_CONF_DIR = '/etc/ipsec.d'
    IPSEC_CONF_PREFIX = 'conn'
    SUFFIX = ''

    def __init__(self, connection: net_model.IPsecTunnel):
        super().__init__()
        self.connection = connection

    def _make_path(self):
        return os.path.join(self.IPSEC_CONF_DIR, f'{self.IPSEC_CONF_PREFIX}_{self.connection.name}.{self.SUFFIX}')


class IPsecConnFile(GenericIPsecFile):
    TEMPLATE = 'ipsec_rhel8_conn.jinja2'
    # Use different ipsec template for RHEL7
    if env.RedhatRelease.version.startswith('7'):
        TEMPLATE = 'ipsec_conn.jinja2'
    SUFFIX = 'conf'

    def _make_jinja_context(self):
        return {
            'name': self.connection.name,
            'family': self.connection.family,
            **self.connection.__dict__,
        }


class IPsecSecretsFile(GenericIPsecFile):
    TEMPLATE = 'ipsec_secret.jinja2'
    SUFFIX = 'secrets'

    def _make_jinja_context(self):
        return {
            'left': self.connection.left_ip.ip,
            'right': self.connection.right_ip.ip,
            'password': self.connection.passphrase,
        }


class WireGuardConnectionFile(JinjaConfFile):
    TEMPLATE = 'wireguard_conn.jinja2'
    CONF_DIR = '/etc/wireguard/'
    SUFFIX = '.conf'

    def __init__(self, connection: net_model.WireGuardTunnel):
        super().__init__()
        self.connection = connection

    def _make_jinja_context(self):
        return self.connection.__dict__

    def _make_path(self):
        return os.path.join(self.CONF_DIR, f'{self.connection.name}{self.SUFFIX}')


class UdevRulesFile(JinjaConfFile):
    RULES_FILE = '/etc/udev/rules.d/70-persistent-net.rules'
    TEMPLATE = 'udev_rule_line.jinja2'

    def __init__(self, interfaces):
        super(UdevRulesFile, self).__init__()
        self._interfaces = interfaces

    def _make_path(self):
        return self.RULES_FILE

    def _make_jinja_context(self):
        return {'interfaces': self._interfaces}


class _NetConfFile(JinjaConfFile, ABC):
    CFG_DIRECTORY: str = '/etc/'
    TEMPLATE_DIR = os.path.join(JinjaConfFile.TEMPLATE_DIR)
    TEMPLATE_MAPPING = {
        net_model.Interface: 'generic.jinja2',
        net_model.EthernetInterface: 'ethernet.jinja2',
        net_model.VlanInterface: 'vlan.jinja2',
        net_model.TeamMasterInterface: 'team_master.jinja2',
        net_model.TeamChildInterface: 'team_slave.jinja2',
        net_model.BondMasterInterface: 'bond_master.jinja2',
        net_model.BondChildInterface: 'bond_slave.jinja2',
        net_model.OVSIntPort: 'ovs_int_port.jinja2',
        net_model.LinuxBridge: 'bridge.jinja2',
        net_model.MACSecInterface: 'macsec.jinja2',
    }

    def __init__(self, interface: net_model.Interface):
        super().__init__()
        self._interface = interface
        self.template = self.TEMPLATE_MAPPING[interface.__class__]

    def _make_jinja_context(self):
        return {'intf': self._interface}


class IfcfgFile(_NetConfFile):
    CFG_DIRECTORY = '/etc/sysconfig/network-scripts/'
    TEMPLATE_DIR = os.path.join(JinjaConfFile.TEMPLATE_DIR, 'ifcfg')

    def _make_path(self):
        file_name = 'ifcfg-%s' % self._interface.name
        file_path = os.path.join(self.CFG_DIRECTORY, file_name)
        return file_path


class NmcliKeyFile(_NetConfFile):
    CFG_DIRECTORY = '/etc/NetworkManager/system-connections/'
    SUFFIX = '.nmconnection'
    ACCESS_RIGHTS = 0o600
    TEMPLATE_DIR = os.path.join(JinjaConfFile.TEMPLATE_DIR, 'nm-keyfiles')

    def _make_path(self):
        file_name = self._interface.name + self.SUFFIX
        file_path = os.path.join(self.CFG_DIRECTORY, file_name)
        return file_path


class SysctlFile(ConfigFile):
    SYSCTL_CONF_FILE = '/etc/sysctl.conf'

    def __init__(self, variables: List[model.system.SysctlVariable]):
        super(SysctlFile, self).__init__()
        self._variables = variables

    def _make_path(self):
        return self.SYSCTL_CONF_FILE

    def _make_content(self):
        conf = ''
        for var in self._variables:
            conf += '%s = %s\n' % (var.key, var.value)
        return conf


class SSHPrivateKey(ConfigFile):
    PRIVATE_KEY_FILENAME = '/root/.ssh/{name}'
    ACCESS_RIGHTS = 0o600

    def __init__(self, identity: model.system.SSHIdentity):
        super(SSHPrivateKey, self).__init__()
        self._identity = identity

    def _make_path(self):
        return self.PRIVATE_KEY_FILENAME.format(name=self._identity.name)

    def _make_content(self):
        return self._identity.private_key


class SSHPublicKey(ConfigFile):
    PUBLIC_KEY_FILENAME = '/root/.ssh/{name}.pub'
    ACCESS_RIGHTS = 0o644

    def __init__(self, identity: model.system.SSHIdentity):
        super(SSHPublicKey, self).__init__()
        self._identity = identity

    def _make_path(self):
        return self.PUBLIC_KEY_FILENAME.format(name=self._identity.name)

    def _make_content(self):
        return self._identity.public_key


class SSHAuthorizedKeysFile(ConfigFile):
    AUTHORIZED_KEYS_FILE = '/root/.ssh/authorized_keys'
    STRATEGY = ConfigFile.APPEND_STRATEGY

    def __init__(self, pubkeys: List[model.system.SSHAuthorizedKey]):
        super(SSHAuthorizedKeysFile, self).__init__()
        self._pubkeys = pubkeys

    def _make_path(self):
        return self.AUTHORIZED_KEYS_FILE

    def _make_content(self):
        return '\n'.join(pk.value for pk in self._pubkeys)


class SSHConfig(ConfigFile):
    CONFIG_FILENAME = '/root/.ssh/config'

    def __init__(self, configs: List[model.system.SSHConfigItem]):
        super(SSHConfig, self).__init__()
        self._configs = configs

    def _make_path(self):
        return self.CONFIG_FILENAME

    def _make_content(self):
        return '\n'.join(['%s %s' % (item.key, item.value) for item in self._configs])


class SSHDConfig(ConfigFile):
    CONFIG_FILENAME = '/etc/ssh/sshd_config'
    STRATEGY = ConfigFile.APPEND_STRATEGY

    def __init__(self, configs: List[model.system.SSHDConfigItem]):
        super().__init__()
        self._configs = configs

    def _make_path(self):
        return self.CONFIG_FILENAME

    def _make_content(self):
        return '\n'.join(['%s %s' % (item.key, item.value) for item in self._configs])


class RcLocalScriptFile(ConfigFile):
    RC_LOCAL_SCRIPT_FILE = '/etc/rc.local'

    def __init__(self, script: model.system.RcLocalScript):
        super(RcLocalScriptFile, self).__init__()
        self._script = script

    def _make_path(self):
        return self.RC_LOCAL_SCRIPT_FILE

    def _make_content(self):
        return self._script.value


class RepositoryFile(JinjaConfFile):
    REPOSITORY_DIRECTORY = '/etc/yum.repos.d/'
    TEMPLATE = 'repo.jinja2'

    def __init__(self, repository: model.system.Repository):
        super().__init__()
        self._repo = repository

    def _make_path(self):
        file_name = '%s.repo' % self._repo.key
        file_path = os.path.join(self.REPOSITORY_DIRECTORY, file_name)
        return file_path

    def _make_jinja_context(self):
        return {'name': self._repo.key, 'url': self._repo.value}


class RouteGenericFile(JinjaConfFile):
    ROUTE_DIRECTORY = '/etc/sysconfig/network-scripts/'
    TEMPLATE = 'route.jinja2'

    def __init__(self, routes: List[net_model.RouteGeneric]):
        super().__init__()
        self._interface = routes[0].interface
        self._routes = routes

    def _make_path(self):
        raise NotImplementedError

    def _make_jinja_context(self):
        return {'routes': self._routes}


class Route4File(RouteGenericFile):
    def _make_path(self):
        file_name = 'route-%s' % self._interface.name
        file_path = os.path.join(self.ROUTE_DIRECTORY, file_name)
        return file_path


class Route6File(RouteGenericFile):
    def _make_path(self):
        file_name = 'route6-%s' % self._interface.name
        file_path = os.path.join(self.ROUTE_DIRECTORY, file_name)
        return file_path


class KDump(ConfigFile):
    CONFIG_FILENAME = '/etc/kdump.conf'

    def __init__(self, opts: List[model.system.KDumpOption]):
        super(KDump, self).__init__()
        self._opts = opts

    def _make_path(self):
        return self.CONFIG_FILENAME

    def _make_content(self):
        return '\n'.join(['%s %s' % (item.key, item.value) for item in self._opts])


class GuestTap(JinjaConfFile):
    FILE_TEMP_DIRECTORY = '/tmp/taps/'
    TEMPLATE_MAPPING = {
        net_model.BridgeGuestTap: 'bridge_tap.jinja2',
        net_model.OVSGuestTap: 'ovs_tap.jinja2',
        net_model.OVSGuestVlanTap: 'ovs_vlan_tap.jinja2',
    }

    def __init__(self, tap: net_model.GenericGuestTap):
        super().__init__()
        self.tap = tap
        self.template = self.TEMPLATE_MAPPING[tap.__class__]

    def _make_path(self):
        file_path = os.path.join(self.FILE_TEMP_DIRECTORY, self.tap.__repr__())
        return file_path

    def _make_jinja_context(self):
        return {'tap': self.tap}


class HostnameConfFile(ConfigFile):
    HOSTNAME_CONF_FILE = '/etc/hostname'

    def __init__(self, hostname: str):
        super().__init__()
        self._hostname = hostname

    def _make_path(self):
        return self.HOSTNAME_CONF_FILE

    def _make_content(self):
        return '%s\n' % self._hostname


class ChronyConf(JinjaConfFile):
    CONFIG_FILENAME = '/etc/chrony.conf'
    TEMPLATE = 'chrony.jinja2'

    def __init__(self, servers: List[model.system.NTPServer]):
        super().__init__()
        self._servers = servers

    def _make_path(self):
        return self.CONFIG_FILENAME

    def _make_jinja_context(self):
        return {'servers': self._servers}


class DockerDaemonJson(ConfigFile):
    DOCKER_DAEMON_FILE = '/etc/docker/daemon.json'

    def __init__(self, settings: model.docker.DockerDaemonSettings):
        super().__init__()
        self._settings = settings

    def _make_path(self):
        return self.DOCKER_DAEMON_FILE

    def _make_content(self):
        return json.dumps(self._settings)

    @property
    def _new_content(self):
        old = self._load_content()
        old.update(self._settings)
        return json.dumps(old)

    def _load_content(self):
        if os.path.exists(self.DOCKER_DAEMON_FILE):
            with open(self.DOCKER_DAEMON_FILE, 'r') as json_file:
                return json.load(json_file)
        else:
            return {}

    def update(self):
        logger.info('Updating docker daemon file')
        logger.info('New content: {}'.format(self._new_content))
        Fs.write_to_path(self._make_path(), self._new_content)


class KernelModuleConf(ConfigFile, ABC):
    CONF_DIR: str = ''

    def __init__(self, mod: model.system.KernelModule):
        super().__init__()
        self.mod = mod

    def _make_path(self):
        return os.path.join(self.CONF_DIR, f'{self.mod.name}.conf')


class KernelLoadModuleConfig(KernelModuleConf):
    CONF_DIR = '/etc/modules-load.d/'

    def _make_content(self):
        return self.mod.name


class KernelModuleOptions(KernelModuleConf, JinjaConfFile):
    CONF_DIR = '/etc/modprobe.d/'
    TEMPLATE = 'kernel_options.jinja2'

    def _make_jinja_context(self):
        return {'mod': self.mod}
