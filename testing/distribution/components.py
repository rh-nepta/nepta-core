import os
import logging
import shutil
import subprocess
import re
from testing import model

logger = logging.getLogger(__name__)


class Command(object):

    def __init__(self, cmdline):
        self._cmdline = cmdline
        self._command_handle = None

    def run(self):
        logger.debug("running command: %s", self._cmdline)
        self._command_handle = subprocess.Popen(self._cmdline + ' 2>&1 ', shell=True, stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)

    def wait(self):
        logger.debug('Waiting for command to finish: %s' % self._cmdline)
        self._command_handle.wait()

    def poll(self):
        return self._command_handle.poll()

    def get_output(self):
        out = self._command_handle.stdout.read().decode()
        self._command_handle.wait()
        ret_code = self._command_handle.returncode
        logger.debug("command: %s\nOutput: %sReturn code: %s", self._cmdline, out, ret_code)
        return out, ret_code

    def watch_output(self):
        logger.info('watching output of command: %s', self._cmdline)
        out = ''
        exit_code = None

        cont = True
        while cont:
            exit_code = self._command_handle.poll()
            self._command_handle.stdout.flush()
            line = self._command_handle.stdout.readline()
            if exit_code and line == '':
                line = self._command_handle.stdout.read()
            line = line.decode()
            cont = exit_code is None or len(line) > 0
            if len(line) > 0:
                logger.debug(line.replace('\n', ''))
                out += line
        return (out, exit_code)

    def terminate(self):
        self._command_handle.terminate()


class DistributionComponent(object):
    _all_components = {}

    def __init__(self):
        if self.__class__ in DistributionComponent._all_components.keys():
            raise ValueError(
                "A singleton instantiation already exists!, always use get_instance method for getting singleton instance")
        DistributionComponent._all_components[self.__class__] = self

    @classmethod
    def get_instance(cls):
        if cls not in cls._all_components.keys():
            cls()
        return cls._all_components[cls]


