This package contains Ethereum smart contracts for launching your `ICO <https://tokenmarket.net/what-is/ico>`_ crowdsale or token offering.

.. image:: https://img.shields.io/pypi/v/ico.svg
        :target: https://pypi.python.org/pypi/ico

.. image:: https://img.shields.io/travis/TokenMarketNet/ico.svg
        :target: https://travis-ci.org/TokenMarketNet/ico

.. image:: https://pyup.io/repos/github/TokenMarketNet/ico/shield.svg
     :target: https://pyup.io/repos/github/TokenMarketNet/ico/
     :alt: Updates

.. contents:: :local:

Introduction
============

As the writing of this, Ethereum smart contract ICO business has been booming almost a year. The industry and development teams are still figuring out the best practices. A lot of similar smart contracts get written over and over again. This project aims to tackle this problem by providing reusable ICO codebase, so that developers can focus on their own project specific value adding feature instead of rebuilding core crowdfunding logic. Having one well maintained codebase with best practice and security audits benefits the community as a whole.

This package provides

* Crowdsale contracts: token, ICO, uncapped ICO, pricing, transfer lock ups, token upgrade in Solidity smart contract programming language

* Automated test suite in Python

* Deployment tools and scripts

Features and design goals
=========================

* **Best practices**: Smart contracts are written with the modern best practices of Ethereum community

* **Separation of concerns**: Crowdsale, token and other logic lies in separate contracts that can be assembled together like lego bricks

* **Testable**: We aim for 100% branch code coverage by automated test suite

* **Reusable**: The contract code is modularized and reusable across different projects, all variables are parametrized and there are no hardcoded values or magic numbers

* **Refund**: Built-in refund and minimum funding goal protect investors

* **Migration**: Token holders can opt in to a new version of the token contract in the case the token owner wants to add more functionality to their token

* **Reissuance**: There can be multiple crowdsales for the same token (pre-ICO, ICO, etc.)

* **Emergency stop**: To try to save the situation in the case we found an issue in the contract post-deploy

* **Build upon a foundation**: Instead of building everything from the scratch, use `OpenZeppelin contracts <https://github.com/OpenZeppelin/zeppelin-solidity/>`_ as much as possible as they are the gold standard of Solidity development

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

Deploy a presale contract
^^^^^^^^^^^^^^^^^^^^^^^^^

A presale contract is a contract to collect presale investor money to be moved to a crowdsale when the crowdsale opens. The cresale contract can be deployed through ``presale`` command. After deploying the investors can call its ``invest()`` and ``refund()`` function from any Ethereum wallet allowing the transaction ``data`` field set.

``presale --help``::

    Usage: presale [OPTIONS]

    Options:
      --chain TEXT     On which chain to deploy
      --address TEXT   Account to deploy from (must exist on geth)
      --days INTEGER   How many days presale is frozen for
      --minimum FLOAT  What is the minimum pre-ico buy in (ether)
      --help           Show this message and exit.

Example that makes immediately refundable presale contract for testing on the mainnet::

    presale --address=0x8888888888888888888 --days=-1 --minimum=0.001

    Make sure mainnet chain is running, you can connect to it, or you'll get timeout
    Web3 provider is RPC connection http://127.0.0.1:8545
    Deploy address is 0x8888888888888888888
    Deploy address balance is 0.80625992728132232
    Please provide the password to unlock account `0x8888888888888888888`.:
    Deploying presale, tx hash is XXX
    Presale contract address is YYYY
    Presale constructor arguments is 0000000000000000000000000000000000000000000000000000000058d9722800000000000000000000000000000000000000000000000000038d7ea4c68000
    Presale freeze ends at 1490645544
    Presale minimum buy in (wei) is 1000000000000000
    Presale.invest() estimated gas cost is 107700
    Presale.invest() data payload is 0xe8b5e51f
    Presale.refund() data payload is 0x590e1ae3
    All done! Enjoy your decentralized future.

Tests
=====

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

In-depth discussion
===================

Timestamp vs. block number
^^^^^^^^^^^^^^^^^^^^^^^^^^

The code uses block timestamps instead of block numbers for start and events. We work on the assumption that crowdsale periods are not so short or time sensitive there would be need for block number based timing. Furthermore if the network miners start to skew block timestamps we might have a larger problem with dishonest miners.

Crowdsale strategies and compound design pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Instead of cramming all the logic into a single contract through mixins and inheritance, we assemble our crowdsale from multiple components. Benefits include more elegant code, better reusability, separation of concern and testability.

Mainly, our crowdsales have the following major parts

* Crowdsale core: capped or uncapped

* Pricing strategy: how price changes during the crowdsale

* Finalizing strategy: What happens after a successful crowdsale: allow tokens to be transferable, give out extra tokens, etc.

Background information
======================

* https://drive.google.com/file/d/0ByMtMw2hul0EN3NCaVFHSFdxRzA/view
