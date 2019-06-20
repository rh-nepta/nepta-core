import unittest
import os
import shutil

from libres.package import Pacman

from nepta.core.strategies.prepare import Prepare
from nepta.core.strategies.setup import Rhel7
from nepta.core.strategies.run import RunScenarios
from nepta.core.strategies.save.meta import SaveMeta
from nepta.core.strategies.save.attachments import SaveAttachments
from nepta.core.model.bundles import Bundle, HostBundle


class MethCallLogger(object):
    """
    ref.: https://stackoverflow.com/questions/3829742/assert-that-a-method-was-called-in-a-python-unit-test/38834006
    """

    def __init__(self, meth, mockup=False):
        self.meth = meth
        self.mock = mockup
        self.was_called = False

    def __call__(self, *args, **kwargs):
        self.was_called = True
        return self.meth(*args, **kwargs) if not self.mock else None

    @classmethod
    def infect(cls, obj, method, mockup=False):
        mock_method = cls(getattr(obj, method.__name__), mockup)
        setattr(obj, method.__name__, mock_method)

    @classmethod
    def infect_all_public(cls, obj, mockup=False, exclude=None):
        if exclude is None:
            exclude = []
        for meth in [meth for meth in dir(obj) if not meth.startswith('__') and callable(getattr(obj, meth))
                                                  and meth not in exclude]:
            cls.infect(obj, getattr(obj, meth), mockup)


class CallFunctionTest(unittest.TestCase):
    LIBRES_PACKAGE = '/tmp/test/test_call/libres-pacakge'

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.LIBRES_PACKAGE):
            shutil.rmtree(cls.LIBRES_PACKAGE)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.LIBRES_PACKAGE):
            shutil.rmtree(cls.LIBRES_PACKAGE)

    def test_call_with_empty_conf_on_prepare_strategy(self):
        empty_bundle = Bundle()
        prepare = Prepare(empty_bundle)
        MethCallLogger.infect(prepare, prepare.start_docker_container)
        MethCallLogger.infect(prepare, prepare.bind_irq)
        MethCallLogger.infect(prepare, prepare.start_iperf3_services)

        prepare()

        self.assertTrue(prepare.bind_irq.was_called)
        self.assertTrue(prepare.start_docker_container.was_called)
        self.assertTrue(prepare.start_iperf3_services.was_called)

    def test_call_with_empty_conf_on_setup_strategy(self):
        empty_bundle = Bundle()
        setup = Rhel7(empty_bundle)

        MethCallLogger.infect_all_public(setup, True, ['run', 'setup_interfaces', '_instance'])
        MethCallLogger.infect(setup, setup.setup_interfaces)

        setup()

        self.assertTrue(setup.configure_kdump.was_called)
        self.assertTrue(setup.start_net.was_called)
        self.assertTrue(setup.setup_ntp.was_called)
        self.assertTrue(setup.configure_tuned_profile.was_called)
        self.assertTrue(setup.setup_lldpad.was_called)
        self.assertTrue(setup.setup_virtual_guest.was_called)
        self.assertTrue(setup.setup_interfaces.was_called)

    def test_call_empty_bundle_compound_strategy(self):
        empty_bundle = Bundle()
        setup = Rhel7(empty_bundle)
        prepare = Prepare(empty_bundle)

        MethCallLogger.infect(prepare, prepare.start_docker_container)
        MethCallLogger.infect(prepare, prepare.bind_irq)
        MethCallLogger.infect(prepare, prepare.start_iperf3_services)

        MethCallLogger.infect_all_public(setup, True, ['run', 'setup_interfaces', '_instance'])
        MethCallLogger.infect(setup, setup.setup_interfaces)

        final = prepare + setup
        final()

        self.assertTrue(prepare.bind_irq.was_called)
        self.assertTrue(prepare.start_docker_container.was_called)
        self.assertTrue(prepare.start_iperf3_services.was_called)

        self.assertTrue(setup.configure_kdump.was_called)
        self.assertTrue(setup.start_net.was_called)
        self.assertTrue(setup.configure_tuned_profile.was_called)
        self.assertTrue(setup.setup_lldpad.was_called)
        self.assertTrue(setup.setup_virtual_guest.was_called)
        self.assertTrue(setup.setup_interfaces.was_called)

    def test_call_empty_bundle_n_package(self):
        empty_bundle = Bundle()
        libres_package = Pacman.in_path(self.LIBRES_PACKAGE)

        save_attach = SaveAttachments(empty_bundle, libres_package)
        MethCallLogger.infect(save_attach, save_attach.save_attachments)

        save_attach()

        self.assertTrue(save_attach.save_attachments.was_called)

        save_meta = SaveMeta(empty_bundle, libres_package)
        MethCallLogger.infect(save_meta, save_meta.save_meta, True)

        save_meta()

        self.assertTrue(save_meta.save_meta.was_called)

    def test_call_bundle_only_with_bundle_n_package_compound(self):
        empty_bundle = Bundle()
        libres_package = Pacman.in_path("/tmp/package-test").assemble()

        prepare = Prepare(empty_bundle)
        run = RunScenarios(empty_bundle, libres_package)
        save_attach = SaveAttachments(empty_bundle, libres_package)

        MethCallLogger.infect(prepare, prepare.start_docker_container)
        MethCallLogger.infect(prepare, prepare.bind_irq)
        MethCallLogger.infect(prepare, prepare.start_iperf3_services)
        MethCallLogger.infect(run, run.run_scenarios, True)
        MethCallLogger.infect(save_attach, save_attach.save_attachments)

        final = prepare + save_attach
        final()

        self.assertTrue(prepare.bind_irq.was_called)
        self.assertTrue(prepare.start_docker_container.was_called)
        self.assertTrue(prepare.start_iperf3_services.was_called)
        self.assertTrue(save_attach.save_attachments.was_called)

    def test_call_check_if_nonscheduled_R_not_called(self):
        empty_bundle = Bundle()
        setup = Rhel7(empty_bundle)

        # mockup all methods
        MethCallLogger.infect_all_public(setup, True)

        setup()

        # check random scheduled if was call
        self.assertTrue(setup.configure_kdump.was_called)
        # check random non scheduled if was not called
        self.assertFalse(setup.wipe_routes.was_called)

    def test_call_save_meta_check_meta(self):
        bundle = HostBundle("klacek1", "Standard")
        libres_package = Pacman.in_path(self.LIBRES_PACKAGE).assemble()
        libres_package.create()
        meta = {
            'UUID': 741852963,
            'Tag': "wertyui",
            'Specific': "a;lskdjfoiqwe;lrfskdf",
        }

        save_meta = SaveMeta(bundle, libres_package, meta)

        MethCallLogger.infect(save_meta, save_meta.save_meta)

        save_meta()

        self.assertTrue(save_meta.save_meta.was_called)
        for k, v in meta.items():
            self.assertEqual(v, libres_package.meta.root[k])
        self.assertEqual('iperf3', libres_package.meta.root['BenchmarkName'])
        self.assertEqual('net', libres_package.meta.root['Area'])