class Fs(DistributionComponent):
    DEBUGGING_PREFIX = None

    # Ref.: https://code.activestate.com/recipes/577257-slugify-make-a-string-usable-in-a-url-or-filename/
    @staticmethod
    def slugify(value):
        """
        Normalizes string, converts to lowercase, removes non-alpha characters,
        and converts spaces to hyphens.

        From Django's "django/template/defaultfilters.py".
        """
        _slugify_strip_re = re.compile(r'[^\w\s-]')
        _slugify_hyphenate_re = re.compile(r'[-\s]+')

        import unicodedata
        if not isinstance(value, str):
            value = str(value)

        value = unicodedata.normalize('NFKD', value)
        value = str(_slugify_strip_re.sub('', value).strip().lower())
        return _slugify_hyphenate_re.sub('-', value)

    def __init__(self):
        super(Fs, self).__init__()

    def read(self, path):
        full_path = self._apply_debug_prefix(path)
        with open(full_path, 'r') as fd:
            return fd.read()

    def write(self, path, content):
        full_path = self._apply_debug_prefix(path)
        with open(full_path, 'w') as fd:
            fd.write(content)
            fd.flush()

    def append(self, path, content):
        full_path = self._apply_debug_prefix(path)
        with open(full_path, 'a') as fd:
            fd.write(content)
            fd.flush()

    def copy(self, src, dst):
        full_src = self._apply_debug_prefix(src)
        full_dst = self._apply_debug_prefix(dst)
        shutil.copy(full_src, full_dst)
        logger.debug('copying file %s > %s', full_src, full_dst)
        self.get_instance().restore_path_context(full_dst)

    def rm(self, path):
        full_path = self._apply_debug_prefix(path)
        logger.debug('removing file :\t%s', full_path)
        os.remove(full_path)

    def mkdir(self, path):
        full_path = self._apply_debug_prefix(path)
        logger.debug('creating directory :\t %s', full_path)
        os.makedirs(full_path)

    def copy_dir(self, src, dst):
        full_src = self._apply_debug_prefix(src)
        full_dst = self._apply_debug_prefix(dst)
        shutil.copytree(full_src, full_dst)
        logger.debug('copying directory %s > %s', full_src, full_dst)
        self.get_instance().restore_path_context(dst)

    def rmdir(self, path):
        full_path = self._apply_debug_prefix(path)
        logger.debug('removing directory :\t%s', full_path)
        shutil.rmtree(full_path)

    def is_file(self, path):
        full_path = self._apply_debug_prefix(path)
        return os.path.isfile(full_path)

    def is_dir(self, path):
        full_path = self._apply_debug_prefix(path)
        return os.path.isdir(full_path)

    def path_exists(self, path):
        full_path = self._apply_debug_prefix(path)
        return os.path.exists(full_path)

    def list_path(self, path):
        full_src_path = self._apply_debug_prefix(path)
        return os.listdir(full_src_path)

    def write_to_path(self, path, content):
        dirname, _ = os.path.split(path)
        if not self.path_exists(dirname):
            self.mkdir(dirname)
            # if calling other self. method use original name, or path. Debug prefix will be appended in stub method
        logger.debug('writing file name: %s\ncontent:\n%s', self._full_path_str(path), content)
        self.write(path, content)
        self.restore_path_context(path)

    def append_to_path(self, path, content):
        if not self.path_exists(path):
            logger.debug('file %s does not exists, will create new one', self._full_path_str(path))
            self.write_to_path(path, content)
        else:
            already_contain = self.read(path).find(content) >= 0
            if not already_contain:
                logger.debug('required content does not exists in file, appending')
                self.append(path, content)
            else:
                logger.debug('required content is already in file. No action taken')

    def copy_path(self, src_path, dst_path):
        full_src_path = self._apply_debug_prefix(src_path)
        if not self.path_exists(src_path):
            raise ValueError('path %s does not exists' % full_src_path)
        elif self.is_file(src_path):
            self.copy(src_path, dst_path)
        elif self.is_dir(src_path):
            self.copy_dir(src_path, dst_path)
        else:
            raise EnvironmentError

    def rm_path(self, path):
        full_src_path = self._apply_debug_prefix(path)
        if not self.path_exists(path):
            raise ValueError('path %s does not exists' % full_src_path)
        elif self.is_file(path):
            self.rm(path)
        elif self.is_dir(path):
            self.rmdir(path)

    def chmod_path(self, path, mode=0o0755):
        full_path = self._apply_debug_prefix(path)
        logger.debug('chmodding path %s to %o', full_path, mode)
        os.chmod(full_path, mode)

    def restore_path_context(self, path):
        full_path = self._apply_debug_prefix(path)
        logger.debug('restoring security context : %s', full_path)
        c = Command('restorecon -FvvR %s' % full_path)
        c.run()
        c.wait()

    def _full_path_str(self, path):
        return self._apply_debug_prefix(path)

    def _apply_debug_prefix(self, path):
        if not Fs.DEBUGGING_PREFIX:
            return path
        else:
            return os.path.join(Fs.DEBUGGING_PREFIX, path[1:])  # strip first /

    def __str__(self):
        return 'Distribution filesystem component, debugging prefix set to %s' % Fs.DEBUGGING_PREFIX

    @staticmethod
    def set_debug_prefix(prefix):
        logger.debug('setting debugging prefix to : %s', prefix)
        Fs.DEBUGGING_PREFIX = prefix


class Uname(DistributionComponent):
    UNAME_CMD = 'uname -a'

    def __init__(self):
        super(Uname, self).__init__()
        uname_command = Command(self.UNAME_CMD)
        uname_command.run()
        uname_string = uname_command.watch_output()[0]
        uname_string_parts = uname_string.split()
        self._version = uname_string_parts[2]
        self._hostname = uname_string_parts[1]

    def __str__(self):
        return 'Uname: kernel %s at %s' % (self._version, self._hostname)

    def get_version(self):
        return self._version

    def get_hostname(self):
        return self._hostname


class RPMTool(DistributionComponent):
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


class LldpTool(DistributionComponent):
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
        lldpad = model.system.SystemdService('lldpad', model.system.AbstractService.ENABLED)
        sysvinit.configure_service(lldpad)

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
        mine_hostname = uname.get_hostname()

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


