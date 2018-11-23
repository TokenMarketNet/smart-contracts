Test suite
==========

.. contents:: :local:

Introduction
^^^^^^^^^^^^

ICO package comes with extensive automated test suite for smart contracts.

About Populus
^^^^^^^^^^^^^

`Populus <http://populus.readthedocs.io/>`_ is a tool for the Ethereum blockchain and smart contract management. The project uses Populus internally. Populus is a Python based suite for

* Running arbitrary Ethereum chains (mainnet, testnet, private testnet)

* Running test suites against Solidity smart contracts


Running tests
^^^^^^^^^^^^^

Install first as given in the instructions.

Running tests using tox

    export SOLC_BINARY=$(pwd)/script/travis-dockerized-solc.sh
    export SOLC_VERSION=0.4.18
    tox

If ``solc`` fails, create a local virtual environment and test populus command locally::

    populus compile

Reasons could include: Docker not running.

Running tests in the current virtual environemtn::

    py.test tests

Run a specific test::

    py.test tests -k test_get_price_tiers
