#!/usr/bin/env python3

from setuptools import setup, find_packages
import versioneer

with open('README.md', 'r') as f:
    readme = f.read()

setup(
    name='nepta-core',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='Core of NePTA framework for network testing.',
    long_description=readme,
    author='Adrian Tomasov',
    author_email='atomasov@redhat.com',
    url='https://github.com/rh-nepta/nepta-core',
    packages=find_packages(include=['nepta.*']),
    install_requires=['jinja2', 'xml-diff', 'numpy', 'singledispatchmethod', 'retry'],
    namespace_packages=['nepta'],
    include_package_data=True,
    scripts=[
        'scripts/reportVulnerabilities',
    ],
    entry_points={'console_scripts': ['nepta = nepta.core.__main__:main']},
)