class SysVInit(DistributionComponent):

    def __init__(self):
        super(SysVInit, self).__init__()

    def start_service(self, service):
        logger.info('starting service %s', service)
        c = Command('service %s start' % service)
        c.run()
        c.watch_output()

    def stop_service(self, service):
        logger.info('stopping service %s', service)
        c = Command('service %s stop' % service)
        c.run()
        c.watch_output()

    def restart_service(self, service):
        logger.info('stopping service %s', service)
        c = Command('service %s restart' % service)
        c.run()
        c.watch_output()

    def enable_service(self, service):
        logger.info('enabling service %s', service)
        c = Command('chkconfig %s on' % service)
        c.run()
        c.watch_output()
        pass

    def disable_service(self, service):
        logger.info('disabling service %s', service)
        c = Command('chkconfig %s off' % service)
        c.run()
        c.watch_output()

    def is_running(self, service):
        c = Command('service %s status' % service)
        c.run()
        _, exit_code = c.get_output()
        return exit_code == 0

    def configure_service(self, model):
        service_name = model.get_name()
        if model.is_enabled():
            logger.info('configuring service %s to be enabled' % service_name)
            self.enable_service(service_name)
            if self.is_running(service_name):
                logger.info('service %s is running at the moment, no further action required' % service_name)
            else:
                logger.info('service %s is not running at the moment, starting' % service_name)
                self.start_service(service_name)
        else:
            logger.info('configuring service %s to be disabled' % service_name)
            self.disable_service(service_name)
            if self.is_running(service_name):
                logger.info('service %s is running at the moment, disabling' % service_name)
                self.stop_service(service_name)
            else:
                logger.info('service %s is not running at the moment, no further action required' % service_name)


class IpCommand(DistributionComponent):
    class Link(object):

        def __init__(self):
            pass

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
            logger.debug("Getting all interfaces")
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

    def __init__(self):
        super(IpCommand, self).__init__()
        self.link = IpCommand.Link()


class Rhts(DistributionComponent):

    def __init__(self):
        super(Rhts, self).__init__()
        self._env = os.environ

    def is_in_rhts(self):
        return 'TEST' in self._env.keys()

    @property
    def whiteboard(self):
        if 'BEAKER_JOB_WHITEBOARD' in self._env:
            return self._env['BEAKER_JOB_WHITEBOARD']

    @property
    def job_id(self):
        if 'JOBID' in self._env:
            return self._env['JOBID']

    @property
    def arch(self):
        if 'ARCH' in self._env:
            return self._env['ARCH']

    def get_distro(self):
        if 'DISTRO' in self._env:
            return self._env['DISTRO']

    def report_result(self, success=True, filename='/dev/null'):
        if not self.is_in_rhts():
            return
        logger.info('reporting rhts results: %s filename: %s', success, filename)

        result_string = ''
        if success:
            result_string = 'PASS'
        else:
            result_string = 'FAILS'

        c = Command('rhts-report-result %s %s %s' % (self._env['TEST'], result_string, filename))
        c.run()
        c.watch_output()

        if 'RECIPETESTID' in self._env.keys() and 'RESULT_SERVER' in self._env.keys():
            # FIXME: call self.submit_log here
            # FIXME: -T and -S are deprecated when using restraint harness!
            c2 = Command(
                'rhts-submit-log -T %s -S %s -l %s' % (self._env['RECIPETESTID'], self._env['RESULT_SERVER'], filename))
            c2.run()
            c2.watch_output()

    def submit_log(self, filename):
        if not self.is_in_rhts():
            return

        logger.info('submiting log using rhts: %s', filename)

        c = Command('rhts-submit-log -l %s' % filename)
        c.run()
        c.watch_output()

    def sync_set(self, state):
        logger.info('rhts synchronization: setting synchronization state: %s', state)
        c = Command('rhts-sync-set -s %s' % state)
        c.run()
        c.watch_output()

    def sync_block(self, states, hosts):
        logger.info('rhts synchronization: waiting for all hosts: %s to be in one of %s states', hosts, states)
        hosts_list = ' '.join(hosts)
        states_list = ' -s '.join([''] + states)
        c = Command('rhts-sync-block %s %s' % (states_list, hosts_list))
        c.run()
        c.watch_output()


