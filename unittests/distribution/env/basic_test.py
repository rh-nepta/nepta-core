from unittest import TestCase

from nepta.core.distribution.env import Environment, RedhatRelease


class EnvPrintTest(TestCase):

    def test_print_env(self):
        print(Environment)

    def test_print_rh_release(self):
        print(RedhatRelease)
