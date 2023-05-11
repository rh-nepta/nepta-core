import unittest
import os
import shutil

from nepta import dataformat as df

from nepta.core.strategies.prepare import Prepare
from nepta.core.strategies.setup import get_strategy, SystemSetup, Network
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
        for meth in [
            meth
            for meth in dir(obj)
            if not meth.startswith('__') and callable(getattr(obj, meth)) and meth not in exclude
        ]:
            cls.infect(obj, getattr(obj, meth), mockup)


class CallFunctionTest(unittest.TestCase):
    PACKAGE_PATH = '/tmp/test/test_call/libres-pacakge'

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.PACKAGE_PATH):
            shutil.rmtree(cls.PACKAGE_PATH)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.PACKAGE_PATH):
            shutil.rmtree(cls.PACKAGE_PATH)

    def tearDown(self) -> None:
        if os.path.exists(self.PACKAGE_PATH):
            shutil.rmtree(self.PACKAGE_PATH)

    def test_call_with_empty_conf_on_prepare_strategy(self):
        empty_bundle = Bundle()
        prepare = Prepare(empty_bundle)
        MethCallLogger.infect(prepare, prepare.start_docker_container)
        MethCallLogger.infect(prepare, prepare.start_iperf3_services)
        # MethCallLogger.infect(prepare, prepare.restart_ipsec_service, mockup=True)

        prepare()

        self.assertTrue(prepare.start_docker_container.was_called)
        self.assertTrue(prepare.start_iperf3_services.was_called)

    def test_call_with_empty_conf_on_setup_strategy(self):
        empty_bundle = Bundle()
        setup = SystemSetup(empty_bundle)

        MethCallLogger.infect_all_public(setup, True, ['run', 'setup_interfaces', '_instance'])

        setup()

        self.assertTrue(setup.configure_kdump.was_called)
        self.assertTrue(setup.setup_ntp.was_called)
        self.assertTrue(setup.configure_tuned_profile.was_called)

    def test_call_empty_bundle_compound_strategy(self):
        empty_bundle = Bundle()
        setup = SystemSetup(empty_bundle)
        prepare = Prepare(empty_bundle)

        MethCallLogger.infect(prepare, prepare.start_docker_container)
        MethCallLogger.infect(prepare, prepare.start_iperf3_services)
        # MethCallLogger.infect(prepare, prepare.restart_ipsec_service, mockup=True)

        MethCallLogger.infect_all_public(setup, True, ['run', 'setup_interfaces', '_instance'])

        final = prepare + setup
        final()

        self.assertTrue(prepare.start_docker_container.was_called)
        self.assertTrue(prepare.start_iperf3_services.was_called)

        self.assertTrue(setup.configure_kdump.was_called)
        self.assertTrue(setup.configure_tuned_profile.was_called)

    def test_call_empty_bundle_n_package(self):
        empty_bundle = Bundle()
        package = df.DataPackage.create(self.PACKAGE_PATH)

        save_attach = SaveAttachments(empty_bundle, package)
        MethCallLogger.infect(save_attach, save_attach.save_attachments)

        save_attach()

        self.assertTrue(save_attach.save_attachments.was_called)

        save_meta = SaveMeta(empty_bundle, package)
        MethCallLogger.infect(save_meta, save_meta.save_meta, True)

        save_meta()

        self.assertTrue(save_meta.save_meta.was_called)

    def test_call_bundle_only_with_bundle_n_package_compound(self):
        empty_bundle = Bundle()
        package = df.DataPackage.create(self.PACKAGE_PATH)

        prepare = Prepare(empty_bundle)
        run = RunScenarios(empty_bundle, package)
        save_attach = SaveAttachments(empty_bundle, package)

        MethCallLogger.infect(prepare, prepare.start_docker_container)
        MethCallLogger.infect(prepare, prepare.start_iperf3_services)
        # MethCallLogger.infect(prepare, prepare.restart_ipsec_service, mockup=True)
        MethCallLogger.infect(run, run.run_scenarios, True)
        MethCallLogger.infect(save_attach, save_attach.save_attachments)

        final = prepare + save_attach
        final()

        self.assertTrue(prepare.start_docker_container.was_called)
        self.assertTrue(prepare.start_iperf3_services.was_called)
        self.assertTrue(save_attach.save_attachments.was_called)

    def test_call_save_meta_check_meta(self):
        bundle = HostBundle('klacek1', 'Standard')
        package = df.DataPackage.create(self.PACKAGE_PATH)
        meta = {
            'UUID': 741852963,
            'Tag': 'wertyui',
            'Specific': 'a;lskdjfoiqwe;lrfskdf',
        }

        save_meta = SaveMeta(bundle, package, meta)

        MethCallLogger.infect(save_meta, save_meta.save_meta)

        save_meta()

        self.assertTrue(save_meta.save_meta.was_called)
        for k, v in meta.items():
            self.assertEqual(v, package.metas[k])
        self.assertEqual('iperf3', package.metas['BenchmarkName'])
        self.assertEqual('net', package.metas['Area'])