class Virsh(DistributionComponent):

    def __init__(self):
        super(Virsh, self).__init__()

    def attach_device(self, guest, dfile, persistent=True):
        guest_name = guest.get_name()
        logger.info('Attaching device specified in %s to guest %s', guest_name, dfile)
        cmd = 'virsh attach-device %s %s' % (guest_name, dfile)
        if persistent:
            cmd += ' --persistent'
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        return retcode

    def domiflist(self, guest):
        guest_name = guest.get_name()
        cmd = 'virsh domiflist %s' % guest_name
        c = Command(cmd)
        c.run()
        out, _ = c.get_output()
        out_lines = out.split('\n')
        out_lines = out_lines[2:-2]
        ret = []
        for line in out_lines:
            parts = line.split()
            ret.append(
                {'interface': parts[0], 'type': parts[1], 'source': parts[2], 'model': parts[3], 'mac': parts[4]})
        return ret

    def detach_interface(self, guest, itype, mac, persistent=True):
        guest_name = guest.get_name()
        logger.info('Detaching interface type %s with mac %s from guest %s', guest_name, itype, mac)
        cmd = 'virsh detach-interface %s %s' % (guest_name, itype)
        if mac:
            cmd += ' --mac %s' % mac
        if persistent:
            cmd += ' --persistent'
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        return retcode

    def set_persistent_max_cpus(self, guest):
        guest_name = guest.get_name()
        num_of_cpus = guest.get_cpu_count()
        logger.info('Setting persistent maximum cpus : %s on guest %s' % (num_of_cpus, guest_name))
        cmd = 'virsh setvcpus %s %s --config --maximum' % (guest_name, num_of_cpus)
        c = Command(cmd)
        c.run()
        _, retcode = c.get_output()
        assert not retcode
        return retcode

    def set_cpus(self, guest):
        guest_name = guest.get_name()
        num_of_cpus = guest.get_cpu_count()
        logger.info('Setting number of cpus : %s on guest %s' % (num_of_cpus, guest_name))
        cmd_config = 'virsh setvcpus %s %s --config' % (guest_name, num_of_cpus)
        cmd_live = 'virsh setvcpus %s %s --live' % (guest_name, num_of_cpus)
        c_conf = Command(cmd_config)
        c_live = Command(cmd_live)
        c_conf.run()
        c_live.run()

        _, ret_conf = c_conf.get_output()
        _, ret_live = c_live.get_output()
        assert not ret_conf
        return ret_conf and ret_live

    def set_persistent_max_mem(self, guest):
        guest_name = guest.get_name()
        mem_size = guest.get_mem_size() * 1024  # conversion from MB to Kb because of virsh
        logger.info('Setting persistent maximum memory size : %s kB on guest %s' % (mem_size, guest_name))
        cmd = 'virsh setmaxmem %s %s --config' % (guest_name, mem_size)
        c = Command(cmd)
        c.run()
        output, retcode = c.get_output()
        assert not retcode
        return retcode

    def set_mem(self, guest):
        guest_name = guest.get_name()
        mem_size = guest.get_mem_size() * 1024  # conversion from MB to Kb because of virsh
        logger.info('Setting allocated memory : %s kB on guest %s' % (mem_size, guest_name))
        cmd_config = 'virsh setmem %s %s --config' % (guest_name, mem_size)
        cmd_live = 'virsh setmem %s %s --live' % (guest_name, mem_size)
        c_conf = Command(cmd_config)
        c_live = Command(cmd_live)

        c_conf.run()
        c_live.run()

        _, ret_conf = c_conf.get_output()
        _, ret_live = c_live.get_output()
        assert not ret_conf
        return ret_conf and ret_live

    def set_cpu_pinning(self, guest):
        return_value = False
        guest_name = guest.get_name()
        cpu_pinning = guest.get_cpu_pinning()
        logger.info('Setting cpu pinning %s on guest %s' % (cpu_pinning, guest_name))
        if cpu_pinning:
            for real, virtual in cpu_pinning:
                logger.info('%s >> real cpu : %s , virtual cpu : %s' % (guest_name, real, virtual))
                cmd_conf = 'virsh vcpupin %s %s %s --config' % (guest_name, virtual, real)
                cmd_live = 'virsh vcpupin %s %s %s --live' % (guest_name, virtual, real)
                c_conf = Command(cmd_conf)
                c_live = Command(cmd_live)
                c_conf.run()
                c_live.run()
                _, ret_conf = c_conf.get_output()
                _, ret_live = c_live.get_output()
                assert not ret_conf
                return_value = ret_conf or ret_live or return_value
        return return_value

    def destroy(self, guest):
        guest_name = guest.get_name()
        logger.info('Destroying guest : %s!' % guest_name)
        cmd = 'virsh destroy %s' % guest_name
        c = Command(cmd)
        c.run()
        output, return_code = c.get_output()
        if return_code:
            logger.warning(output)
        else:
            logger.info(output)
        return return_code

    def start(self, guest):
        guest_name = guest.get_name()
        logger.info('Starting guest %s!' % guest_name)
        cmd = 'virsh start %s' % guest_name
        c = Command(cmd)
        c.run()
        output, return_code = c.get_output()
        if return_code:
            logger.error("Virsh >> %s" % output)
        else:
            logger.info("Virsh >> %s" % output)
        return return_code


