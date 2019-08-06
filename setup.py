#!/usr/bin/env python3

from setuptools import setup, find_namespace_packages
import versioneer

with open('README.md', 'r') as f:
    readme = f.read()

print(find_namespace_packages())
setup(
    name='nepta-core',
    version=versioneer.get_version(),
    description='Core of NePTA framework for network testing.',
    long_description=readme,
    author='Adrian Tomasov',
    author_email='atomasov@redhat.com',
    url='https://github.com/rh-nepta/nepta-core',
    packages=find_namespace_packages(include=['nepta.*']),
    install_requires=['jinja2==2.10.1', 'xml-diff==0.7.0'],
    namespace_packages=['nepta'],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'nepta = nepta.core.__main__:main'
        ]
    },
)
