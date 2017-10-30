import os
from setuptools import setup
from torrt import VERSION


f = open(os.path.join(os.path.dirname(__file__), 'README.rst'))
README = f.read()
f.close()

setup(
    name='torrt',
    version='.'.join(map(str, VERSION)),
    url='https://github.com/idlesign/torrt',

    description='Automates torrent updates for you.',
    long_description=README,
    license='BSD 3-Clause License',

    author='Igor `idle sign` Starikov',
    author_email='idlesign@yandex.ru',

    packages=['torrt'],
    include_package_data=True,
    zip_safe=False,

    install_requires=['requests', 'beautifulsoup4', 'torrentool', 'lxml', 'six'],

    entry_points={
        'console_scripts': ['torrt = torrt.main:process_commands'],
    },

    classifiers=[
        # As in https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: BSD License'
    ],
)
