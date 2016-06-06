#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

from granadilla.version import VERSION


def read(filename):
    with open(filename) as fp:
        return fp.read()


setup(
    name="granadilla",
    version=VERSION,
    author="Polyconseil Sysadmin Team",
    author_email="sysadmin+granadilla@polyconseil.fr",
    description="An opinionated LDAP frontend.",
    license="GPL",
    keywords=['granadilla', 'ldap', 'directory', 'admin'],
    url="https://github.com/Polyconseil/granadilla",
    packages=find_packages(),
    long_description=read('README.rst'),
    install_requires=[
        # Django core
        'Django>=1.7,<1.8',

        # Databases
        'django-ldapdb>=0.6.0',

        # Configuration
        'django-appconf',
        'getconf>=1.2.0',

        # Passwords
        'smbpasswd',
        'zxcvbn',

        # Command line
        'colorama',
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Environment :: Console",
        "Framework :: Django",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Systems Administration :: Authentication/Directory :: LDAP",
    ],
    include_package_data=True,
)
