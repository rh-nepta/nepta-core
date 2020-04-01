import re

from nepta.core.distribution import components


class RedhatRelease(components.DistributionComponent):
    RELEASE_FILE_PATH = '/etc/redhat-release'

    def __init__(self):
        super(RedhatRelease, self).__init__()
        splitting_regex = r'(.*) (release) (.*) \((.*)\)'
        with open(RedhatRelease.RELEASE_FILE_PATH, 'r') as fd:
            release_file_content = fd.read()
        m = re.match(splitting_regex, release_file_content)
        self._brand = m.group(1)
        self._version = m.group(3)
        self._codename = m.group(4)

    def __str__(self):
        return '%s %s %s' % (self._brand, self._version, self._codename)

    def get_brand(self):
        return self._brand

    def get_version(self):
        return self._version

    def get_codename(self):
        return self._codename


class Environment(components.DistributionComponent):

    def __init__(self):
        super().__init__()
        kernel_version = components.uname.get_version()
        self.kernel_src_rpm = components.rpmtool.get_src_name('kernel-%s' % kernel_version)
        if not self.kernel_src_rpm:
            self.kernel = 'unknown-' + kernel_version
        else:
            match = re.search(r'(?P<src_name>.+)-(.+)-(.+)\.*\.src\.rpm', self.kernel_src_rpm)
            self.kernel = match.group('src_name') + '-' + kernel_version
        self.fqdn = components.uname.get_hostname()
        self.distro = components.rhts.get_distro()
        if not self.distro:
            self.distro = 'Linux'
        self.rhel_version = rh_release.get_version()

    @property
    def hostname(self):
        return self.fqdn.split('.')[0]

    def __str__(self):
        r = self.__class__.__name__
        for k, v in self.__dict__.items():
            r += '\n%s=%s' % (k, v)
        return r


rh_release = RedhatRelease.get_instance()
environment = Environment().get_instance()
