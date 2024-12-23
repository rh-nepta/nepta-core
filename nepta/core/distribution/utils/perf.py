import logging
import re
import os
import abc
from enum import Enum
from typing import Tuple, Optional

from nepta.core import NEPTA_CORE_DIR
from nepta.core.distribution.command import Command, ShellCommand
from nepta.core.model.system import SystemService, KernelModule, TimeZone

logger = logging.getLogger(__name__)


class Perf:
    FOLD_TMP_FILE = os.path.join('/tmp', 'perf_fold.tmp')
    FOLD_SCRIPT = os.path.join(NEPTA_CORE_DIR, 'scripts', 'perun', 'stackcollapse-perf.pl')

    @classmethod
    def record(cls, command: str, output_file: str, extra_options: Optional[str] = None):
        record_command = ShellCommand(f'perf record {extra_options} -o {output_file} {command}', stderr=None)
        record_command.run()
        return record_command.watch_output()

    @classmethod
    def script(cls, input_file: str, output_file: str):
        script_command = ShellCommand(f'perf script -i {input_file} > {output_file}')
        script_command.run()
        script_command.watch_output()

    @classmethod
    def fold_output(cls, input_file: str, output_file: str):
        cls.script(input_file, cls.FOLD_TMP_FILE)
        fold_command = ShellCommand(f'{cls.FOLD_SCRIPT} {cls.FOLD_TMP_FILE} > {output_file}')
        fold_command.run()
        fold_command.watch_output()
        os.remove(cls.FOLD_TMP_FILE)
