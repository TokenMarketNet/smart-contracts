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

Running tests::

    py.test tests

Run a specific test::

    py.test tests -k test_get_price_tiers

Deploying on testnet
^^^^^^^^^^^^^^^^^^^^

Compile contracts::

    populus compile

Deploy::

    python testnet_deploy.py


Deploying on a private testnet
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Create a local chain::

    populus chain run local

Compile contracts::

    populus compile

Deploy::

    python private_testnet_deploy.py
