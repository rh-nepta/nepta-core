import logging
import re

from nepta.core import model
from nepta.core.model.network import Interface
from nepta.core.distribution.command import Command
from nepta.core.distribution.utils.system import Uname, SystemD

logger = logging.getLogger(__name__)


class IpCommand:
    class Link:
        @classmethod
        def get_interface_name(cls, mac):
            mac_regex = r'[0-9]*: (.*):.*\n.*link/ether (%s)' % mac
            link_cmd = Command('ip link')
            link_cmd.run()
            out, _ = link_cmd.get_output()
            m = re.search(mac_regex, out)
            if m is None:
                return m
            return m.group(1)

        @classmethod
        def get_all_interfaces(cls):
            logger.debug('Getting all interfaces')
            link_cmd = Command('ip link')
            link_cmd.run()

            out, _ = link_cmd.get_output()

            return re.findall(r'^[0-9]*: (.*):', out, re.MULTILINE)

        @classmethod
        def rename_interface(cls, old_name, new_name):
            logger.info('renaming interface %s -> %s' % (old_name, new_name))
            link_cmd_line = 'ip link set %s name %s' % (old_name, new_name)
            link_cmd = Command(link_cmd_line)
            link_cmd.run()
            _, retcode = link_cmd.get_output()
            return retcode

        @classmethod
        def down_interface(cls, name):
            logger.info('disabling interface %s' % (name))
            link_cmd_line = 'ip link set %s down ' % (name)
            link_cmd = Command(link_cmd_line)
            link_cmd.run()
            _, retcode = link_cmd.get_output()
            return retcode

        @classmethod
        def up_interface(cls, name):
            logger.info('enabling interface %s' % (name))
            link_cmd_line = 'ip link set %s up ' % (name)
            link_cmd = Command(link_cmd_line)
            link_cmd.run()
            _, retcode = link_cmd.get_output()
            return retcode

    class Xfrm:

        @classmethod
        def state(cls) -> str:
            xfrm_cmd = Command('ip xfrm state')
            xfrm_cmd.run()
            out, _ = xfrm_cmd.get_output()
            return out

        @classmethod
        def number_of_tunnel(cls) -> int:
            tunnel_headers = [x for x in cls.state().split('\n') if x.startswith('src')]
            return len(tunnel_headers)

    class Route:

        @staticmethod
        def get_route_for_ip(ip):
            route_cmd = Command(f'ip route get {ip}')
            route_cmd.run()
            out, _ = route_cmd.get_output()
            return out

        @classmethod
        def get_outgoing_interface(cls, ip):
            # output example: 8.8.8.8 via 10.40.144.254 dev bnx2_0 src 10.40.144.1 uid 0
            route = cls.get_route_for_ip(ip).split(' ')
            return route[route.index('dev') + 1]


class NmCli:
    class Con:
        PREFIX_CMD = 'nmcli con'

        @classmethod
        def up(cls, interface: Interface):
            logger.info(f'Enabling interface {interface}')
            uuid = cls.get_interface_uuid(interface)
            if uuid:
                cmd = Command(f'{cls.PREFIX_CMD} up {uuid}')
                cmd.run().watch_and_log_error()
            else:
                logger.error(f'Cannot find interface uuid: {interface}')

        @classmethod
        def down(cls, interface: Interface):
            logger.info(f'Disabling interface {interface}')
            uuid = cls.get_interface_uuid(interface)
            if uuid:
                cmd = Command(f'{cls.PREFIX_CMD} down {uuid}')
                cmd.run().watch_and_log_error()
            else:
                logger.error(f'Cannot find interface uuid: {interface}')

        @classmethod
        def reload(cls):
            cmd = Command(f'{cls.PREFIX_CMD} reload')
            cmd.run().watch_and_log_error()

        @classmethod
        def show(cls, human_readable=True):
            if human_readable:
                cmd = Command(f'{cls.PREFIX_CMD} show')
            else:
                cmd = Command('nmcli -t con show')
            out = cmd.run().watch_and_log_error()[0]
            return out

        @classmethod
        def get_interface_uuid(cls, interface: Interface):
            for line in cls.show(human_readable=False).strip().split('\n'):
                if len(line.strip()):
                    logger.debug(f'Inspecting line: {line}')
                    try:
                        name, uuid, dev_type, device = line.split(':')
                        name = name.split()[-1]
                        if device == interface.name or name == interface.name:
                            return uuid
                    except ValueError as e:
                        logger.error('Unexpected line. Cannot parse.')
                        logger.error(f'Line: {line}')
                        logger.error(e)
            return None  # explicit notation


