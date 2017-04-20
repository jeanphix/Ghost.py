"""
Ghost.py
--------

Webkit based webclient.

"""
from setuptools import setup, find_packages


setup(
    name='Ghost.py',
    version='2.0.0-dev',
    url='https://github.com/jeanphix/Ghost.py',
    license='mit',
    author='Jean-Philippe Serafin',
    author_email='serafinjp@gmail.com',
    description='Webkit based webclient.',
    long_description=__doc__,
    data_files=[('ghost', ['README.rst', ])],
    packages=find_packages(),
    include_package_data=True,
    tests_require=['Flask'],
    test_suite='tests.run',
    zip_safe=False,
    platforms='any',
    install_requires=[
        'xvfbwrapper==0.2.8',
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
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
