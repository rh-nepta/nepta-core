import os
import logging

from nepta.core import model
from nepta.core.distribution import conf_files, env
from nepta.core.distribution.command import Command
from nepta.core.strategies.setup.generic import _GenericSetup as Setup
from nepta.core.distribution.utils.system import Tuned, KernelModuleUtils, TimeDateCtl, SystemD

logger = logging.getLogger(__name__)


class SystemSetup(Setup):
    @Setup.schedule
    def set_timezone(self):
        zones = self.conf.get_subset(m_class=model.system.TimeZone)
        if len(zones):
            if len(zones) > 1:
                logger.warning(f'Multiple time zones specified! Using {zones[0]}.')
            TimeDateCtl.set_timezone(zones[0])

    @Setup.schedule
    def setup_hostname(self):
        hostname = self.conf.get_hostname()
        logger.info(f'Setting up hostname >> f{hostname}')
        cf = conf_files.HostnameConfFile(hostname)
        cf.apply()
        c = Command(f'hostname -F {cf.get_path()}')
        c.run()
        c.watch_and_log_error()

    @Setup.schedule
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

        confs = self.conf.get_subset(m_class=model.system.SSHDConfigItem)
        conf_files.SSHDConfig(confs).apply()

    # Use /kernel/networking/kdump task instead of configuring KDump in our
    # test framework.
    @Setup.schedule
    def configure_kdump(self):
        logger.info('Configuring KDump')
        confs = self.conf.get_subset(m_class=model.system.KDumpOption)
        conf_files.KDump(confs).apply()

    @Setup.schedule
    def configure_kernel_variables(self):
        logger.info('Configuring sysctl variables')
        kvars = self.conf.get_subset(m_class=model.system.SysctlVariable)
        conf_files.SysctlFile(kvars).apply()
        c = Command('sysctl --system')
        c.run()
        c.watch_output()

    @Setup.schedule
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

    @Setup.schedule
    def configure_services(self):
        for service in self.conf.get_subset(model.system.SystemService):
            SystemD.configure_service(service)

    @Setup.schedule
    def configure_kernel_modules(self):
        logger.info('Configuring kernel modules')
        for mod in self.conf.get_subset(m_class=model.system.KernelModule):
            logger.info(f'Configuring module {mod}')
            conf_files.KernelLoadModuleConfig(mod).apply()
            conf_files.KernelModuleOptions(mod).apply()
            logger.info(f'Inserting module {mod}')
            KernelModuleUtils.modprobe(mod)

    @Setup.schedule
    def generate_pcp_config(self):
        for pcp in self.conf.get_subset(m_type=model.system.PCPConfiguration):
            logger.info(f'Generating PCP configuration: {pcp}')
            if os.path.exists(pcp.config_path):
                logger.info('PCP config already exists >> Deleting ')
                os.remove(pcp.config_path)

            os.makedirs(pcp.log_path, exist_ok=True)
            cmd = Command(f'pmlogconf -c {pcp.config_path}').run()
            out, ret_code = cmd.watch_output()
            if ret_code:
                logger.error(f'PCP cannot generate configuration! Log: {out}')

    @Setup.schedule
    def setup_ntp(self):
        if env.RedhatRelease.version.startswith('6'):
            logger.warning('Skipping NTP configuration!')
            return
        servers = self.conf.get_subset(m_class=model.system.NTPServer)
        conf_files.ChronyConf(servers).apply()
