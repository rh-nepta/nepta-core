import subprocess
import logging

logger = logging.getLogger(__name__)


class Command(object):
    """
    This object abstracts an execution of shell command. It uses the subprocess library to fork a system process
    and transfers stdout and stderr using subprocess.PIPE.

    Usage:
        -> cmd = Command('tuned-adm active')
        -> cmd.run()
        -> out, ret_code = cmd.get_output()
    """

    def __init__(self, cmdline, enable_debug_log=True, host=None):
        if host is not None:
            cmdline = f'ssh -o LogLevel=ERROR {host} {cmdline}'

        self._cmdline = cmdline.split()
        self._command_handle = None
        self.enable_debug = enable_debug_log

    def __str__(self):
        return '{cls}: {cmd}'.format(cls=self.__class__.__name__, cmd=self._cmd_str())

    def __enter__(self):
        self.run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.poll() is None:
            logger.warning(f'Killing process {self}!')
            self.terminate()

    def log_debug(self, *args, **kwargs):
        if self.enable_debug:
            logger.debug(*args, **kwargs)

    def _cmd_str(self):
        return ' '.join(self._cmdline)

    def run(self):
        self.log_debug('Running %s', self)
        self._command_handle = subprocess.Popen(self._cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return self

    def wait(self):
        self.log_debug(f'Waiting to finish: {self}')
        self._command_handle.wait()
        return self

    def poll(self):
        return self._command_handle.poll()

    def _read_line_from_pipe(self):
        self._command_handle.stdout.flush()
        return self._command_handle.stdout.readline().decode()

    def _read_whole_pipe(self):
        self._command_handle.stdout.flush()
        return self._command_handle.stdout.read().decode()

    def get_output(self):
        """
        Do not read output as whole block. Output has to be read line by line due to buffer over fill. To see problem
        explanation see references below.

        [0] https://docs.python.org/3/library/subprocess.html#subprocess.Popen.stderr
        [1] https://stackoverflow.com/questions/48161117/subprocess-calling-rsync-hangs-after-possible-buffer-fill
        :return: output, return code
        """
        return self.watch_output()

    def watch_output(self):
        """
        This method continuously logs an output generated by the executed command.
        :return: command output and return code
        """
        logger.info(f'Watching output of >> {self}')
        output_buffer = ''

        while self.poll() is None:
            line = self._read_line_from_pipe()
            self.log_debug(line.replace('\n', ''))
            output_buffer += line
        else:  # the end of the cycle
            line = self._read_whole_pipe()
            self.log_debug(line.replace('\n', ''))
            output_buffer += line

        return output_buffer, self.poll()

    def terminate(self):
        self._command_handle.terminate()

    def watch_and_log_error(self):
        out, ret_code = self.watch_output()
        if ret_code:
            logger.error(out)
        return out, ret_code


class ShellCommand(Command):
    """
    This class extends behaviour of Command class. It executes provided command inside unix shell environment, which
    is necessary for command with unix pipes or other shell utilities.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cmdline = ' '.join(self._cmdline)

    def _cmd_str(self):
        return self._cmdline

    def run(self):
        self.log_debug('Running command: %s', self._cmdline)
        self._command_handle = subprocess.Popen(
            self._cmdline, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        )
        return self
