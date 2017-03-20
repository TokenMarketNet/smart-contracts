.. highlight:: shell

.. contents:: :local:

Introduction
============

This repository contains crowdsale smart contracts to be used with your `ICO <https://tokenmarket.net/what-is/ico>`_.

* Crowdsale contracts: token, ICO, uncapped ICO, pricing, transfer lock ups

* Populus based test suite

As the writing of this, Ethereum smart contract ICO business has been booming almost a year. The industry and development teams are still figuring out the best practices. A lot of similar smart contracts get written over and over again. This project aims to tackle this problem by providing reusable ICO codebase, so that developers can focus on their own project specific value adding feature instead of rebuilding core crowdfunding logic. Having one well maintained codebase with best practice and security audits benefits the community as a whole.

TODO
====

[ ] Refund

[ ] Migration agent

Features and design goals
=========================

* **Best practices**: Smart contracts are written with the modern best practices of Ethereum community in mind

* **Separation of concerns**: crowdsale and token logic lies in separate contracts

* **Testable**: all branches can be covered by an automatic test suite

* **Reusable**: The contract code is modularized and reusable across different projects, all variables are parametrized and there are no hardcoded values or magic numbers

* **Reissuance**: There can be multiple crowdsales for the same token (pre-ICO, ICO)

* **Emergency stop**: To try to save the situation in the case we found an issue in the contract post-deploy

* **Build upon a foundation**: Instead of building everything from the scratch, use [OpenZeppelin contracts](https://github.com/OpenZeppelin/zeppelin-solidity/) as much as possible as they are the gold standard of Solidity development

Installation
============

Preface
^^^^^^^

Instructions are written in OSX and Linux in mind.

Experience needed

* Basic command line usage

* Basic Github usage

Setting up - OSX
^^^^^^^^^^^^^^^^

Packages needed

* `Populus native dependencies <http://populus.readthedocs.io/en/latest/quickstart.html>`_

Get Solidity compiler. Use version 0.4.8. For OSX:

.. code-block:: console

    brew unlink solidity  # If needed
    # Install 0.4.8
    brew install https://raw.githubusercontent.com/ethereum/homebrew-ethereum/77cce03da9f289e5a3ffe579840d3c5dc0a62717/solidity.rb

Clone this repository from Github.

Python 3.x required. `See installing Python <https://www.python.org/downloads/>`_.

.. code-block:: console

     python3.5 --version
     Python 3.5.2

Create virtualenv for Python package management in the project root folder (same as where ``setup.py`` is):

.. code-block:: console

    python3.5 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Setting up - Ubuntu Linux 14.04
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Install dependencies:

.. code-block:: console

    sudo add-apt-repository ppa:fkrull/deadsnakes
    sudo apt-get update
    sudo apt-get install -y python3.5 python3.5-dev
    sudo apt install -y git build-essential python3-setuptools libssl-dev

`Install Go Ethereum <https://github.com/ethereum/go-ethereum/wiki/Installation-Instructions-for-Ubuntu>`_:

.. code-block:: console

    sudo apt-get install software-properties-common
    sudo add-apt-repository -y ppa:ethereum/ethereum
    sudo apt-get update
    sudo apt-get install -y ethereum solc

Then:

.. code-block:: console

    git clone # ...
    cd Smart-Contracts
    python3.5 -m venv --without-pip venv
    source venv/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python
    pip install -r requirements.txt
    pip install -e .

Usage
=====

About Populus
^^^^^^^^^^^^^

`Populus <http://populus.readthedocs.io/>`_ is a tool for the Ethereum blockchain and smart contract management. The project uses Populus internally. Populus is a Python based suite for

* Running arbitrary Ethereum chains (mainnet, testnet, private testnet)

* Running test suites against Solidity smart contracts

Tests
=====

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

In-depth discussion
===================

Timestamp vs. block number
--------------------------

The code uses block timestamps instead of block numbers for start and events. We work on the assumption that crowdsale periods are not so short or time sensitive there would be need for block number based timing. Furthermore if the network miners start to skew block timestamps we might have a larger problem with dishonest miners.

Crowdsale strategies and compound design pattern
------------------------------------------------

Instead of cramming all the logic into a single contract through mixins and inheritance, we assemble our crowdsale from multiple components. Benefits include more elegant code, better reusability, separation of concern and testability.

Mainly, our crowdsales have the following major parts

* Crowdsale core: capped or uncapped

* Pricing strategy: how price changes during the crowdsale

* Finalizing strategy: What happens after a successful crowdsale: allow tokens to be transferable, give out extra tokens, etc.