class LldpTool:
    LLD_ENABLED_INTERFACE_TYPES = [model.network.EthernetInterface]
    SET_LLDP_CMDS = [
        'lldptool -L -i %s adminStatus=rxtx',
        'lldptool -i %s -T -V portDesc enableTx=yes',
        'lldptool -i %s -T -V sysName enableTx=yes',
        'lldptool -i %s -T -V sysDesc enableTx=yes',
        'lldptool -i %s -T -V sysCap enableTx=yes',
        'lldptool -i %s -T -V mngAddr enableTx=yes',
    ]

    GET_LLDP_CMDS = [
        'lldptool -n -i %s -t -V sysName',
        'lldptool -n -i %s -t -V portDesc',
    ]

    @classmethod
    def _is_enabled(cls, iface):
        return type(iface) in cls.LLD_ENABLED_INTERFACE_TYPES

    @staticmethod
    def restart_lldpad():
        # waitng to be sure if network is up
        from time import sleep

        sleep(5)

        # TODO : make something better
        # Warning: bad_hack
        lldpad = model.system.SystemService('lldpad')
        SystemD.configure_service(lldpad)

    @classmethod
    def enable_on_interfaces(cls, interfaces):
        logger.info('enabling lldp')

        for iface in interfaces:
            if cls._is_enabled(iface):
                logger.info('Setting up lldp for : %s' % iface.name)
                for lldp_cmd in cls.SET_LLDP_CMDS:
                    cmd = Command(lldp_cmd % iface.name)
                    cmd.run()
                    output, ret_val = cmd.get_output()
                    logger.debug(lldp_cmd % iface.name + ' output : %s   return : %s' % (output, ret_val))

    @classmethod
    def discover_topology(cls, interfaces):
        def get_val_from_lldp_output(lldp_out):
            lines = lldp_out.split('\n')
            if len(lines) > 1:
                val = lines[1][1:]
            else:
                val = None
            return val

        logger.info('discovering up lldp topology')

        output_table = []
        mine_hostname = Uname.get_hostname()

        for iface in interfaces:
            if cls._is_enabled(iface):
                iface_values = []
                for cmd in cls.GET_LLDP_CMDS:
                    c = Command(cmd % iface.name)
                    c.run()
                    out, _ = c.get_output()
                    value = get_val_from_lldp_output(out)
                    if value:
                        iface_values.append(value)

                output_table.append([mine_hostname, iface.name, iface_values])

        out_string = 'discovered lldp topology:\n'
        for line in output_table:
            out_string += '%s %s <=connected=> %s \n' % (line[0], line[1], line[2])
        return out_string


class OvsVsctl:
    @staticmethod
    def add_bridge(bridge):
        bridge_name = bridge.name
        logger.info('creating ovs bridge  %s' % bridge_name)
        cmd_line = 'ovs-vsctl add-br %s' % bridge_name
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    @staticmethod
    def dell_bridge(bridge):
        bridge_name = bridge.name
        logger.info('deleting ovs bridge  %s' % bridge_name)
        cmd_line = 'ovs-vsctl del-br %s' % bridge_name
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    @staticmethod
    def add_port(bridge, interface):
        bridge_name = bridge.name
        interface_name = interface.name
        logger.info('adding interface %s to bridge %s' % (interface_name, bridge_name))
        cmd_line = 'ovs-vsctl add-port %s %s' % (bridge_name, interface_name)
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    @staticmethod
    def add_tunnel_port(bridge, tunnel):
        bridge_name = bridge.name
        tunnel_name = tunnel.name
        tunnel_type = tunnel.type
        tunnel_rem_ip = tunnel.remote_ip
        tunnel_key = tunnel.key

        logger.info(
            'adding interface %s to bridge %s, type = %s, remote ip = %s'
            % (tunnel.name, bridge.name, tunnel.type, tunnel.remote_ip)
        )
        cmd_line = 'ovs-vsctl add-port %s %s -- set Interface %s type=%s options:remote_ip=%s options:key=%s' % (
            bridge_name,
            tunnel_name,
            tunnel_name,
            tunnel_type,
            tunnel_rem_ip,
            tunnel_key,
        )
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    @staticmethod
    def dell_port(bridge, interface):
        bridge_name = bridge.get_name()
        interface_name = interface.get_name()
        logger.info('removing interface %s from bridge %s' % (interface_name, bridge_name))
        cmd_line = 'ovs-vsctl del-port %s %s' % (bridge_name, interface_name)
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode


class TcpDump:

    @staticmethod
    def count(expression: str, interface: str = None, timeout: int = None) -> int:
        cmd = f'tcpdump {expression} --count'
        if interface:
            cmd += f' -i {interface}'
        if timeout:
            cmd = f'timeout {timeout} {cmd}'

        cmd = Command(cmd)
        cmd.run()
        out, ret = cmd.get_output()

        for line in out.split('\n'):
            if 'packets captured' in line:
                return int(line.split()[0])
        else:
            raise ValueError('Cannot find packets captured in tcpdump output.')
