from nepta.core.distribution.command import Command, ShellCommand
from packaging import version

import re
from collections import namedtuple


def split_nevra(nevra_string):
    # Define the NEVRA pattern
    pattern = r'^(?P<name>[\w\-\+\.]+)-(?:(?P<epoch>\d+):)?(?P<version>[\w\-\+\.]+)-(?P<release>[\w\-\+\.]+)\.(?P<arch>[\w\-\+\.]+)$'
    match = re.match(pattern, nevra_string)

    if not match:
        raise ValueError("Invalid NEVRA format")

    # Extract the components, with a default epoch of 0 if it's not specified
    nevra = namedtuple('NEVRA', ['name', 'epoch', 'version', 'release', 'arch'])
    name = match.group('name')
    epoch = int(match.group('epoch')) if match.group('epoch') else 0
    version = match.group('version')
    release = match.group('release')
    arch = match.group('arch')

    return nevra(name, epoch, version, release, arch)


class Tuna:
    NEW_CLI_VERSION = version.parse('0.18-2')

    @staticmethod
    def list_all_irqs():
        cmd_line = 'tuna --show_irqs'
        cmd = Command(cmd_line)
        cmd.run()
        output, _ = cmd.get_output()

        return output

    @staticmethod
    def get_version() -> version.Version:
        rpm_cmd = Command('rpm -qa tuna')
        rpm_cmd.run()
        out, ret_code = rpm_cmd.watch_output()
        nevra = split_nevra(out)
        ver = version.parse('%s-%s' % (nevra.version, nevra.release.split('.')[0]))
        return ver

    @staticmethod
    def get_irq_of_interface(interface):
        cmd_line = 'tuna --show_irqs | grep %s' % interface
        cmd = Command(cmd_line)
        cmd.run()
        all_irq, _ = cmd.get_output()

        output = []
        for i in all_irq.split('\n'):
            if len(i):
                output.append(i.split()[0])
        return output

    @classmethod
    def set_irq_cpu_binding(cls, interface, cpu):
        interface_irq = cls.get_irq_of_interface(interface)
        irqs = ', '.join(interface_irq)

        cmd_line = 'tuna --irqs=%s --cpu=%s --move' % (irqs, cpu)
        cmd = Command(cmd_line)
        cmd.run()
        cmd.get_output()

    @classmethod
    def set_irq_socket_binding(cls, interface, socket):
        interface_irq = cls.get_irq_of_interface(interface)
        irqs = ', '.join(interface_irq)

        cmd_line = 'tuna --irqs=%s --sockets=%s --move' % (irqs, socket)
        cmd = Command(cmd_line)
        cmd.run()
        cmd.get_output()

    @classmethod
    def set_irq_spread_over_cpu_list(cls, interface: str, spread: str, host=None) -> None:
        spread_argument = 'spread' if cls.get_version() >= cls.NEW_CLI_VERSION else '--spread'
        cmd_line = f'tuna {spread_argument} --irqs={interface}\\* --cpus={spread}'
        cmd = ShellCommand(cmd_line, host=host)
        cmd.run()
        cmd.watch_and_log_error()

    @classmethod
    def reset_irq_binding(cls, interface):
        # default socket is 0 , we have to use reset if we want to test TCP, because irq binding fuck it up
        # TODO : using lstopo fin default socket
        cls.set_irq_socket_binding(interface, 0)
