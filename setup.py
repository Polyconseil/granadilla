#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
import subprocess

from setuptools import find_packages, setup
from setuptools.command import build_py

from granadilla.version import VERSION


def read(filename):
    with open(filename) as fp:
        return fp.read()


def find_package_data(patterns):
    package_data = {}
    for pattern in patterns:
        package, subpattern = pattern.split('/', 1)
        matched = glob.glob(pattern, recursive=True)
        package_data.setdefault(package, []).extend([
            # We need the paths relative to their package.
            path.split('/', 1)[1] for path in matched
        ])
    return package_data


class BuildWithMakefile(build_py.build_py):
    """Custom 'build' command that runs 'make build' first."""

    def run(self):
        # Ensure the checked-out folder comes first.
        # We install the project as `pip install -e .`, but zest
        # will assemble the bdist_wheel from a temporary location;
        # this makes sure that `polytranet.settings` is the file at that
        # -- thus assembling staticassets in the proper folders.

        env = dict(os.environ)
        env['PYTHONPATH'] = ':'.join(
            [
                os.path.dirname(__file__)
            ] + env.get('PYTHONPATH', '').split(':')
        )

        subprocess.check_call(['make', 'build'], env=env)

        # Recompute package data
        self.package_data = find_package_data(PACKAGE_DATA_PATTERNS)

        # Override the cached set of data_files.
        self.data_files = self._get_data_files()
        return super().run()


PACKAGE = 'granadilla'
PACKAGE_DATA_PATTERNS = [
    'granadilla/locale/**/*.mo',
]


setup(
    name=PACKAGE,
    version=VERSION,
    author="Polyconseil Sysadmin Team",
    author_email="sysadmin+%s@polyconseil.fr" % PACKAGE,
    description="An opinionated LDAP frontend.",
    license="GPL",
    keywords=['granadilla', 'ldap', 'directory', 'admin'],
    url="https://github.com/Polyconseil/%s" % PACKAGE,
    packages=find_packages(),
    long_description=read('README.rst'),
    zip_safe=False,

    # Ref: https://stackoverflow.com/questions/24347450/how-do-you-add-additional-files-to-a-wheel/49501350#49501350
    # Yep, the Python docs are false here.
    package_data=find_package_data(PACKAGE_DATA_PATTERNS),
    cmdclass={'build_py': BuildWithMakefile},
    include_package_data=True,
    install_requires=[
        # Databases
        'django-ldapdb',
        'django-auth-ldap',

        # Configuration
        'django-appconf',
        'getconf>=1.2.0',
        'django-zxcvbn-password>=2.0.0',
        'django-password-strength>=1.2.1',


        # Passwords
        'zxcvbn',

        # Command line
        'colorama',
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Environment :: Console",
        "Framework :: Django :: 2.1",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
    ],
)
