import json
import logging
import abc
import numpy as np
from enum import Enum
from singledispatchmethod import singledispatchmethod
from typing import Dict, Callable, Optional

from nepta.core.distribution.command import Command
from nepta.core.tests.cmd_tool import CommandTool, CommandArgument
from nepta.core.tests.mpstat import MPStat

logger = logging.getLogger(__name__)


class BccProfile(CommandTool):
    """
    BCC profiler tool
    """

    PROGRAM_NAME = " /usr/share/bcc/tools/profile"

    MAPPING = [
        CommandArgument("frequency", "-F", default_value=49),
        CommandArgument("annotations", "-a", argument_type=bool),
        CommandArgument("delimited", "-d", argument_type=bool),
        CommandArgument("folded", "-f", argument_type=bool),
        CommandArgument("duration", "", argument_type=int),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
