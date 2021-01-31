import io
import os
import re
import sys

from setuptools import setup, find_packages

PATH_BASE = os.path.dirname(__file__)


def read_file(fpath):
    """Reads a file within package directories."""
    with io.open(os.path.join(PATH_BASE, fpath)) as f:
        return f.read()


def get_version():
    """Returns version number, without module import (which can lead to ImportError
    if some dependencies are unavailable before install."""
    contents = read_file(os.path.join('torrt', '__init__.py'))
    version = re.search('VERSION = \(([^)]+)\)', contents)
    version = version.group(1).replace(', ', '.').strip()
    return version


setup(
    name='torrt',
    version=get_version(),
    url='https://github.com/idlesign/torrt',

    description='Automates torrent updates for you.',
    long_description=read_file('README.rst'),
    license='BSD 3-Clause License',

    author='Igor `idle sign` Starikov',
    author_email='idlesign@yandex.ru',

    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,

    install_requires=[
        'requests',
        'beautifulsoup4',
        'torrentool',
        'lxml',
    ],
    setup_requires=[] + (['pytest-runner'] if 'test' in sys.argv else []) + [],

    extras_require={
        'telegram': ['python-telegram-bot >=11.1.0, <12.0.0a0']
    },
    test_suite='tests',
    tests_require=[
        'pytest',
        'pytest-datafixtures',
        'pytest-responsemock>=1.0.0',
    ],

    entry_points={
        'console_scripts': ['torrt = torrt.main:process_commands'],
    },

    classifiers=[
        # As in https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'License :: OSI Approved :: BSD License'
    ],
)
