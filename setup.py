"""
Ghost.py
--------

Webkit based webclient.

"""

import io
import os
import re

from setuptools import find_packages, setup

MODULE_NAME = 'ghost'


def find_file(*path_components):
    """Builds path from arguments."""
    return os.path.join(os.path.dirname(__file__), *path_components)


def get_version():
    """Reads package version number from module."""
    with io.open(
        find_file(MODULE_NAME, 'ghost.py'),
        encoding='utf8'
    ) as init:
        for line in init.readlines():
            res = re.match(r'^__version__ = [\'"](.*)[\'"]$', line)
            if res:
                return res.group(1)


setup(
    name='Ghost.py',
    version=get_version(),
    url='https://github.com/jeanphix/Ghost.py',
    license='mit',
    author='Jean-Philippe Serafin',
    author_email='serafinjp@gmail.com',
    description='Webkit based webclient.',
    long_description=__doc__,
    data_files=[(MODULE_NAME, ['README.rst',])],
    packages=find_packages(),
    include_package_data=True,
    tests_require=['Flask'],
    test_suite='tests.run',
    zip_safe=False,
    platforms='any',
    install_requires=[
        'xvfbwrapper ~=0.2.8',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
