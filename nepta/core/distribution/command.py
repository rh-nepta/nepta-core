import subprocess
import logging

logger = logging.getLogger(__name__)


class Command(object):

    def __init__(self, cmdline, enable_debug_log=True):
        self._cmdline = cmdline
        self._command_handle = None
        self.log_debug = logger.debug if enable_debug_log else lambda *_: None

    def run(self):
        self.log_debug("running command: %s", self._cmdline)
        self._command_handle = subprocess.Popen(self._cmdline + ' 2>&1 ', shell=True, stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)

    def wait(self):
        self.log_debug('Waiting for command to finish: %s' % self._cmdline)
        self._command_handle.wait()

    def poll(self):
        return self._command_handle.poll()

    def get_output(self):
        out = self._command_handle.stdout.read().decode()
        self._command_handle.wait()
        ret_code = self._command_handle.returncode
        self.log_debug("command: %s\nOutput: %sReturn code: %s", self._cmdline, out, ret_code)
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
                self.log_debug(line.replace('\n', ''))
                out += line
        return out, exit_code

    def terminate(self):
        self._command_handle.terminate()
