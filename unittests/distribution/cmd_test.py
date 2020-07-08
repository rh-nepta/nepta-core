from unittest import TestCase
from copy import deepcopy

from nepta.core.distribution.command import Command, ShellCommand


class CommandTest(TestCase):
    def test_basic(self):
        cmd = Command(f'echo -n {self.__class__.__name__}')
        cmd.run()
        out, ret = cmd.get_output()
        self.assertEqual(out, self.__class__.__name__)
        self.assertEqual(ret, 0)

    def test_no_bash(self):
        input_str = 'asdf | grep asdf'
        cmd = Command(f'echo -n {input_str}')
        cmd.run()
        out, ret = cmd.get_output()
        self.assertEqual(out, input_str)
        self.assertEqual(ret, 0)

    def test_bash(self):
        input_str = 'asdf | grep asdf'
        cmd = ShellCommand(f'echo -n {input_str}')
        cmd.run()
        out, ret = cmd.get_output()
        self.assertEqual(out.strip(), input_str.split()[-1])
        self.assertEqual(ret, 0)

    def test_deepcopy(self):
        cmd = Command('asdf')
        cmd2 = deepcopy(cmd)
