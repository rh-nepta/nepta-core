import jinja2
import logging

from nepta.dataformat import DataPackage
from nepta.core.model.bundles import Bundle, SyncHost
from nepta.core.strategies.generic import Strategy
from nepta.core.strategies.save.save_package import Save
from nepta.core.distribution.command import Command

logger = logging.getLogger(__name__)


class RemoteLogs(Strategy):
    _RSYNC_TEMPLATE = jinja2.Template("""rsync -e ssh -avz --no-owner --no-group --recursive --chmod=a+r,a+w,a+X  \
    {{ host }}:{{ directory }}/ {{ local_path }}""")

    def __init__(self, conf: Bundle, package: DataPackage):
        super().__init__()
        self.conf = conf
        self.package = package

    @Strategy.schedule
    def rsync_remote_df_package(self):
        remote_hosts = self.conf.get_subset(m_class=SyncHost)

        for host in remote_hosts:
            remote_log = self.package.remote_packages.new(host.hostname)
            logger.info(f'Stealing df-pck from {host.hostname} into {remote_log.path}.')
            cmd = Command(self._RSYNC_TEMPLATE.render(
                host=host.hostname, directory=Save.SYMLINK_NAME, local_path=remote_log.path))
            cmd.run()
            logger.info(cmd.get_output()[0])
