from unittest import TestCase

from nepta.core.model import system, bundles
from nepta.core.distribution.conf_files import KernelModuleOptions


class ModelTest(TestCase):

    def test_kernel_module_model(self):
        chcr = system.KernelModule('chcr')
        cryptd = system.KernelModule('cryptd', cryptd_max_cpu_qlen=2048)

        self.assertEqual(chcr.options, {})
        self.assertEqual(chcr.name, 'chcr')
        self.assertEqual(cryptd.options, {'cryptd_max_cpu_qlen': 2048})

        b = bundles.Bundle()
        b.chcr = chcr
        b.cryptd = cryptd

        self.assertEqual(len(b.get_subset(m_class=system.KernelModule)), 2)

    def test_kernel_module_conf_files(self):
        b = bundles.Bundle()
        b.chcr = system.KernelModule('chcr')
        b.cryptd = system.KernelModule('cryptd', cryptd_max_cpu_qlen=2048)

        self.assertEqual(KernelModuleOptions(b.chcr).get_content(), '')
        self.assertEqual(KernelModuleOptions(b.chcr).get_path(), '/etc/modprobe.d/chcr.conf')
        self.assertEqual(KernelModuleOptions(b.cryptd).get_content(), 'options cryptd_max_cpu_qlen=2048\n')

