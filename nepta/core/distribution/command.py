import subprocess
import logging

logger = logging.getLogger(__name__)


class Command(object):

    def __init__(self, cmdline, enable_debug_log=True):
        self._cmdline = cmdline.split()
        self._command_handle = None
        self.log_debug = logger.debug if enable_debug_log else lambda *_: None

    def run(self):
        self.log_debug("Running command: %s", self._cmdline)
        self._command_handle = subprocess.Popen(
            self._cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def wait(self):
        self.log_debug('Waiting for command to finish: %s' % self._cmdline)
        self._command_handle.wait()

    def poll(self):
        return self._command_handle.poll()

    def get_output(self):
        out = self._command_handle.stdout.read().decode()
        self._command_handle.wait()
        ret_code = self._command_handle.returncode
        self.log_debug("Command: %s\nOutput: %sReturn code: %s", self._cmdline, out, ret_code)
        return out, ret_code

    def watch_output(self):
        logger.info('Watching output of command: %s', self._cmdline)
        output_buffer = ''

        while self.poll() is None:
            self._command_handle.stdout.flush()
            line = self._command_handle.stdout.readline().decode()
            self.log_debug(line.replace('\n', ''))
            output_buffer += line
        else:  # the end of the cycle
            self._command_handle.stdout.flush()
            line = self._command_handle.stdout.read().decode()
            self.log_debug(line.replace('\n', ''))
            output_buffer += line

        return output_buffer, self.poll()

    def terminate(self):
        self._command_handle.terminate()
