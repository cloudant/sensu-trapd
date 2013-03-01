#!/usr/bin/env python
# coding=utf-8
import os
import sys
import platform
from distutils.core import setup

distro = platform.dist()[0]

# Configure Data Files
data_files = list()
data_files.append(('', ['requirements.txt', 'version.txt']))
data_files.append(('', ['conf/config.json.default', 'conf/traps.json.default']))

def get_version():
    """ 
        Read the version.txt file to get the new version string
        Generate it if version.txt is not available. Generation
        is required for pip installs
    """
    try:
        f = open('version.txt')
    except IOError:
        os.system("./version.sh > version.txt")
        f = open('version.txt')
    version = ''.join(f.readlines()).rstrip()
    f.close()
    return version

version = get_version()

setup(
    name='sensu-trapd',
    version=version,
    url='https://github.com/cloudant/sensu-trapd',
    author='Cloudant Inc.',
    author_email='akipp@cloudant.com',
    license='MIT License',
    description='SNMP Trap Receiver for Sensu',
    package_dir={'': 'src'},
    packages=['sensu', 'sensu.snmp'],
    scripts=['src/bin/sensu-trapd'],
    data_files=data_files,
    #install_requires=install_requires,
    #test_suite='test.main',
)
