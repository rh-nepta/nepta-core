import os
import sys

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution import components
from nepta.core.model import bundles
from nepta.core.distribution.env import environment


class SaveMeta(Strategy):

    def __init__(self, conf, package, meta=None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.meta = meta if meta is not None else {}

    @Strategy.schedule
    def save_meta(self):
        root = self.package.meta.root
        root.update(self.meta)
        root['TestCase'] = self.conf.conf_name
        root['Kernel'] = environment.kernel
        root['Area'] = 'net'

        root['BenchmarkName'] = 'iperf3'  # TODO : we might have more banchmarks (netperf, iPerf3, etc.)
        root['BenchmarkVersion'] = components.RPMTool.get_package_version('iperf3')
        root['Arguments'] = ' '.join(sys.argv) if len(sys.argv) > 1 else os.environ['NETWORK_PERFTEST_ARGS']
        root['HostName'] = environment.fqdn
        root['OtherHostNames'] = [environment.fqdn]
        root['OtherHostNames'] += [h.hostname for h in self.conf.get_subset(m_class=bundles.SyncHost)]
        root['SELinux'] = components.SELinux.getenforce()

        # FIXME: Where is this used...?
        root['InRHTS'] = str(components.rhts.is_in_rhts())

        if components.rhts.is_in_rhts():
            root['Distribution'] = environment.distro
            root['WhiteBoard'] = components.rhts.whiteboard
            root['BeakerJobID'] = components.rhts.job_id

        # In some special cases, tuned profile is not set (e.g.: Docker) or tuned-adm is not installed
        tuned_profile = components.Tuned.get_profile()
        if tuned_profile:
            root['TunedProfile'] = tuned_profile

        root['Architecture'] = components.Lscpu.architecture()

        version = components.RPMTool.get_package_version('testing-performance-network_perftest')
        devel_version = components.RPMTool.get_package_version('testing-performance-network_perftest-devel')
        if version is not None:
            root['NetworkPerftestVersion'] = version
        elif devel_version is not None:
            root['NetworkPerftestVersion'] = devel_version
