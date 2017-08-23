.. _contract-verification:

=================================
Contract source code verification
=================================

.. contents:: :local:

Verifying contracts on EtherScan
================================

ICO package has a semi-automated process to verify deployed contracts on `EtherScan verification service <https://etherscan.io/verifyContract>`_.

Benefits of verification
========================

* You can see the state of your contract variables real time on EtherScan block explorer

* You prove that there are deterministic and verifiable builds for your deployed smart contracts

Prerequisites
=============

* You need to have Chrome and `chromedriver <http://brewformulas.org/Chromedriver>`_ installed for the browser automation

* You need to have `Splinter <http://splinter.readthedocs.io/en/latest/>`_ Python package installed:

.. code-block:: shell

    pip install Splinter

How automatic verification works
================================

You need to specify the verification settings in your YAML deployment script for :ref:`deploy-contracts` command.

You need to make sure that you have your Solidity version and optimization parameters correctly.

Example how to get Solidity version:

.. code-block:: shell

    solc --version

Here is an example YAML section:

.. code-block:: yaml

    # Use automated Chrome to verify all contracts on etherscan.io
    verify_on_etherscan: yes
    browser_driver: chrome

    solc:

        # This is the Solidity version tag we verify on EtherScan.
        # For available versions see
        # https://kovan.etherscan.io/verifyContract2
        #
        # See values in Compiler drop down.
        # You can also get the local compiler version with:
        #
        #     solc --version
        #
        # Note that for EtherScan you need to add letter "v" at the front of the version
        #
        # Note: You need to have correct optmization settings for the compiler
        # in populus.json that matches what EtherScan is expecting.
        #
        version: v0.4.14+commit.c2215d46

        #
        # We supply these to EtherScan as the solc settings we used to compile the contract.
        # They must match values in populus.json compilication / backends section.
        # These are the defaults supplied with the default populus.json.
        #
        optimizations:
            optimizer: true
            runs: 500

When you run `deploy-contracts` and `verify_on_etherscan` is turned `on`, a Chrome browser will automatically open after a contract has been deployed. It goes to Verify page on EtherScan and automatically submits all verification information, including libraries.

In the case there is a problem with the verification, `deploy-contracts` will stop and ask you to continue. During this time, you can check what is the actual error from EtherScan on the opened Chrome browser.


