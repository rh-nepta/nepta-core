import os
import logging

from nepta.core.strategies.generic import Strategy
from nepta.dataformat import DataPackage

logger = logging.getLogger(__name__)


class PackagesStrategy(Strategy):

    def __init__(self, package: DataPackage):
        super().__init__()
        self.package = package


class Save(PackagesStrategy):
    SYMLINK_NAME = '/root/result'

    @Strategy.schedule
    def save(self):
        self.package.close()

    @Strategy.schedule
    def create_local_symlink(self):
        pkg_path = os.path.abspath(self.package.path)
        if os.path.islink(self.SYMLINK_NAME):
            os.unlink(self.SYMLINK_NAME)
        logger.info(f'Creating symlink >> {self.SYMLINK_NAME} -> {pkg_path}')
        os.symlink(pkg_path, self.SYMLINK_NAME)


class OpenRemotePackages(PackagesStrategy):

    @Strategy.schedule
    def save_remote_packages(self):
        self.package.remote_packages.unarchive()


class SaveRemotePackages(PackagesStrategy):

    @Strategy.schedule
    def save_remote_packages(self):
        self.package.remote_packages.save()
