import logging
import re

from nepta.core.distribution.command import Command
from nepta.core.model.system import AbstractService

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
                ret_dict[line[:first_double_dot].strip()] = line[first_double_dot+1:].strip()

        return ret_dict

    @staticmethod
    def architecture():
        return Lscpu.parse_output_into_dict()['Architecture']


class SysVInit(object):

    @staticmethod
    def start_service(service):
        logger.info('starting service %s', service)
        c = Command('service %s start' % service)
        c.run()
        c.watch_output()

    @staticmethod
    def stop_service(service):
        logger.info('stopping service %s', service)
        c = Command('service %s stop' % service)
        c.run()
        c.watch_output()

    @staticmethod
    def restart_service(service):
        logger.info('stopping service %s', service)
        c = Command('service %s restart' % service)
        c.run()
        c.watch_output()

    @staticmethod
    def enable_service(service):
        logger.info('enabling service %s', service)
        c = Command('chkconfig %s on' % service)
        c.run()
        c.watch_output()
        pass

    @staticmethod
    def disable_service(service):
        logger.info('disabling service %s', service)
        c = Command('chkconfig %s off' % service)
        c.run()
        c.watch_output()

    @staticmethod
    def is_running(service):
        c = Command('service %s status' % service)
        c.run()
        _, exit_code = c.get_output()
        return exit_code == 0

    @classmethod
    def configure_service(cls, model: AbstractService):
        service_name = model.get_name()
        if model.is_enabled():
            logger.info('configuring service %s to be enabled' % service_name)
            cls.enable_service(service_name)
            if cls.is_running(service_name):
                logger.info('service %s is running at the moment, no further action required' % service_name)
            else:
                logger.info('service %s is not running at the moment, starting' % service_name)
                cls.start_service(service_name)
        else:
            logger.info('configuring service %s to be disabled' % service_name)
            cls.disable_service(service_name)
            if cls.is_running(service_name):
                logger.info('service %s is running at the moment, disabling' % service_name)
                cls.stop_service(service_name)
            else:
                logger.info('service %s is not running at the moment, no further action required' % service_name)
