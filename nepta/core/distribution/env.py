import re
import os
import json
from logging import getLogger

from nepta.core.distribution.utils.system import Uname, RPMTool
from nepta.core.distribution.command import Command

logger = getLogger(__name__)


class _MetaPrintedType(type):
    def __str__(self):
        return (
            self.__name__
            + '\n\t'
            + '\n\t'.join([f'{k} => {v}' for k, v in self.__dict__.items() if not k.startswith('_')])
        )


class RedhatRelease(metaclass=_MetaPrintedType):
    _RELEASE_FILE_PATH = '/etc/redhat-release'

    _splitting_regex = r'(.*) (release) ([0-9\.]*) ?\(?(.*)\)?'
    with open(_RELEASE_FILE_PATH, 'r') as _fd:
        _release_file_content = _fd.read()
    _m = re.match(_splitting_regex, _release_file_content)
    if _m is not None:
        brand = _m.group(1)
        version = _m.group(3)
        codename = _m.group(4)


class Environment(metaclass=_MetaPrintedType):
    _env = os.environ
    kernel_src_rpm = RPMTool.get_src_name_from_file(f'/boot/vmlinuz-{Uname.get_version()}')
    kernel = 'kernel-' + Uname.get_version()
    _match = None
    if kernel_src_rpm:
        _match = re.search(r'(?P<src_name>.+)-(.+)-(.+)\.*\.src\.rpm', kernel_src_rpm)
        if _match is not None:
            kernel = _match.group('src_name') + '-' + Uname.get_version()
    fqdn = Uname.get_hostname()
    distro = _env.get('RSTRNT_OSDISTRO', 'Linux')
    rhel_version = RedhatRelease.version
    hostname = fqdn.split('.')[0]
    whiteboard = _env.get('BEAKER_JOB_WHITEBOARD')
    hub = _env.get('BEAKER_HUB_URL')
    job_id = _env.get('RSTRNT_JOBID')
    recipe_id = _env.get('RSTRNT_RECIPESETID')
    arch = _env.get('RSTRNT_OSARCH')
    lab_controler = _env.get('LAB_CONTROLLER')
    test_name = _env.get('TEST')
    in_rstrnt = test_name is not None

    # TODO: delete WA
    conf = None


class Hardware(metaclass=_MetaPrintedType):
    try:
        with Command('nproc') as _cmd:
            nproc = int(_cmd.watch_output()[0].strip())

        with Command('grep MemTotal /proc/meminfo') as _cmd:
            total_memory = int(_cmd.watch_output()[0].split()[1]) * 1024  # convert to bytes

        with Command('ip -j link') as _cmd:
            interfaces = {x['ifname']: x for x in json.loads(_cmd.watch_output()[0])}
    except FileNotFoundError as e:
        logger.error(e)
