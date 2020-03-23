from unittest import TestCase

from nepta.core.model import system, bundles


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
