import logging
import re
import abc
from enum import Enum

from nepta.core.distribution.command import Command
from nepta.core.model.system import SystemService, TunedAdmProfile, KernelModule

logger = logging.getLogger(__name__)


class Uname(object):
    UNAME_CMD = 'uname -a'

    @classmethod
    def __str__(cls):
        return f"Uname: kernel {cls.get_version()} at {cls.get_hostname()}"

    @classmethod
    def _exec(cls):
        uname_command = Command(cls.UNAME_CMD).run()
        uname_string = uname_command.get_output()[0]
        return uname_string.split()

    @classmethod
    def get_version(cls):
        return cls._exec()[2]

    @classmethod
    def get_hostname(cls):
        return cls._exec()[1]


class RPMTool(object):
    CMD_RPM = '/bin/rpm'

    @classmethod
    def get_src_name(cls, pkg_nvr):
        rpm_cmd = Command('%s -q -i %s' % (cls.CMD_RPM, pkg_nvr))
        rpm_cmd.run()
        out, _ = rpm_cmd.get_output()
        re_match = re.search(r'Source\s+RPM\s*:\s+(?P<all_src_name>.*[^\n])', out, re.MULTILINE)
        if re_match:
            src_name = re_match.group('all_src_name')
            return src_name
        else:
            return None

    @classmethod
    def get_package_version(cls, package):
        rpm_cmd = Command("%s -qa %s" % (cls.CMD_RPM, package))
        rpm_cmd.run()
        out, ret_code = rpm_cmd.watch_output()
        if ret_code == 0 and len(out):
            first_match = out.split()[0]  # strip whitespaces
            #  "kernel-4.18.0-67.el8.x86_64".split("kernel-") -> [[], ['4.18.0-67.el8.x86_64']]
            return first_match.split("%s-" % package)[1]
        else:
            return None


class SELinux(object):

    @staticmethod
    def getenforce():
        cmd = Command('getenforce')
        cmd.run()
        out, ret_code = cmd.get_output()
        out = out.split()[0]  # skipping new line character
        return out

    @staticmethod
    def setenforce(level):
        cmd = Command('setenforce %s' % level)
        cmd.run()
        out, ret_code = cmd.watch_output()
        return out


class Tuned(object):

    @staticmethod
    def set_profile(profile):
        cmd = Command('tuned-adm profile %s' % profile)
        cmd.run()
        return cmd.watch_output()

    @staticmethod
    def get_profile():
        cmd = Command('tuned-adm active')
        cmd.run()
        out, ret = cmd.watch_output()
        if ret:
            return None
        re_match = re.search(r'.*: (.*)\n', out)
        if re_match:
            return re_match.group(1)
        else:
            return None


class Lscpu(object):

    @staticmethod
    def parse_output_into_dict():
        cmd = Command('lscpu')
        ret_dict = {}
        cmd.run()
        out, ret_code = cmd.watch_output()
        for line in out.split('\n'):
            if line:  # skip blank line
                first_double_dot = line.find(':')
                ret_dict[line[:first_double_dot].strip()] = line[first_double_dot + 1:].strip()

        return ret_dict

    @staticmethod
    def architecture():
        return Lscpu.parse_output_into_dict()['Architecture']


class GenericServiceHandler(abc.ABC):
    class Actions(Enum):
        START = 'start'
        STOP = 'stop'
        RESTART = 'restart'
        STATUS = 'status'

    @staticmethod
    @abc.abstractmethod
    def run_service_cmd(action: Actions, service: SystemService) -> (str, int):
        pass

    @classmethod
    def start_service(cls, service: SystemService):
        logger.info('starting service %s', service)
        cls.run_service_cmd(cls.Actions.START, service)

    @classmethod
    def stop_service(cls, service: SystemService):
        logger.info('stopping service %s', service)
        cls.run_service_cmd(cls.Actions.STOP, service)

    @classmethod
    def restart_service(cls, service: SystemService):
        logger.info('restarting service %s', service)
        cls.run_service_cmd(cls.Actions.RESTART, service)

    @staticmethod
    def enable_service(service: SystemService):
        logger.info('enabling service %s', service)
        c = Command('chkconfig %s on' % service.name)
        c.run()
        c.watch_output()

    @staticmethod
    def disable_service(service: SystemService):
        logger.info('disabling service %s', service)
        c = Command('chkconfig %s off' % service.name)
        c.run()
        c.watch_output()

    @classmethod
    def is_running(cls, service: SystemService) -> bool:
        _, exit_code = cls.run_service_cmd(cls.Actions.STATUS, service)
        return not exit_code

    @classmethod
    def configure_service(cls, service: SystemService):
        if service.enable:
            logger.info('configuring service %s to be enabled' % service)
            cls.enable_service(service)
            if cls.is_running(service):
                logger.info('service %s is running at the moment, no further action required' % service)
            else:
                logger.info('service %s is not running at the moment, starting' % service)
                cls.start_service(service)
        else:
            logger.info('configuring service %s to be disabled' % service)
            cls.disable_service(service)
            if cls.is_running(service):
                logger.info('service %s is running at the moment, disabling' % service)
                cls.stop_service(service)
            else:
                logger.info('service %s is not running at the moment, no further action required' % service)


class SysVInit(GenericServiceHandler):
    @staticmethod
    def run_service_cmd(action, service):
        c = Command(f"service {service.name} {action}")
        c.run()
        return c.watch_output()


class SystemD(GenericServiceHandler):
    @staticmethod
    def run_service_cmd(action, service):
        c = Command(f"systemctl {action} {service.name}")
        c.run()
        return c.watch_output()


class KernelModuleUtils:

    @staticmethod
    def modprobe(module: KernelModule):
        opts = " ".join([f"{k}={v}" for k, v in module.options.items()])
        cmd = Command(f"modprobe {module.name} {opts}")
        cmd.run()
        out, ret = cmd.get_output()
        if ret:
            logger.error(f"Error during modprobe module {module.name} with options {module.options}")