class Ovs_vsctl(DistributionComponent):

    def __init__(self):
        super(Ovs_vsctl, self).__init__()

    def add_bridge(self, bridge):
        bridge_name = bridge.name
        logger.info('creating ovs bridge  %s' % bridge_name)
        cmd_line = 'ovs-vsctl add-br %s' % bridge_name
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    def dell_bridge(self, bridge):
        bridge_name = bridge.name
        logger.info('deleting ovs bridge  %s' % bridge_name)
        cmd_line = 'ovs-vsctl del-br %s' % bridge_name
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    def add_port(self, bridge, interface):
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

    def add_tunnel_port(self, bridge, tunnel):
        bridge_name = bridge.name
        tunnel_name = tunnel.name
        tunnel_type = tunnel.type
        tunnel_rem_ip = tunnel.remote_ip
        tunnel_key = tunnel.key

        logger.info('adding interface %s to bridge %s, type = %s, remote ip = %s'
                    % (tunnel.name, bridge.name, tunnel.type, tunnel.remote_ip))
        cmd_line = 'ovs-vsctl add-port %s %s -- set Interface %s type=%s options:remote_ip=%s options:key=%s' \
                   % (bridge_name, tunnel_name, tunnel_name, tunnel_type, tunnel_rem_ip, tunnel_key)
        cmd = Command(cmd_line)
        cmd.run()
        output, retcode = cmd.get_output()
        if retcode:
            logger.error(output)
        return retcode

    def dell_port(self, bridge, interface):
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


class Tuna(DistributionComponent):

    def __init__(self):
        super(Tuna, self).__init__()

    def list_all_irqs(self):
        cmd_line = "tuna --show_irqs"
        cmd = Command(cmd_line)
        cmd.run()
        output, _ = cmd.get_output()

        return output

    def get_irq_of_interface(self, interface):
        cmd_line = "tuna --show_irqs | grep %s" % interface
        cmd = Command(cmd_line)
        cmd.run()
        all_irq, _ = cmd.get_output()

        output = []
        for i in all_irq.split('\n'):
            if len(i):
                output.append(i.split()[0])
        return output

    def set_irq_cpu_binding(self, interface, cpu):
        interface_irq = self.get_irq_of_interface(interface)
        irqs = ""

        for irq in interface_irq:
            irqs += irq + ","

        cmd_line = "tuna --irqs=%s --cpu=%s --move" % (irqs, cpu)
        cmd = Command(cmd_line)
        cmd.run()
        cmd.get_output()

    def set_irq_socket_binding(self, interface, socket):
        interface_irq = self.get_irq_of_interface(interface)
        irqs = ""

        for irq in interface_irq:
            irqs += irq + ","

        cmd_line = "tuna --irqs=%s --sockets=%s --move" % (irqs, socket)
        cmd = Command(cmd_line)
        cmd.run()
        cmd.get_output()

    def reset_irq_binding(self, interface):
        # default socket is 0 , we have to use reset if we want to test TCP, because irq binding fuck it up
        # TODO : using lstopo fin default socket
        self.set_irq_socket_binding(interface, 0)


class Docker(DistributionComponent):
    CMD = 'docker'

    class Network(object):
        CMD = 'network'

        @staticmethod
        def create(network):
            cmd_prototype = '{} {} create'.format(Docker.CMD, Docker.Network.CMD)
            if network.v4:
                cmd_prototype += ' --subnet {} --gateway {}'.format(network.v4, network.v4.gw_ip)
            if network.v6:
                cmd_prototype += ' --ipv6 --subnet {} --gateway {}'.format(network.v6, network.v6.gw_ip)
            cmd_prototype += ' ' + network.name

            cmd = Command(cmd_prototype)
            cmd.run()
            out, retcode = cmd.watch_output()
            if retcode:
                logger.error(out)

    class Volume(object):
        CMD = 'volume'

        @staticmethod
        def create(volume):
            cmd_protype = '{} {} create {}'.format(Docker.CMD, Docker.Volume.CMD, volume.name)
            cmd = Command(cmd_protype)
            cmd.run()
            out, retcode = cmd.watch_output()
            if retcode:
                logger.error(out)

    def __init__(self):
        super(Docker, self).__init__()
        self.network = Docker.Network()
        self.volume = Docker.Volume()

    @staticmethod
    def build(image):
        cmd_prototype = '{} build {} -f {} -t {}'.format(Docker.CMD, image.context, image.dockerfile, image.name)
        cmd = Command(cmd_prototype)
        cmd.run()
        out, retcode = cmd.watch_output()
        if retcode:
            logger.error(out)

    @staticmethod
    def run(container, inherit_arguments_from_master_proc=True):
        cmd_prototype = '{} run'.format(Docker.CMD)
        if container.hostname:
            cmd_prototype += ' -h {}'.format(container.hostname)
        if container.network:
            cmd_prototype += ' --network {}'.format(container.network.name)
        if container.volumes:
            for vol in container.volumes:
                cmd_prototype += ' --volume {}:/{}'.format(vol.name, vol.name)
        if container.v4_conf:
            cmd_prototype += ' --ip {}'.format(container.v4_conf.addresses[0].ip)
        if container.v6_conf:
            cmd_prototype += ' --ip6 {}'.format(container.v6_conf.addresses[0].ip)

        if container.inherit_env:
            for env_var in container.inherit_env:
                cmd_prototype += ' -e {}'.format(env_var)

        cmd_prototype += ' ' + container.image.name

        if inherit_arguments_from_master_proc:
            import sys
            if len(sys.argv) > 1:
                cmd_prototype += ' ' + ' '.join(sys.argv[1:])
            else:
                cmd_prototype += ' ' + os.environ['NETWORK_PERFTEST_ARGS']

        if container.extra_arguments:
            cmd_prototype += container.extra_arguments

        cmd = Command(cmd_prototype)
        cmd.run()
        out, ret_code = cmd.watch_output()
        if ret_code:
            logger.error(out)


