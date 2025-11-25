import logging
from typing import Optional

from nepta.dataformat import DataPackage
from nepta.core.strategies.generic import Strategy
from nepta.core.model.bundles import SyncHost, HostBundle
from nepta.core.distribution.env import Environment
from nepta.core.distribution.utils.system import SELinux, RPMTool, Tuned, Lscpu

logger = logging.getLogger(__name__)


class SaveMeta(Strategy):
    def __init__(self, conf: HostBundle, package: DataPackage, meta: Optional[dict] = None):
        super().__init__()
        self.conf = conf
        self.package = package
        self.meta = meta or {}

    @Strategy.schedule
    def save_meta(self):
        root = self.package.metas
        root.update(self.meta)
        root["TestCase"] = self.conf.conf_name
        root["Kernel"] = Environment.kernel
        root["Area"] = "net"

        if 'SockPerf' in self.conf.conf_name:
            root["BenchmarkName"] = "sockperf"
            root["BenchmarkVersion"] = RPMTool.get_package_version("sockperf")
        else:
            root["BenchmarkName"] = "iperf3"
            root["BenchmarkVersion"] = RPMTool.get_package_version("iperf3")
        root["Arguments"] = "-v"
        root["HostName"] = Environment.fqdn
        root["OtherHostNames"] = [Environment.fqdn]
        root["OtherHostNames"] += [h.hostname for h in self.conf.get_subset(m_class=SyncHost)]
        root["SELinux"] = SELinux.getenforce()
        root["Architecture"] = Lscpu.architecture()

        if Environment.in_rstrnt:
            root["Distribution"] = Environment.distro
            root["WhiteBoard"] = Environment.whiteboard
            root["BeakerJobID"] = Environment.job_id
            root["BeakerHUB"] = Environment.hub

        if Environment.in_tf:
            root["TfGitUrl"] = Environment.tf_git_url
            root["TfGitRef"] = Environment.tf_git_ref

        # In some special cases, tuned profile is not set (e.g.: Docker) or tuned-adm is not installed
        try:
            tuned_profile = Tuned.get_profile()
            if tuned_profile:
                root["TunedProfile"] = tuned_profile
        except Exception as e:
            logger.error("Tuned profile is unknown due to following error.")
            logger.error(str(e))
