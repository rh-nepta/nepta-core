from nepta.core.distribution.command import Command, ShellCommand
from packaging import version

import re
from collections import namedtuple


def split_nevra(nevra_string):
    # Define the NEVRA pattern
    pattern = r"^(?P<name>[\w\-\+\.]+)-(?:(?P<epoch>\d+):)?(?P<version>[\w\-\+\.]+)-(?P<release>[\w\-\+\.]+)\.(?P<arch>[\w\-\+\.]+)$"
    match = re.match(pattern, nevra_string)

    if not match:
        raise ValueError("Invalid NEVRA format")

    # Extract the components, with a default epoch of 0 if it's not specified
    nevra = namedtuple("NEVRA", ["name", "epoch", "version", "release", "arch"])
    name = match.group("name")
    epoch = int(match.group("epoch")) if match.group("epoch") else 0
    version = match.group("version")
    release = match.group("release")
    arch = match.group("arch")

    return nevra(name, epoch, version, release, arch)


class Tuna:
    NEW_CLI_VERSION = version.parse("0.18-2")

    @staticmethod
    def get_version() -> version.Version:
        rpm_cmd = Command("rpm -q tuna")
        rpm_cmd.run()
        out, ret_code = rpm_cmd.watch_output()

        nevra = split_nevra(out)

        ver = version.parse("%s-%s" % (nevra.version, nevra.release.split(".")[0]))

        return ver

    @classmethod
    def is_new_cli(cls) -> bool:
        return cls.get_version() >= cls.NEW_CLI_VERSION

    @classmethod
    def list_all_irqs(cls):
        if cls.is_new_cli():
            cmd_line = "tuna show_irqs"
        else:
            cmd_line = "tuna --show_irqs"

        cmd = Command(cmd_line)
        cmd.run()
        output, _ = cmd.get_output()

        return output

    @classmethod
    def get_irq_of_interface(cls, interface):
        all_irq = cls.list_all_irqs()

        output = []
        for line in all_irq.splitlines():
            if interface in line:
                parts = line.split()
                if parts:
                    output.append(parts[0])

        return output

    @classmethod
    def set_irq_cpu_binding(cls, interface, cpu):
        interface_irq = cls.get_irq_of_interface(interface)

        if not interface_irq:
            raise RuntimeError(f"No IRQs found for interface/pattern: {interface}")

        irqs = ",".join(interface_irq)

        if cls.is_new_cli():
            cmd_line = f"tuna move --irqs={irqs} --cpus={cpu}"
        else:
            cmd_line = f"tuna --irqs={irqs} --cpus={cpu} --move"

        cmd = Command(cmd_line)
        cmd.run()
        cmd.get_output()

    @classmethod
    def set_irq_socket_binding(cls, interface, socket):
        interface_irq = cls.get_irq_of_interface(interface)

        if not interface_irq:
            raise RuntimeError(f"No IRQs found for interface/pattern: {interface}")

        irqs = ",".join(interface_irq)

        if cls.is_new_cli():
            cmd_line = f"tuna move --irqs={irqs} --sockets={socket}"
        else:
            cmd_line = f"tuna --irqs={irqs} --sockets={socket} --move"

        cmd = Command(cmd_line)
        cmd.run()
        cmd.get_output()

    @classmethod
    def set_irq_spread_over_cpu_list(cls, interface: str, spread: str, host=None) -> None:
        irq_pattern = f"{interface}*"

        if cls.is_new_cli():
            cmd_line = f"tuna spread --irqs='{irq_pattern}' --cpus={spread}"
        else:
            cmd_line = f"tuna --irqs='{irq_pattern}' --cpus={spread} --move --spread"

        cmd = ShellCommand(cmd_line, host=host)
        cmd.run()
        cmd.watch_and_log_error()

    @classmethod
    def reset_irq_binding(cls, interface):
        # default socket is 0 , we have to use reset if we want to test TCP, because irq binding fuck it up
        # TODO: use lstopo to find default socket
        cls.set_irq_socket_binding(interface, 0)
