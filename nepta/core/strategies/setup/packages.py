import logging
from jinja2 import Template

from nepta.core import model
from nepta.core.distribution import conf_files, env
from nepta.core.distribution.command import Command
from nepta.core.strategies.setup.generic import _GenericSetup as Setup

logger = logging.getLogger(__name__)


class Packages(Setup):
    _PKG_MANAGERS_CMD = 'dnf -y --allowerasing install '

    # Use yum pkg manager for RHEL7
    if env.RedhatRelease.version.startswith('7'):
        _PKG_MANAGERS_CMD = 'yum -y install '

    def __init__(self, conf):
        super().__init__(conf)
        self._installer = self._PKG_MANAGERS_CMD
        self._custom_repo_install_tmplt = Template(
            """{{ installer }} {{ pkg.name }} \
    {% for repo in pkg.disable_repos %}--disablerepo {{ repo.key }} {% endfor %}\
    {% for repo in pkg.enable_repos %}--enablerepo {{ repo.key }} {% endfor %}"""
        )

    @Setup.schedule
    def add_repositories(self):
        logger.info('Adding repositories')
        repos = self.conf.get_subset(m_class=model.system.Repository)
        for repo in repos:
            logger.info('Adding repo %s', repo)
            conf_files.RepositoryFile(repo).apply()

    @Setup.schedule
    def install_packages(self):
        pkgs = self.conf.get_subset(m_type=model.system.Package)
        install_cmd = self._installer + ' '.join([str(pkg.value) for pkg in pkgs])
        c = Command(install_cmd)
        c.run()
        out, retcode = c.watch_output()
        logger.info(out)

    @Setup.schedule
    def install_special_packages(self):
        spec_pkgs = self.conf.get_subset(m_type=model.system.SpecialPackage)
        for pkg in spec_pkgs:
            install_cmd = self._custom_repo_install_tmplt.render(installer=self._installer, pkg=pkg)
            c = Command(install_cmd)
            c.run()
            out, retcode = c.watch_output()
            logger.info(out)
