#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'populus'
]

test_requirements = [
    'pytest'
]

setup(
    name='ico',
    version='0.1',
    description="Ethereum smart contracts and tools for managing crowdsales",
    long_description=readme + '\n\n' + history,
    author="Mikko Ohtamaa",
    author_email='mikko@tokenmarket.net',
    url='https://tokenmarket.net',
    packages=[
        'ico',
    ],
    package_dir={'ico':
                 'ico'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache 2.0",
    zip_safe=False,
    keywords='ethereum blockchain smartcontract crowdsale ico solidity populus',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    setup_requires=["pytest-runner"],
    tests_require=test_requirements
)
