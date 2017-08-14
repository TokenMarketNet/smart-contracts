.. _command-line:

=====================
Command line commands
=====================

.. contents:: :local:

Introduction
============

Here are listed command line commands.

All commands read `populus.json` file for the chain configuration from the current working directory. The chain configuration should set up a Web3 HTTP provider how command line command talks to an Ethereum node. The Ethereum node must have an address with ETH balance for the operations.

.. _deploy-token:

deploy-token
============

Deploy a crowdsale token contract.

.. autoprogram:: pyramid.scripts.pdistreport:get_parser()
    :prog: pdistreport


