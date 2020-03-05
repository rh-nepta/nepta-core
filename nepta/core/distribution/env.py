import re
import os

from nepta.core.distribution.utils.system import Uname, RPMTool
from nepta.core.distribution.utils.rstrnt import Rstrnt


class _MetaPrintedType(type):
    def __str__(self):
        return self.__name__ + "\n\t" + "\n\t".join(
            [f"{k} => {v}" for k, v in self.__dict__.items() if not k.startswith('_')])


class RedhatRelease(object, metaclass=_MetaPrintedType):
    _RELEASE_FILE_PATH = '/etc/redhat-release'

    _splitting_regex = r'(.*) (release) (.*) \((.*)\)'
    with open(_RELEASE_FILE_PATH, 'r') as _fd:
        _release_file_content = _fd.read()
    _m = re.match(_splitting_regex, _release_file_content)
    brand = _m.group(1)
    version = _m.group(3)
    codename = _m.group(4)


class Environment(object, metaclass=_MetaPrintedType):
    _env = os.environ
    kernel_version = Uname.get_version()
    kernel_src_rpm = RPMTool.get_src_name('kernel-%s' % kernel_version)
    if not kernel_src_rpm:
        kernel = 'unknown-' + kernel_version
    else:
        _match = re.search(r'(?P<src_name>.+)-(.+)-(.+)\.*\.src\.rpm', kernel_src_rpm)
        kernel = _match.group('src_name') + '-' + kernel_version
    fqdn = Uname.get_hostname()
    distro = _env.get('DISTRO')
    if not distro:
        distro = 'Linux'
    rhel_version = RedhatRelease.version
    hostname = fqdn.split('.')[0]
    whiteboard = _env.get('BEAKER_JOB_WHITEBOARD')
    job_id = _env.get('JOBID')
    arch = _env.get('ARCH')
    in_rhts = 'TEST' in _env.keys()