class SELinux(DistributionComponent):

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


class Tuned(DistributionComponent):

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


class Lscpu(DistributionComponent):

    @staticmethod
    def parse_output_into_dict():
        cmd = Command('lscpu')
        ret_dict = {}
        cmd.run()
        out, ret_code = cmd.watch_output()
        for line in out.split('\n'):
            if line:  # skip blank line
                key, val = line.split(':')
                ret_dict[key.strip()] = val.strip()

        return ret_dict

    @staticmethod
    def architecture():
        return Lscpu.parse_output_into_dict()['Architecture']


class Attero(DistributionComponent):

    MaxAttempts = 5

    @staticmethod
    def clear_existing_impairments():
        logger.info("Clearing Attero existing configuration.")
        from pyattero import attero
        controler = attero.Control()
        controler.conn()
        controler.clear_impairments()
        controler.configure()
        controler.end()

    @staticmethod
    def set_delay_and_bottleneck_bandwidth(direction, delay, bandwidth):
        i = 0
        while True:
            try:
                Attero.set_delay(direction, delay)
                Attero.set_bandwidth(direction, bandwidth)
            except Exception as e:
                logger.error("Attero cannot set impairments [delay: %s, bandwidth: %s, attempt: %s]" % (delay, bandwidth, i))
                logger.error(e)
                i += 1
                if i >= Attero.MaxAttempts:
                    raise e
            else:
                break

    @staticmethod
    def set_delay(direction, delay):
        logger.info("Setting Attero to create a delay of %s ms in %s direction." % (delay, direction))
        from pyattero import attero, options
        controller = attero.Control()
        controller.conn()
        flow_option = options.Flow(direction)
        flow_option.set_option(options.Latency(delay))
        controller.set_option(flow_option)
        controller.configure()
        controller.end()

    @staticmethod
    def set_bandwidth(direction, bandwidth):
        logger.info("Setting Attero to create a bottleneck of %s kbps in %s direction." % (bandwidth, direction))
        from pyattero import attero, options
        controller = attero.Control()
        controller.conn()
        flow_option = options.Flow(direction)
        flow_option.set_option(options.Bandwidth(bandwidth))
        controller.set_option(flow_option)
        controller.configure()
        controller.end()

    @staticmethod
    def start():
        from pyattero import attero
        controller = attero.Control()
        controller.conn()
        controller.start()
        controller.end()

    @staticmethod
    def stop():
        from pyattero import attero
        controller = attero.Control()
        controller.conn()
        controller.stop()
        controller.end()


fs = Fs.get_instance()
uname = Uname.get_instance()
lldptool = LldpTool.get_instance()
sysvinit = SysVInit.get_instance()
ip = IpCommand.get_instance()
rhts = Rhts.get_instance()
ovs_vsctl = Ovs_vsctl.get_instance()
virsh = Virsh.get_instance()
rpmtool = RPMTool.get_instance()
tuna = Tuna.get_instance()
docker = Docker.get_instance()
selinux = SELinux.get_instance()
tuned = Tuned.get_instance()
lscpu = Lscpu.get_instance()
attero = Attero.get_instance()
